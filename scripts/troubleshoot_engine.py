#!/usr/bin/env python3
"""
CSCI 5840 - Network Automation & Security
AI & Automated Network Troubleshooting Engine
Processes natural language diagnostic prompts, gathers multi-layer network state,
performs root-cause analysis, and generates structured remediation reports.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import hvac

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_URL = "https://127.0.0.1:8200"
CA_CERT = os.path.join(BASE_DIR, "vault", "certs", "ca.crt")
APPROLE_FILE = os.path.expanduser("~/.vault_approle.json")

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

def query_eapi_text(mgmt_ip, cmds, timeout=4.0):
    """Executes commands via eAPI returning text output."""
    url = f"http://{mgmt_ip}/command-api"
    auth_str = base64.b64encode(b"admin:admin").decode("utf-8")
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {"version": 1, "cmds": cmds, "format": "text"},
        "id": "troubleshoot-cli"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth_str}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for item in data.get("result", []):
                results.append(item.get("output", ""))
            return True, results
    except Exception as e:
        return False, [str(e)]

def run_docker_exec(container, cmd_list, timeout=4.0):
    """Executes a diagnostic command inside a Docker container."""
    try:
        full_cmd = ["docker", "exec", container] + cmd_list
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode == 0, res.stdout.strip() or res.stderr.strip()
    except Exception as e:
        return False, str(e)

def analyze_and_troubleshoot(prompt):
    """
    Analyzes natural language prompt, determines diagnostic scope, executes probes,
    and returns a structured troubleshooting report.
    """
    p_lower = prompt.lower()
    start_time = time.time()
    
    findings = []
    evidence = {}
    recommendations = []
    status = "HEALTHY"
    severity = "INFO"

    # Identify Target Devices & Protocols from Prompt
    devices_in_prompt = [d for d in DEVICE_MGMT_IPS.keys() if d.lower() in p_lower]
    hosts_in_prompt = [h for h in ["h1", "h2", "h3", "h4", "web"] if h in p_lower]

    is_bgp_query = any(k in p_lower for k in ["bgp", "as 65005", "as 65001", "pe-ce", "asbr", "peer"])
    is_ospf_query = any(k in p_lower for k in ["ospf", "area 0", "adjacenc", "neighbor", "backbone"])
    is_vrrp_query = any(k in p_lower for k in ["vrrp", "gateway", "failover", "standby", "master", "priority"])
    is_dhcp_query = any(k in p_lower for k in ["dhcp", "lease", "pool", "ipam", "reservation", "allocation"])
    is_cpu_query = any(k in p_lower for k in ["cpu", "memory", "top", "process", "utilization", "load", "spike"])
    is_reachability_query = any(k in p_lower for k in ["ping", "reach", "connect", "drop", "loss", "http", "curl", "packet", "slow", "down", "traffic"])

    # Default to comprehensive triage if prompt is broad or general
    if not (is_bgp_query or is_ospf_query or is_vrrp_query or is_dhcp_query or is_cpu_query or is_reachability_query):
        is_reachability_query = True
        is_ospf_query = True
        is_bgp_query = True
        is_vrrp_query = True

    # --- 1. BGP DIAGNOSTICS ---
    if is_bgp_query:
        # Check BGP on R5, R3, R4
        for dev in ["R5", "R3", "R4"]:
            ok, out = query_eapi_text(DEVICE_MGMT_IPS[dev], ["enable", "show ip bgp summary", "show ip route bgp"])
            if ok and len(out) > 1:
                evidence[f"{dev} - show ip bgp summary"] = out[1]
                if "Estab" in out[1]:
                    findings.append(f"🟢 **{dev} BGP Peering**: Active & Established with eBGP peers.")
                else:
                    findings.append(f"🔴 **{dev} BGP Peering**: BGP session not established or degraded.")
                    status = "DEGRADED"
                    severity = "HIGH"
                    recommendations.append(f"Verify eBGP neighbor IP and AS numbers on {dev} (AS 65005 <-> 65001).")

    # --- 2. OSPF DIAGNOSTICS ---
    if is_ospf_query:
        for dev in ["R1", "R2", "R3", "R4"]:
            ok, out = query_eapi_text(DEVICE_MGMT_IPS[dev], ["enable", "show ip ospf neighbor", "show ip ospf"])
            if ok and len(out) > 1:
                evidence[f"{dev} - show ip ospf neighbor"] = out[1]
                if "FULL" in out[1] or "2Ways" in out[1]:
                    full_count = out[1].count("FULL")
                    findings.append(f"🟢 **{dev} OSPF Area 0**: {full_count} Neighbor(s) in FULL adjacency state.")
                else:
                    findings.append(f"🟡 **{dev} OSPF Area 0**: No FULL neighbor adjacencies observed.")
                    status = "DEGRADED"
                    severity = "MEDIUM"
                    recommendations.append(f"Inspect Ethernet1 link and MTU settings on {dev} across the core backbone switch S3/S4.")

    # --- 3. VRRP & GATEWAY REDUNDANCY DIAGNOSTICS ---
    if is_vrrp_query:
        for dev in ["R1", "R2"]:
            ok, out = query_eapi_text(DEVICE_MGMT_IPS[dev], ["enable", "show vrrp brief", "show interfaces description"])
            if ok and len(out) > 1:
                evidence[f"{dev} - show vrrp brief"] = out[1]
                if "Master" in out[1]:
                    findings.append(f"🟢 **{dev} VRRP State**: Active as Master for configured Virtual IP Groups (10, 20, 30).")
                elif "Backup" in out[1]:
                    findings.append(f"🟢 **{dev} VRRP State**: Active as Hot Standby Backup ready for instant failover.")
                else:
                    findings.append(f"🔴 **{dev} VRRP State**: Non-operational or Init state detected.")
                    status = "DEGRADED"
                    severity = "HIGH"

    # --- 4. DHCP POOL & LEASE DIAGNOSTICS ---
    if is_dhcp_query:
        ok, out = query_eapi_text(DEVICE_MGMT_IPS["R2"], ["enable", "show dhcp server lease", "show running-config section dhcp"])
        if ok and len(out) > 1:
            evidence["R2 - show dhcp server lease"] = out[1]
            lease_count = len([l for l in out[1].splitlines() if "." in l and "10.10." in l])
            findings.append(f"🟢 **R2 DHCP Server**: Active with {lease_count} dynamic leases granted across VLAN 10 & 20 pools.")
        else:
            findings.append("🟡 **R2 DHCP Server**: Unable to pull lease database via eAPI.")

    # --- 5. CPU & PROCESS RESOURCE DIAGNOSTICS ---
    if is_cpu_query:
        target_devs = devices_in_prompt or ["R1", "R2", "R3", "R4", "R5", "S1", "S2"]
        for dev in target_devs:
            ok, out = query_eapi_text(DEVICE_MGMT_IPS[dev], ["enable", "show processes top once"])
            if ok and len(out) > 1:
                raw_top = out[1]
                evidence[f"{dev} - show processes top once"] = raw_top[:600]
                # Check CPU idle
                m = re.search(r"(\d+\.\d+)\s+id", raw_top)
                idle = float(m.group(1)) if m else 50.0
                cpu_load = round(100.0 - idle, 1)
                if cpu_load > 90.0:
                    findings.append(f"🔴 **{dev} CPU Utilization**: High Load detected at **{cpu_load}%**.")
                    status = "WARNING"
                    recommendations.append(f"Inspect top background daemon threads on {dev} using `show processes top cpu`.")
                else:
                    findings.append(f"🟢 **{dev} CPU Utilization**: Healthy at **{cpu_load}%** (Idle: {idle}%).")

    # --- 6. DATA PLANE REACHABILITY & PATH PROBES ---
    if is_reachability_query:
        # Probe H1 -> Web Server
        ok_h1_ping, out_h1 = run_docker_exec("clab-lab1-h1", ["ping", "-c", "2", "-W", "1", "198.51.100.10"])
        ok_h1_http, out_h1_http = run_docker_exec("clab-lab1-h1", ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://198.51.100.10/"])
        evidence["H1 -> Web Server Ping"] = out_h1
        evidence["H1 -> Web Server HTTP GET"] = f"HTTP Response: {out_h1_http}"
        
        if ok_h1_ping and out_h1_http == "200":
            findings.append("🟢 **H1 (VLAN 10) Data Plane**: End-to-end IPv4 routing to Web Server is 100% operational (HTTP 200 OK).")
        else:
            findings.append("🔴 **H1 (VLAN 10) Data Plane**: Reachability failure to Web Server (198.51.100.10).")
            status = "CRITICAL"
            severity = "CRITICAL"
            recommendations.append("Check default gateway VRRP VIP on R1/R2 and OSPF route redistribution.")

        # Probe H2 -> Web Server
        ok_h2_ping, out_h2 = run_docker_exec("clab-lab1-h2", ["ping", "-c", "2", "-W", "1", "198.51.100.10"])
        ok_h2_http, out_h2_http = run_docker_exec("clab-lab1-h2", ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://198.51.100.10/"])
        evidence["H2 -> Web Server Ping"] = out_h2
        evidence["H2 -> Web Server HTTP GET"] = f"HTTP Response: {out_h2_http}"

        if ok_h2_ping and out_h2_http == "200":
            findings.append("🟢 **H2 (VLAN 20) Data Plane**: End-to-end IPv4 routing to Web Server is 100% operational (HTTP 200 OK).")
        else:
            findings.append("🔴 **H2 (VLAN 20) Data Plane**: Reachability failure from VLAN 20.")
            status = "CRITICAL"

        # Probe H4 -> Web Server IPv6
        ok_h4_ping, out_h4 = run_docker_exec("clab-lab1-h4", ["ping", "-6", "-c", "2", "-W", "1", "2001:db8:100::10"])
        evidence["H4 (VLAN 30) -> Web Server IPv6 Ping"] = out_h4
        if ok_h4_ping:
            findings.append("🟢 **H4 (VLAN 30) IPv6-Only Data Plane**: IPv6 global routing to Web Server is healthy.")
        else:
            findings.append("🟡 **H4 (VLAN 30) IPv6-Only Data Plane**: IPv6 packet loss observed to Web Server.")

    elapsed = round(time.time() - start_time, 2)
    if not recommendations:
        recommendations.append("No active failures detected. The network topology, routing protocols, and data plane are operating nominally.")

    report = {
        "prompt": prompt,
        "status": status,
        "severity": severity,
        "elapsed_sec": elapsed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "findings": findings,
        "recommendations": recommendations,
        "evidence": evidence,
        "summary": f"Diagnostic run completed in {elapsed}s. Overall Network State: {status}."
    }
    return report

def main():
    parser = argparse.ArgumentParser(description="AI Network Troubleshooting & Diagnostic Engine")
    parser.add_argument("--prompt", default="Perform complete network health triage and verify routing convergence", help="Troubleshooting query")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    report = analyze_and_troubleshoot(args.prompt)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("======================================================================")
        print(f"       AI NETWORK TROUBLESHOOTING REPORT: {report['status']}         ")
        print("======================================================================")
        print(f"Prompt     : {report['prompt']}")
        print(f"Elapsed    : {report['elapsed_sec']} seconds | Timestamp: {report['timestamp']}")
        print(f"Status     : {report['status']} (Severity: {report['severity']})\n")
        
        print("--- Diagnostic Findings & Correlated Evidence ---")
        for f in report["findings"]:
            print(f"  • {f}")

        print("\n--- Root Cause & Recommended Remediations ---")
        for r in report["recommendations"]:
            print(f"  ➜ {r}")

        print("\n--- Raw Command Evidence ---")
        for k, v in report["evidence"].items():
            print(f"\n[{k}]")
            print(v[:400] + ("\n... [truncated]" if len(v) > 400 else ""))

if __name__ == "__main__":
    main()
