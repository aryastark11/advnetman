import time
import re
import logging
from typing import Dict, List, Any, Optional
from netsleuth.storage.db import (
    save_incident,
    get_incidents,
    get_incident_by_id,
    add_timeline_event,
    update_node_health
)
from .rules import evaluate_all_rules, EXPECTED_OSPF_INTERFACES
from .blast_radius import compute_blast_radius
from .evidence_builder import compile_incident_evidence

logger = logging.getLogger("netsleuth.engine")

class IncidentEngine:
    def __init__(self):
        self._active_incident_map: Dict[str, str] = {} # key: (device, category) -> incident_id

    def build_deterministic_hypothesis(self, violation: Dict[str, Any], ev_ids: List[str]) -> Dict[str, Any]:
        """Provides deterministic root-cause hypothesis and proposed fix (works with LLM disabled)."""
        rule = violation.get("rule", "")
        dev = violation.get("device", "")
        detail = violation.get("detail", "")
        raw = violation.get("raw_data", {})

        cause = f"Deterministic Localization: {detail}"
        confidence = 0.95
        next_test = f"Verify {dev} protocol adjacency & interface operational state."
        commands = []
        rollback_cmds = []

        if rule == "bgp_peer_down":
            peer_ip = raw.get("peer_ip", "")
            asn = "65005" if dev == "R5" else "65001"
            cause = f"BGP session between {dev} and peer {peer_ip} (AS {asn}) collapsed."
            commands = [f"router bgp {asn}", f"no neighbor {peer_ip} shutdown"]
            rollback_cmds = [f"router bgp {asn}", f"neighbor {peer_ip} shutdown"]
        elif rule in ["ospf_area_mismatch", "ospf_neighbor_missing", "ospf_neighbor_not_full"]:
            intf = raw.get("interface", "")
            if not intf:
                m = re.search(r'(Ethernet[\d\./]+|Management[\d\./]+)', violation.get("title", "") + " " + violation.get("detail", ""))
                intf = m.group(1) if m else "Ethernet3"

            # Derive target area
            target_area = raw.get("area_id") or raw.get("expected_area", "")
            if not target_area:
                for exp_i, exp_a in EXPECTED_OSPF_INTERFACES.get(dev, []):
                    if exp_i == intf:
                        target_area = exp_a.split(".")[-1] if exp_a.startswith("0.0.0.") else exp_a
                        break
            if not target_area:
                target_area = "10" if dev in ["R4", "R6"] else ("20" if dev == "R7" else ("30" if dev == "R8" else "0"))

            cfg_area = raw.get("configured_area", "")
            cfg_area_id = cfg_area.split(".")[-1] if cfg_area.startswith("0.0.0.") else (cfg_area or "99")

            if rule == "ospf_area_mismatch" or "mismatch" in violation.get("title", "").lower() or (cfg_area and cfg_area != raw.get("expected_area")):
                cause = f"OSPF Area configuration mismatch on {dev} {intf} (configured: {cfg_area or 'unknown'}, expected: Area {target_area})."
                commands = [f"interface {intf}", f"ip ospf area {target_area}"]
                rollback_cmds = [f"interface {intf}", f"ip ospf area {cfg_area_id or '99'}"]
            elif rule == "ospf_neighbor_missing":
                cause = f"OSPF neighbor adjacency missing on {dev} {intf} (expected Area {target_area})."
                commands = [f"interface {intf}", f"ip ospf area {target_area}", "no shutdown"]
                rollback_cmds = [f"interface {intf}", f"ip ospf area {cfg_area_id or '99'}"]
            else: # ospf_neighbor_not_full
                cause = f"OSPF Area mismatch or hello/dead interval timer mismatch on {dev} {intf}."
                commands = [f"interface {intf}", "ip ospf hello-interval 1", "ip ospf dead-interval 3", f"ip ospf area {target_area}", "no shutdown"]
                rollback_cmds = [f"interface {intf}", "shutdown"]
        elif rule == "vlan_trunk_missing":
            intf = raw.get("interface", "Ethernet1")
            exp_vlans = raw.get("expected_vlans", "10,20")
            cur_vlans = raw.get("allowed_vlans", "20")
            missing = raw.get("missing_vlans", ["10"])
            cause = f"Layer 2 802.1Q trunk pruning fault on {dev} {intf}: VLAN(s) {','.join(missing)} omitted from allowed VLAN list."
            commands = [f"interface {intf}", f"switchport trunk allowed vlan {exp_vlans}"]
            rollback_cmds = [f"interface {intf}", f"switchport trunk allowed vlan {cur_vlans}"]
        elif rule == "interface_down":
            intf = raw.get("name") or raw.get("interface", "")
            if not intf:
                m = re.search(r'(Ethernet[\d\./]+|Management[\d\./]+)', violation.get("title", "") + " " + violation.get("detail", ""))
                intf = m.group(1) if m else "Ethernet1"
            cause = f"Physical / administrative link failure on {dev} interface {intf}."
            commands = [f"interface {intf}", "no shutdown"]
            rollback_cmds = [f"interface {intf}", "shutdown"]
        elif rule == "rip_missing_network":
            cause = f"RIPv2 network statement missing from {dev} or distribution router."
            commands = ["router rip", "network 10.10.0.0/16", "no shutdown"]
            rollback_cmds = ["router rip", "no network 10.10.0.0/16"]
        elif rule == "varp_gateway_down":
            cause = f"VARP / VRRP active-active gateway service degraded on {dev}."
            commands = ["ip virtual-router mac-address 00:1c:73:00:00:01", "interface Ethernet2.10", "no shutdown"]
            rollback_cmds = []
        elif rule == "synthetic_probe_failure":
            cause = f"End-to-end data plane transport interruption toward {dev}."
            commands = []
            rollback_cmds = []

        return {
            "summary": cause,
            "hypotheses": [
                {
                    "cause": cause,
                    "confidence": confidence,
                    "evidence_ids": ev_ids,
                    "next_test": next_test
                }
            ],
            "proposed_fix": {
                "description": f"Restore nominal state on {dev} via eAPI.",
                "device": dev,
                "commands": commands,
                "risk": "low" if commands else "none",
                "rollback": rollback_cmds
            }
        }

    def scan_and_reconcile(self) -> List[Dict[str, Any]]:
        """Run health rules, compute blast radius, correlate incidents, update timeline."""
        violations = evaluate_all_rules()
        seen_keys = set()
        active_incidents = []

        # Update all node health initially to healthy
        all_devs = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "S1", "S2", "S3", "S4", "S5", "web-server", "nmas", "backup-server", "H1", "H2", "H3", "H4", "H5", "H6", "H7"]
        node_health_state = {d: "healthy" for d in all_devs}

        for v in violations:
            dev = v.get("device", "Network")
            cat = v.get("category", "General")
            key = f"{dev}:{cat}"
            seen_keys.add(key)

            # Node health status
            severity = v.get("severity", "medium")
            if severity == "critical":
                node_health_state[dev] = "critical"
            elif severity == "high" and node_health_state.get(dev) != "critical":
                node_health_state[dev] = "critical"
            elif severity == "medium" and node_health_state.get(dev) not in ["critical", "warning"]:
                node_health_state[dev] = "warning"

            # Check if incident already exists for this key
            inc_id = self._active_incident_map.get(key)
            existing_inc = get_incident_by_id(inc_id) if inc_id else None

            if not existing_inc or existing_inc.get("status") in ["resolved", "closed", "rollback"]:
                # Create NEW Incident
                now = time.time()
                inc_id = f"INC-{int(now * 1000) % 1000000}"
                blast = compute_blast_radius(dev, cat, v)

                # Build evidence
                ev_items = compile_incident_evidence(inc_id, v)
                ev_ids = [e["id"] for e in ev_items]

                # Deterministic core hypothesis
                diag = self.build_deterministic_hypothesis(v, ev_ids)

                inc_payload = {
                    "id": inc_id,
                    "title": v.get("title", f"Failure detected on {dev}"),
                    "severity": severity,
                    "category": cat,
                    "status": "open",
                    "root_cause_device": dev,
                    "blast_radius_hosts": blast.get("affected_hosts", []),
                    "blast_radius_services": blast.get("affected_services", []),
                    "hypotheses": diag["hypotheses"],
                    "proposed_fix": diag["proposed_fix"],
                    "created_at": now
                }

                save_incident(inc_payload)
                self._active_incident_map[key] = inc_id

                # Timeline events
                add_timeline_event(
                    incident_id=inc_id,
                    event_type="incident_created",
                    description=f"Deterministic engine opened incident: {v.get('title')}",
                    details={"violation": v, "blast_radius": blast}
                )
                if v.get("evidence_type") == "probe_failure":
                    add_timeline_event(
                        incident_id=inc_id,
                        event_type="first_bad_probe",
                        description=f"First synthetic probe failure recorded toward {dev}",
                        details=v.get("raw_data", {})
                    )
                elif "ospf" in v.get("rule", "") or "bgp" in v.get("rule", ""):
                    add_timeline_event(
                        incident_id=inc_id,
                        event_type="adjacency_change",
                        description=f"Protocol adjacency state collapsed: {v.get('title')}",
                        details=v.get("raw_data", {})
                    )
                elif "interface" in v.get("rule", ""):
                    add_timeline_event(
                        incident_id=inc_id,
                        event_type="interface_down",
                        description=f"Interface failure detected: {v.get('title')}",
                        details=v.get("raw_data", {})
                    )

                active_incidents.append(inc_payload)
            else:
                # Update existing incident
                existing_inc["updated_at"] = time.time()
                save_incident(existing_inc)
                active_incidents.append(existing_inc)

        # Check for auto-recovery of previously open incidents
        for k, inc_id in list(self._active_incident_map.items()):
            if k not in seen_keys:
                inc = get_incident_by_id(inc_id)
                if inc and inc.get("status") in ["open", "investigating", "mitigating", "rollback"]:
                    inc["status"] = "resolved"
                    save_incident(inc)
                    add_timeline_event(
                        incident_id=inc_id,
                        event_type="recovery",
                        description=f"Incident auto-resolved: all deterministic health checks now PASSING.",
                        details={"resolved_key": k}
                    )
                del self._active_incident_map[k]

        # Reconcile any persistent open DB incidents whose root causes are now resolved
        all_open_incs = get_incidents("open")
        for inc in all_open_incs:
            dev = inc.get("root_cause_device", "")
            cat = inc.get("category", "")
            key = f"{dev}:{cat}"
            if key not in seen_keys:
                inc["status"] = "resolved"
                save_incident(inc)
                add_timeline_event(
                    incident_id=inc["id"],
                    event_type="recovery",
                    description=f"Incident auto-resolved: network restored to nominal baseline.",
                    details={"resolved_key": key}
                )

        # Update node health in storage
        for d, h in node_health_state.items():
            update_node_health(d, h)

        return active_incidents

incident_engine = IncidentEngine()
