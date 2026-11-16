#!/usr/bin/env python3
"""
NetSleuth Fault Injection & Demo Automation Engine
CSCI 5840 Labs 9-10
Scenarios:
  - interface-down
  - ospf-area-mismatch
  - rip-missing-network
  - bgp-peer-down
  - vlan-trunk-missing
  - varp-gateway-down
  - webserver-down
"""

import sys
import os
import argparse
import subprocess
import time

# Ensure netsleuth is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from netsleuth.remediation.engine import apply_eapi_config

SCENARIOS = {
    "interface-down": {
        "title": "Physical / Administrative Interface Failure (R1 Ethernet2 Down)",
        "device": "R1",
        "inject_cmds": ["interface Ethernet2", "shutdown"],
        "clear_cmds": ["interface Ethernet2", "no shutdown"],
        "category": "Data Plane - Interface"
    },
    "ospf-area-mismatch": {
        "title": "OSPF Area Mismatch on Expansion Link (R4 Ethernet3 Area 99)",
        "device": "R4",
        "inject_cmds": ["interface Ethernet3", "ip ospf area 99"],
        "clear_cmds": ["interface Ethernet3", "ip ospf area 10"],
        "category": "Control Plane - OSPF"
    },
    "rip-missing-network": {
        "title": "RIPv2 Missing Network Advertisement (R1 Network 10.10.0.0/16 Removed)",
        "device": "R1",
        "inject_cmds": ["router rip", "no network 10.10.0.0/16", "no network 10.10.10.0/24", "no network 10.10.20.0/24"],
        "clear_cmds": ["router rip", "network 10.10.0.0/16"],
        "category": "Control Plane - RIP"
    },
    "bgp-peer-down": {
        "title": "eBGP Peering Session Collapse (R5 Peer 172.16.35.1 Shutdown)",
        "device": "R5",
        "inject_cmds": ["router bgp 65005", "neighbor 172.16.35.1 shutdown"],
        "clear_cmds": ["router bgp 65005", "no neighbor 172.16.35.1 shutdown"],
        "category": "Control Plane - BGP"
    },
    "vlan-trunk-missing": {
        "title": "Layer 2 VLAN Trunk Pruned (S1 Trunk Ethernet1 VLAN 10 Removed)",
        "device": "S1",
        "inject_cmds": ["interface Ethernet1", "switchport trunk allowed vlan 20"],
        "clear_cmds": ["interface Ethernet1", "switchport trunk allowed vlan 10,20"],
        "category": "Data Plane - Interface"
    },
    "varp-gateway-down": {
        "title": "VARP First-Hop Virtual Gateway Failure (R1 Ethernet2.10 Shutdown)",
        "device": "R1",
        "inject_cmds": ["interface Ethernet2.10", "shutdown"],
        "clear_cmds": ["interface Ethernet2.10", "no shutdown"],
        "category": "High Availability - VARP"
    },
    "webserver-down": {
        "title": "Application Web Server Process Terminated (Web Server HTTP Down)",
        "device": "web-server",
        "inject_custom": "docker exec clab-lab1-web-server pkill -f python3 || true",
        "clear_custom": "docker exec -d clab-lab1-web-server python3 /server.py",
        "category": "Service - Web Server"
    }
}

def inject_scenario(scenario_name: str) -> bool:
    sc = SCENARIOS.get(scenario_name)
    if not sc:
        print(f"[-] Unknown scenario '{scenario_name}'. Available: {list(SCENARIOS.keys())}")
        return False

    print(f"\n[+] Injecting Fault Scenario: {sc['title']}")
    print(f"    Target Device: {sc['device']} | Category: {sc['category']}")

    if "inject_custom" in sc:
        res = subprocess.run(sc["inject_custom"], shell=True, capture_output=True, text=True)
        ok = (res.returncode == 0)
    else:
        ok, out = apply_eapi_config(sc["device"], sc["inject_cmds"])

    if ok:
        print(f"    [✓] Fault injected successfully into {sc['device']}.")
    else:
        print(f"    [-] Failed to inject fault into {sc['device']}")
    return ok

def clear_scenario(scenario_name: str) -> bool:
    sc = SCENARIOS.get(scenario_name)
    if not sc:
        print(f"[-] Unknown scenario '{scenario_name}'")
        return False

    print(f"\n[*] Clearing Fault Scenario: {sc['title']}")
    if "clear_custom" in sc:
        res = subprocess.run(sc["clear_custom"], shell=True, capture_output=True, text=True)
        ok = (res.returncode == 0)
    else:
        ok, out = apply_eapi_config(sc["device"], sc["clear_cmds"])

    if ok:
        print(f"    [✓] Fault cleared on {sc['device']}. Nominal baseline restored.")
    else:
        print(f"    [-] Failed to clear fault on {sc['device']}")
    return ok

def clear_all():
    print("\n[***] Clearing ALL fault scenarios across the network...")
    for sc_name in SCENARIOS:
        clear_scenario(sc_name)
    print("\n[✓] All scenarios cleared. Network fully converged.")

def main():
    parser = argparse.ArgumentParser(description="NetSleuth Fault Injection & Demo Automation CLI")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), help="Scenario to inject")
    parser.add_argument("--clear", action="store_true", help="Clear the specified scenario or all scenarios")
    args = parser.parse_args()

    if args.clear:
        if args.scenario:
            clear_scenario(args.scenario)
        else:
            clear_all()
    elif args.scenario:
        inject_scenario(args.scenario)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
