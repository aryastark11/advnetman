import logging
from typing import Dict, List, Any, Optional
from netsleuth.collectors.eapi_poller import (
    get_interfaces_status,
    get_ospf_neighbors,
    get_bgp_peers,
    get_rip_routes,
    get_varp_state,
    run_commands
)
from netsleuth.storage.db import get_config_drift, get_recent_probes

logger = logging.getLogger("netsleuth.rules")

EXPECTED_OSPF_INTERFACES = {
    "R1": [("Ethernet1", "0.0.0.0")],
    "R2": [("Ethernet1", "0.0.0.0"), ("Ethernet3", "0.0.0.30")],
    "R3": [("Ethernet2", "0.0.0.0")],
    "R4": [("Ethernet2", "0.0.0.0"), ("Ethernet3", "0.0.0.10")],
    "R6": [("Ethernet1", "0.0.0.10"), ("Ethernet2", "0.0.0.20")],
    "R7": [("Ethernet1", "0.0.0.20")],
    "R8": [("Ethernet1", "0.0.0.30")],
}

def check_ospf_rules() -> List[Dict[str, Any]]:
    violations = []
    
    for dev, exp_intfs in EXPECTED_OSPF_INTERFACES.items():
        neighbors = get_ospf_neighbors(dev)
        active_intf_areas = {}
        for n in neighbors:
            intf_name = n.get("interface", "")
            area_val = n.get("area", "")
            active_intf_areas[intf_name] = (n.get("state", "").lower(), area_val, n)

        for exp_intf, exp_area in exp_intfs:
            if exp_intf not in active_intf_areas:
                violations.append({
                    "rule": "ospf_neighbor_missing",
                    "device": dev,
                    "severity": "critical" if dev in ["R4", "R6"] else "high",
                    "category": "Control Plane - OSPF",
                    "title": f"OSPF Adjacency Missing on {dev} ({exp_intf})",
                    "detail": f"Router {dev} has no active OSPF neighbor on {exp_intf} (expected Area {exp_area}). Possible area ID mismatch or interface shutdown.",
                    "evidence_type": "ospf_neighbor",
                    "raw_data": {"device": dev, "interface": exp_intf, "expected_area": exp_area, "neighbors": neighbors}
                })
            else:
                state, area_val, n_data = active_intf_areas[exp_intf]
                if state not in ["full", "2ways"]:
                    violations.append({
                        "rule": "ospf_neighbor_not_full",
                        "device": dev,
                        "severity": "high",
                        "category": "Control Plane - OSPF",
                        "title": f"OSPF Adjacency Degraded on {dev} ({exp_intf})",
                        "detail": f"OSPF neighbor on {exp_intf} is in '{state}' state instead of FULL.",
                        "evidence_type": "ospf_neighbor",
                        "raw_data": n_data
                    })
    return violations

def check_bgp_rules() -> List[Dict[str, Any]]:
    violations = []
    # R3, R4, R5 participate in eBGP
    for dev in ["R3", "R4", "R5"]:
        peers = get_bgp_peers(dev)
        if not peers:
            violations.append({
                "rule": "bgp_no_peers",
                "device": dev,
                "severity": "critical",
                "category": "Control Plane - BGP",
                "title": f"No BGP Peers Configured or Active on {dev}",
                "detail": f"ASBR router {dev} has zero active BGP sessions.",
                "evidence_type": "bgp_summary",
                "raw_data": {"device": dev, "peers": []}
            })
            continue

        for p in peers:
            state = p.get("state", "")
            if state != "Established":
                violations.append({
                    "rule": "bgp_peer_down",
                    "device": dev,
                    "severity": "critical",
                    "category": "Control Plane - BGP",
                    "title": f"BGP Session Down on {dev} to Peer {p.get('peer_ip')}",
                    "detail": f"eBGP session with peer {p.get('peer_ip')} (AS {p.get('asn')}) is in '{state}' state.",
                    "evidence_type": "bgp_summary",
                    "raw_data": p
                })
            elif p.get("prefixes_received", 0) == 0 and dev == "R5":
                violations.append({
                    "rule": "bgp_no_prefixes",
                    "device": dev,
                    "severity": "high",
                    "category": "Control Plane - BGP",
                    "title": f"Zero BGP Prefixes Received on R5 from {p.get('peer_ip')}",
                    "detail": f"BGP session is Established but 0 prefixes received from ASBR.",
                    "evidence_type": "bgp_summary",
                    "raw_data": p
                })
    return violations

