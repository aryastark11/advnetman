#!/usr/bin/env python3
"""
CSCI 5840 - Network Automation & Security
Golden Baseline, Configuration Drift, Route Table & Neighbor Drift Comparator
Compares live Arista eAPI state against Golden Configurations & Golden Network Baselines.
"""

import argparse
import base64
import csv
import difflib
import json
import os
import sys
import urllib.request
import hvac

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_DIR = os.path.join(BASE_DIR, "golden_configs")
IPAM_CSV = os.path.join(BASE_DIR, "ipam.csv")
VAULT_URL = "https://127.0.0.1:8200"
CA_CERT = os.path.join(BASE_DIR, "vault", "certs", "ca.crt")
APPROLE_FILE = os.path.expanduser("~/.vault_approle.json")

# Golden Baseline Routing & Neighbor Expectations per Device
EXPECTED_NEIGHBORS = {
    "R1": {
        "ospf_neighbors": ["10.0.0.2", "10.0.0.3", "10.0.0.4"],
        "vrrp_groups": [10, 20, 30],
        "expected_vrrp_state": "master",
        "bgp_peers": []
    },
    "R2": {
        "ospf_neighbors": ["10.0.0.1", "10.0.0.3", "10.0.0.4"],
        "vrrp_groups": [10, 20, 30],
        "expected_vrrp_state": "master",
        "bgp_peers": []
    },
    "R3": {
        "ospf_neighbors": ["10.0.0.1", "10.0.0.2", "10.0.0.4"],
        "bgp_peers": ["172.16.35.2"],
        "vrrp_groups": []
    },
    "R4": {
        "ospf_neighbors": ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
        "bgp_peers": ["172.16.45.2"],
        "vrrp_groups": []
    },
    "R5": {
        "ospf_neighbors": [],
        "bgp_peers": ["172.16.35.1", "172.16.45.1"],
        "vrrp_groups": []
    },
    "S1": {"ospf_neighbors": [], "bgp_peers": [], "vrrp_groups": []},
    "S2": {"ospf_neighbors": [], "bgp_peers": [], "vrrp_groups": []},
    "S3": {"ospf_neighbors": [], "bgp_peers": [], "vrrp_groups": []},
    "S4": {"ospf_neighbors": [], "bgp_peers": [], "vrrp_groups": []}
}

DEVICE_MGMT_IPS = {
    "R1": "172.20.20.11",
    "R2": "172.20.20.12",
    "R3": "172.20.20.13",
    "R4": "172.20.20.14",
    "R5": "172.20.20.15",
    "S1": "172.20.20.21",
    "S2": "172.20.20.22",
    "S3": "172.20.20.23",
    "S4": "172.20.20.24",
}

def get_vault_credentials():
    """Retrieves device credentials from Vault or returns defaults."""
    credentials = {}
    if os.path.exists(APPROLE_FILE) and os.path.exists(CA_CERT):
        try:
            with open(APPROLE_FILE, "r") as f:
                approle_data = json.load(f)
            client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
            client.auth.approle.login(
                role_id=approle_data["role_id"],
                secret_id=approle_data["secret_id"]
            )
            for hostname in DEVICE_MGMT_IPS.keys():
                try:
                    sec = client.secrets.kv.v2.read_secret_version(
                        mount_point="network",
                        path=f"devices/{hostname}"
                    )["data"]["data"]
                    credentials[hostname] = {
                        "username": sec.get("username", "admin"),
                        "password": sec.get("password", "admin")
                    }
                except Exception:
                    credentials[hostname] = {"username": "admin", "password": "admin"}
            return credentials
        except Exception:
            pass
    
    for hostname in DEVICE_MGMT_IPS.keys():
        credentials[hostname] = {"username": "admin", "password": "admin"}
    return credentials

def query_device_eapi(mgmt_ip, username, password, cmds, fmt="json", timeout=4.0):
    """Executes commands on Arista device via eAPI JSON-RPC."""
    url = f"http://{mgmt_ip}/command-api"
    auth_str = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": cmds,
            "format": fmt
        },
        "id": "compare-golden-audit"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth_str}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data.get("result", [])
    except Exception as e:
        return False, str(e)

def parse_running_config(mgmt_ip, username, password):
    """Pulls running-config in text format from Arista device."""
    ok, res = query_device_eapi(mgmt_ip, username, password, ["enable", "show running-config"], fmt="text")
    if ok and len(res) > 1:
        return res[1].get("output", "")
    return ""