def check_rip_rules() -> List[Dict[str, Any]]:
    violations = []
    # R1 and R2 should have RIP routes and network statements for campus VLAN subnets
    for dev in ["R1", "R2"]:
        # 1. Check running config for RIP network statements
        rip_cfg = run_commands(dev, ["show running-config section router rip"], encoding="text")
        rip_text = rip_cfg[0].get("output", "") if rip_cfg else ""
        if "network 10.10." not in rip_text and "network 10.0.0.0" not in rip_text:
            violations.append({
                "rule": "rip_missing_network",
                "device": dev,
                "severity": "high",
                "category": "Control Plane - RIP",
                "title": f"RIPv2 Network Advertisement Missing on {dev}",
                "detail": f"Router {dev} is missing network advertisement statement (10.10.0.0/16) in RIP configuration.",
                "evidence_type": "rip_config",
                "raw_data": {"device": dev, "config": rip_text}
            })
            continue

        # 2. Check route database
        routes = get_rip_routes(dev)
        has_subnets = any("10.10." in r.get("network", "") for r in routes)
        if not has_subnets:
            violations.append({
                "rule": "rip_missing_network",
                "device": dev,
                "severity": "high",
                "category": "Control Plane - RIP",
                "title": f"RIPv2 Route Database Missing VLAN Subnets on {dev}",
                "detail": f"Router {dev} does not receive RIPv2 routes for 10.10.x.x subnets.",
                "evidence_type": "rip_database",
                "raw_data": {"device": dev, "routes": routes}
            })
    return violations

def check_interface_rules() -> List[Dict[str, Any]]:
    violations = []
    # Check all routers and switches
    all_devs = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "S1", "S2", "S3", "S4", "S5"]
    for dev in all_devs:
        data = get_interfaces_status(dev)
        statuses = data.get("statuses", {})
        errors = data.get("errors", {})

        for intf_name, st in statuses.items():
            # Skip unmapped or disabled interfaces
            if not intf_name.startswith("Ethernet"):
                continue

            link_st = st.get("lineProtocolStatus") or st.get("interfaceStatus", "")
            # Check for explicitly down interfaces that are configured
            if link_st in ["down", "notconnect", "disabled"]:
                # Check if it was intentionally shut or down
                st_data = dict(st)
                st_data["interface"] = intf_name
                st_data["name"] = intf_name
                violations.append({
                    "rule": "interface_down",
                    "device": dev,
                    "severity": "high" if dev.startswith("R") else "medium",
                    "category": "Data Plane - Interface",
                    "title": f"Interface {intf_name} Down on {dev}",
                    "detail": f"Interface {intf_name} on {dev} line protocol is '{link_st}'.",
                    "evidence_type": "interface_state",
                    "raw_data": st_data
                })

        for intf_name, err in errors.items():
            in_errs = err.get("inErrors", 0)
            out_errs = err.get("outErrors", 0)
            fcs_errs = err.get("fcsErrors", 0)
            if in_errs > 50 or out_errs > 50 or fcs_errs > 10:
                err_data = dict(err)
                err_data["interface"] = intf_name
                err_data["name"] = intf_name
                violations.append({
                    "rule": "interface_errors_rising",
                    "device": dev,
                    "severity": "medium",
                    "category": "Data Plane - Interface",
                    "title": f"High Interface Error Counter on {dev} {intf_name}",
                    "detail": f"Interface {intf_name} reports inErrors={in_errs}, outErrors={out_errs}, fcsErrors={fcs_errs}.",
                    "evidence_type": "interface_errors",
                    "raw_data": err_data
                })
    return violations