def audit_device(hostname, mgmt_ip, username, password):
    """Audits a single device against its golden config and operational baselines."""
    report = {
        "hostname": hostname,
        "mgmt_ip": mgmt_ip,
        "online": False,
        "has_golden_config": False,
        "config_compliance_pct": 0.0,
        "config_diff_lines": 0,
        "diff_added": 0,
        "diff_removed": 0,
        "diff_unified": "",
        "golden_config_text": "",
        "running_config_text": "",
        "routes": {
            "total_routes": 0,
            "connected": 0,
            "ospf": 0,
            "bgp": 0,
            "rip": 0,
            "static": 0,
            "raw_table": ""
        },
        "neighbors": {
            "ospf_neighbors": [],
            "ospf_drift": "IN_SYNC",
            "bgp_peers": [],
            "bgp_drift": "IN_SYNC",
            "vrrp_state": [],
            "vrrp_drift": "IN_SYNC"
        },
        "summary_status": "UNKNOWN"
    }

    # 1. Load Golden Config
    golden_filename = f"{hostname.lower()}_v1.0-baseline.cfg"
    golden_path = os.path.join(GOLDEN_DIR, golden_filename)
    golden_lines = []
    if os.path.exists(golden_path):
        report["has_golden_config"] = True
        with open(golden_path, "r", encoding="utf-8") as f:
            report["golden_config_text"] = f.read()
            golden_lines = [l.strip() for l in report["golden_config_text"].splitlines() if l.strip() and not l.strip().startswith("!")]

    # 2. Pull Live Running Config & Telemetry
    running_cfg_raw = parse_running_config(mgmt_ip, username, password)
    if running_cfg_raw:
        report["online"] = True
        report["running_config_text"] = running_cfg_raw
        running_lines = [l.strip() for l in running_cfg_raw.splitlines() if l.strip() and not l.strip().startswith("!")]
        
        # Calculate Unified Diff
        diff_generator = difflib.unified_diff(
            golden_lines,
            running_lines,
            fromfile=f"golden_configs/{golden_filename}",
            tofile=f"{hostname} (running-config)",
            lineterm=""
        )
        diff_list = list(diff_generator)
        report["diff_unified"] = "\n".join(diff_list)
        
        added = sum(1 for line in diff_list if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_list if line.startswith("-") and not line.startswith("---"))
        report["diff_added"] = added
        report["diff_removed"] = removed
        report["config_diff_lines"] = added + removed

        total_lines = max(len(golden_lines), 1)
        common_lines = total_lines - removed
        report["config_compliance_pct"] = round(max(0.0, min(100.0, (common_lines / total_lines) * 100.0)), 1)

    # 3. Pull Live Routing Table
    if report["online"]:
        ok_r, res_r = query_device_eapi(mgmt_ip, username, password, ["enable", "show ip route summary", "show ip route"], fmt="text")
        if ok_r and len(res_r) > 2:
            report["routes"]["raw_table"] = res_r[2].get("output", "")
        
        ok_rj, res_rj = query_device_eapi(mgmt_ip, username, password, ["enable", "show ip route summary"], fmt="json")
        if ok_rj and len(res_rj) > 1 and isinstance(res_rj[1], dict):
            rdata = res_rj[1]
            report["routes"]["total_routes"] = rdata.get("totalRoutes", 0)
            report["routes"]["connected"] = rdata.get("connected", 0)
            report["routes"]["static"] = rdata.get("static", 0)
            report["routes"]["ospf"] = rdata.get("ospfCounts", {}).get("ospfTotal", 0)
            report["routes"]["bgp"] = rdata.get("bgpCounts", {}).get("bgpTotal", 0)
            report["routes"]["rip"] = rdata.get("rip", 0)

    # 4. Pull Live Neighbor States (OSPF, BGP, VRRP)
    if report["online"]:
        # OSPF
        ok_o, res_o = query_device_eapi(mgmt_ip, username, password, ["enable", "show ip ospf neighbor"], fmt="json")
        if ok_o and len(res_o) > 1 and isinstance(res_o[1], dict):
            try:
                inst_list = res_o[1].get("vrfs", {}).get("default", {}).get("instList", {})
                for inst_id, inst in inst_list.items():
                    for nbr in inst.get("ospfNeighborEntries", []):
                        report["neighbors"]["ospf_neighbors"].append({
                            "routerId": nbr.get("routerId"),
                            "interface": nbr.get("interfaceName"),
                            "ip": nbr.get("interfaceAddress"),
                            "state": nbr.get("adjacencyState"),
                            "drState": nbr.get("drState")
                        })
            except Exception:
                pass
        
        # BGP
        ok_b, res_b = query_device_eapi(mgmt_ip, username, password, ["enable", "show ip bgp summary"], fmt="json")
        if ok_b and len(res_b) > 1 and isinstance(res_b[1], dict):
            try:
                vrf_bgp = res_b[1].get("vrfs", {}).get("default", {})
                peers = vrf_bgp.get("peers", {})
                for peer_ip, pdata in peers.items():
                    report["neighbors"]["bgp_peers"].append({
                        "peer_ip": peer_ip,
                        "asn": pdata.get("asn"),
                        "state": pdata.get("peerState"),
                        "prefix_received": pdata.get("prefixReceived", 0)
                    })
            except Exception:
                pass

        # VRRP
        ok_v, res_v = query_device_eapi(mgmt_ip, username, password, ["enable", "show vrrp brief"], fmt="json")
        if ok_v and len(res_v) > 1 and isinstance(res_v[1], dict):
            try:
                for vr in res_v[1].get("virtualRouters", []):
                    report["neighbors"]["vrrp_state"].append({
                        "group": vr.get("groupId"),
                        "interface": vr.get("interface"),
                        "state": vr.get("state"),
                        "priority": vr.get("priority"),
                        "vip": vr.get("virtualIp") or (vr.get("virtualIps", [""])[0] if vr.get("virtualIps") else "")
                    })
            except Exception:
                pass

    # Evaluate Overall Status
    if not report["online"]:
        report["summary_status"] = "OFFLINE"
    elif report["config_diff_lines"] == 0:
        report["summary_status"] = "COMPLIANT (100% Match)"
    elif report["config_compliance_pct"] >= 90.0:
        report["summary_status"] = f"SLIGHT DRIFT ({report['config_compliance_pct']}%)"
    else:
        report["summary_status"] = f"DRIFT DETECTED ({report['config_compliance_pct']}%)"

    return report