def check_varp_rules() -> List[Dict[str, Any]]:
    violations = []
    for dev in ["R1", "R2"]:
        vdata = get_varp_state(dev)
        vrrp_entries = vdata.get("vrrp", [])
        if not vrrp_entries:
            violations.append({
                "rule": "varp_not_configured",
                "device": dev,
                "severity": "high",
                "category": "High Availability - VARP",
                "title": f"VARP/VRRP Virtual Routers Inactive on {dev}",
                "detail": f"Gateway router {dev} has no active VRRP virtual routers.",
                "evidence_type": "varp_state",
                "raw_data": vdata
            })
            continue

        for vr in vrrp_entries:
            st = vr.get("state", "").lower()
            if st not in ["master", "backup"]:
                violations.append({
                    "rule": "varp_gateway_down",
                    "device": dev,
                    "severity": "high",
                    "category": "High Availability - VARP",
                    "title": f"VARP Gateway Group {vr.get('groupId')} Down on {dev}",
                    "detail": f"Virtual router group {vr.get('groupId')} on {vr.get('interface')} is in '{st}' state.",
                    "evidence_type": "varp_state",
                    "raw_data": vr
                })
    return violations

def check_probe_rules() -> List[Dict[str, Any]]:
    violations = []
    probes = get_recent_probes(limit=40)
    if not probes:
        return []

    # Group latest probe per (source_host, target_name, probe_type)
    latest = {}
    for p in probes:
        key = (p["source_host"], p["target_name"], p["probe_type"])
        if key not in latest:
            latest[key] = p

    failures_by_target = {}
    for (sh, target, ptype), p in latest.items():
        if p["success"] == 0:
            if target not in failures_by_target:
                failures_by_target[target] = []
            failures_by_target[target].append(p)

    for target, fail_list in failures_by_target.items():
        affected_hosts = list(set(f["source_host"] for f in fail_list))
        severity = "critical" if target == "Web Server" else "high"
        violations.append({
            "rule": "synthetic_probe_failure",
            "device": "Web Server" if target == "Web Server" else "Core Network",
            "severity": severity,
            "category": "Synthetic Probes",
            "title": f"Synthetic Probes Failing to {target} ({len(affected_hosts)} Hosts Affected)",
            "detail": f"Probes failing from: {', '.join(sorted(affected_hosts))}. Error: {fail_list[0].get('error_msg')}",
            "evidence_type": "probe_failure",
            "raw_data": {"target": target, "affected_hosts": affected_hosts, "failures": fail_list}
        })
    return violations

def check_drift_rules() -> List[Dict[str, Any]]:
    violations = []
    drifts = get_config_drift()
    for d in drifts:
        if d.get("has_drift"):
            violations.append({
                "rule": "golden_config_drift",
                "device": d.get("device"),
                "severity": "low",
                "category": "Config Drift",
                "title": f"Configuration Drift Detected on {d.get('device')}",
                "detail": f"Running configuration differs from golden baseline v1.0.",
                "evidence_type": "config_diff",
                "raw_data": {"device": d.get("device"), "diff": d.get("diff_text", "")}
            })
    return violations

def evaluate_all_rules() -> List[Dict[str, Any]]:
    """Runs all deterministic health rules and returns list of rule violations."""
    all_violations = []
    all_violations.extend(check_interface_rules())
    all_violations.extend(check_bgp_rules())
    all_violations.extend(check_ospf_rules())
    all_violations.extend(check_rip_rules())
    all_violations.extend(check_varp_rules())
    all_violations.extend(check_probe_rules())
    all_violations.extend(check_drift_rules())
    return all_violations