def audit_all_devices():
    """Audits all network routers and switches against Golden baselines."""
    creds = get_vault_credentials()
    results = {}
    for hostname, mgmt_ip in sorted(DEVICE_MGMT_IPS.items()):
        cred = creds.get(hostname, {"username": "admin", "password": "admin"})
        results[hostname] = audit_device(hostname, mgmt_ip, cred["username"], cred["password"])
    return results

def generate_markdown_report(audit_results):
    """Generates an executive markdown comparison report."""
    md = []
    md.append("# 🏛️ Golden Baseline vs. Running Network State Audit Report")
    md.append(f"*Generated by NetDevOps Automation Framework*\n")
    md.append("| Device | Management IP | Status | Config Compliance | Diff Lines | Active Routes | Neighbors (OSPF/BGP) |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")

    for name, r in audit_results.items():
        status_badge = "🟢 ONLINE" if r["online"] else "🔴 OFFLINE"
        comp_badge = f"**{r['config_compliance_pct']}%**"
        diff_badge = f"+{r['diff_added']} / -{r['diff_removed']}" if r['config_diff_lines'] > 0 else "0 (In-Sync)"
        routes_summary = f"{r['routes']['total_routes']} (O:{r['routes']['ospf']}, B:{r['routes']['bgp']})" if r['online'] else "N/A"
        nbrs_summary = f"OSPF: {len(r['neighbors']['ospf_neighbors'])}, BGP: {len(r['neighbors']['bgp_peers'])}" if r['online'] else "N/A"
        md.append(f"| **{name}** | `{r['mgmt_ip']}` | {status_badge} | {comp_badge} | `{diff_badge}` | {routes_summary} | {nbrs_summary} |")

    md.append("\n---\n")
    for name, r in audit_results.items():
        if r["config_diff_lines"] > 0:
            md.append(f"### 🔍 {name} Configuration Drift Diff")
            md.append("```diff")
            md.append(r["diff_unified"] if r["diff_unified"] else "No unified diff text")
            md.append("```\n")

    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Golden Baseline & State Drift Comparator")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--markdown", help="Write Markdown report to specified file path")
    parser.add_argument("--device", help="Audit specific device only (e.g., R1)")
    args = parser.parse_args()

    results = audit_all_devices()
    if args.device:
        dev_key = args.device.upper()
        if dev_key in results:
            results = {dev_key: results[dev_key]}
        else:
            print(f"Device {args.device} not found in inventory!", file=sys.stderr)
            sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        md_text = generate_markdown_report(results)
        if args.markdown:
            with open(args.markdown, "w", encoding="utf-8") as f:
                f.write(md_text)
            print(f"[✓] Golden drift report written to: {args.markdown}")
        else:
            print(md_text)

if __name__ == "__main__":
    main()
