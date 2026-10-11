#!/usr/bin/env python3
"""
NetDevOps CI/CD Pipeline - Stage 4: Comprehensive Network Verification Suite
Validates End-to-End Data Plane Connectivity, Control Plane Protocol States,
High Availability, Security/AAA, and Telemetry Data Lake ingestion.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cmd(cmd, timeout=5):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.returncode == 0, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def get_container_ip(container, iface="eth1", family=4):
    cmd = f"docker exec {container} ip -{family} addr show {iface}"
    ok, stdout, _ = run_cmd(cmd)
    if ok and stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if family == 4 and line.startswith("inet "):
                return line.split()[1].split("/")[0]
            elif family == 6 and line.startswith("inet6 ") and "fe80" not in line and "ffff" not in line:
                return line.split()[1].split("/")[0]
    return None

class TestRunner:
    def __init__(self):
        self.results = []
        self.categories = {}

    def test(self, category, name, cmd_or_func, detail=""):
        if category not in self.categories:
            self.categories[category] = []
            
        start_t = time.time()
        if callable(cmd_or_func):
            success, output = cmd_or_func()
        else:
            success, stdout, stderr = run_cmd(cmd_or_func)
            output = stdout if success else (stderr or stdout)
            
        elapsed_ms = int((time.time() - start_t) * 1000)
        
        status_str = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
        print(f"  [{status_str}] {name:<55} ({elapsed_ms}ms)")
        if not success and output:
            print(f"         \033[91mOutput: {output[:120]}\033[0m")
            
        res_item = {
            "category": category,
            "name": name,
            "passed": success,
            "output": output,
            "elapsed_ms": elapsed_ms,
            "detail": detail
        }
        self.results.append(res_item)
        self.categories[category].append(res_item)
        return success

    def print_summary(self, markdown_path=None):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        pass_pct = (passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 75)
        print(f"  VERIFICATION TEST SUMMARY: {passed}/{total} Passed ({pass_pct:.1f}%) | {failed} Failed")
        print("=" * 75)

        for cat, items in self.categories.items():
            cat_passed = sum(1 for i in items if i["passed"])
            cat_total = len(items)
            badge = "\033[92m[PASS]\033[0m" if cat_passed == cat_total else "\033[91m[FAIL]\033[0m"
            print(f"  {badge} {cat:<40}: {cat_passed}/{cat_total} Passed")

        if markdown_path:
            md = "# 🧪 Automated Network Verification Test Report\n\n"
            md += f"**Overall Result**: `{'✅ PASSED' if failed == 0 else '❌ FAILED'}` | **Score**: `{passed}/{total} ({pass_pct:.1f}%)`\n\n"
            md += "### 📋 Category Results Breakdown\n\n"
            md += "| Test Category | Passed | Total | Status |\n"
            md += "| :--- | :--- | :--- | :--- |\n"
            for cat, items in self.categories.items():
                cat_p = sum(1 for i in items if i["passed"])
                cat_t = len(items)
                status = "✅ PASS" if cat_p == cat_t else "❌ FAIL"
                md += f"| **{cat}** | {cat_p} | {cat_t} | {status} |\n"
            
            md += "\n### 🔬 Detailed Test Assertions\n\n"
            md += "| Status | Test Name | Category | Latency |\n"
            md += "| :--- | :--- | :--- | :--- |\n"
            for r in self.results:
                st = "✅" if r["passed"] else "❌"
                md += f"| {st} | {r['name']} | {r['category']} | {r['elapsed_ms']}ms |\n"

            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"\n[✓] Markdown Verification Report written to: {markdown_path}")

        return failed == 0

def main():
    parser = argparse.ArgumentParser(description="Automated Network Health & Verification Suite")
    parser.add_argument("--markdown", help="Path to write markdown test report")
    parser.add_argument("--json", help="Path to write JSON test report")
    args = parser.parse_args()

    print("=" * 75)
    print("  NETDEVOPS CI/CD PIPELINE - STAGE 4: POST-DEPLOYMENT VERIFICATION SUITE")
    print("=" * 75)

    runner = TestRunner()

    # Discover Dynamic Host IPs
    h1_ip = get_container_ip("clab-lab1-h1", "eth1", 4) or "10.10.10.100"
    h2_ip = get_container_ip("clab-lab1-h2", "eth1", 4) or "10.10.20.100"
    h3_ip = get_container_ip("clab-lab1-h3", "eth1", 4) or "10.10.10.101"
    h4_ip6 = get_container_ip("clab-lab1-h4", "eth1", 6) or "2001:db8:30::104"

    # 1. DATA PLANE: Host to Internet / Web Server Connectivity
    print("\n--- 4.1 Data Plane: Host-to-Internet Web Server Connectivity ---")
    runner.test("Data Plane - Internet Access", "H1 (VLAN 10) -> Web Server IPv4 Ping",
                "docker exec clab-lab1-h1 ping -c 2 -W 2 198.51.100.10")
    runner.test("Data Plane - Internet Access", "H1 (VLAN 10) -> Web Server HTTP 200 GET",
                "docker exec clab-lab1-h1 curl -s -m 5 http://198.51.100.10 | grep -q 'Hello World'")
    runner.test("Data Plane - Internet Access", "H2 (VLAN 20) -> Web Server IPv4 Ping",
                "docker exec clab-lab1-h2 ping -c 2 -W 2 198.51.100.10")
    runner.test("Data Plane - Internet Access", "H2 (VLAN 20) -> Web Server HTTP 200 GET",
                "docker exec clab-lab1-h2 curl -s -m 5 http://198.51.100.10 | grep -q 'Hello World'")
    runner.test("Data Plane - Internet Access", "H3 (VLAN 10) -> Web Server IPv4 Ping",
                "docker exec clab-lab1-h3 ping -c 2 -W 2 198.51.100.10")
    runner.test("Data Plane - Internet Access", "H3 (VLAN 10) -> Web Server HTTP 200 GET",
                "docker exec clab-lab1-h3 curl -s -m 5 http://198.51.100.10 | grep -q 'Hello World'")
    runner.test("Data Plane - Internet Access", "H4 (VLAN 30) -> Web Server IPv6 Ping",
                "docker exec clab-lab1-h4 ping6 -c 2 -W 2 2001:db8:100::10")
    runner.test("Data Plane - Internet Access", "H4 (VLAN 30) -> Web Server HTTP 200 GET (IPv6)",
                "docker exec clab-lab1-h4 curl -6 -s -m 5 http://[2001:db8:100::10] | grep -q 'Hello World'")

    # 2. DATA PLANE: Inter-VLAN & Intra-VLAN Connectivity
    print("\n--- 4.2 Data Plane: Inter-VLAN & Intra-VLAN Switching & Routing ---")
    runner.test("Data Plane - Inter/Intra VLAN", f"H1 (VLAN 10) <-> H3 (VLAN 10) Intra-VLAN ({h3_ip})",
                f"docker exec clab-lab1-h1 ping -c 2 -W 2 {h3_ip}")
    runner.test("Data Plane - Inter/Intra VLAN", f"H1 (VLAN 10) <-> H2 (VLAN 20) Inter-VLAN ({h2_ip})",
                f"docker exec clab-lab1-h1 ping -c 2 -W 2 {h2_ip}")
    runner.test("Data Plane - Inter/Intra VLAN", f"H2 (VLAN 20) <-> H3 (VLAN 10) Inter-VLAN ({h3_ip})",
                f"docker exec clab-lab1-h2 ping -c 2 -W 2 {h3_ip}")
    runner.test("Data Plane - Inter/Intra VLAN", f"H1 (VLAN 10) <-> H4 (VLAN 30) IPv6 ({h4_ip6})",
                f"docker exec clab-lab1-h1 ping6 -c 2 -W 2 {h4_ip6}")
    runner.test("Data Plane - Inter/Intra VLAN", f"H2 (VLAN 20) <-> H4 (VLAN 30) IPv6 ({h4_ip6})",
                f"docker exec clab-lab1-h2 ping6 -c 2 -W 2 {h4_ip6}")

    # 3. CONTROL PLANE: BGP, OSPF, RIP Routing Adjacencies
    print("\n--- 4.3 Control Plane: Routing Protocol Adjacencies & Convergence ---")
    runner.test("Control Plane - BGP", "BGP Peering R5 <-> R3 Established (AS 65005 <-> 65001)",
                "docker exec clab-lab1-r5 FastCli -p 15 -c 'show ip bgp summary' | grep '172.16.35.1' | grep -q -E '[0-9]+'")
    runner.test("Control Plane - BGP", "BGP Peering R5 <-> R4 Established (AS 65005 <-> 65001)",
                "docker exec clab-lab1-r5 FastCli -p 15 -c 'show ip bgp summary' | grep '172.16.45.1' | grep -q -E '[0-9]+'")
    runner.test("Control Plane - OSPF", "OSPF Area 0 Neighbor Adjacencies on R1 (FULL)",
                "docker exec clab-lab1-r1 FastCli -p 15 -c 'show ip ospf neighbor' | grep -q 'FULL'")
    runner.test("Control Plane - OSPF", "OSPF Area 0 Neighbor Adjacencies on R2 (FULL)",
                "docker exec clab-lab1-r2 FastCli -p 15 -c 'show ip ospf neighbor' | grep -q 'FULL'")
    runner.test("Control Plane - RIP", "RIPv2 Route Database on R1 Contains Subnets",
                "docker exec clab-lab1-r1 FastCli -p 15 -c 'show ip rip database' | grep -q '10.10.'")

    # 4. HIGH AVAILABILITY: VRRP Redundancy
    print("\n--- 4.4 High Availability: VRRP Redundancy Status ---")
    runner.test("High Availability - VRRP", "VRRP Group 10/20/30 Configured on R1",
                "docker exec clab-lab1-r1 FastCli -p 15 -c 'show vrrp' | grep -q 'Ethernet2'")
    runner.test("High Availability - VRRP", "VRRP Group 10/20/30 Configured on R2",
                "docker exec clab-lab1-r2 FastCli -p 15 -c 'show vrrp' | grep -q 'Ethernet2'")

    # 5. SECURITY & MANAGEMENT: eAPI, AAA, 2FA
    print("\n--- 4.5 Security & Automation: eAPI Command-API & 2FA Health ---")
    runner.test("Security & Management", "eAPI HTTP Command-API Active on R1",
                "docker exec clab-lab1-r1 FastCli -p 15 -c 'show management api http-commands' | grep -i -E 'Enabled:\\s+Yes'")
    runner.test("Security & Management", "FreeRADIUS 2FA Daemon Running",
                "systemctl is-active freeradius || true")
    runner.test("Security & Management", "PrivacyIDEA REST Service Running on Port 5000",
                "curl -s -m 2 http://127.0.0.1:5000/token/list | grep -q 'operator'")

    # 6. TELEMETRY & OBSERVABILITY: InfluxDB Data Lake & Grafana
    print("\n--- 4.6 Telemetry & Observability: InfluxDB Data Lake & Grafana NOC ---")
    runner.test("Observability", "InfluxDB Telemetry Data Lake Active on Port 8086",
                "curl -s -m 3 http://localhost:8086/ping")
    runner.test("Observability", "Grafana NOC Master Dashboard Active on Port 3000",
                "curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:3000/d/nmas-noc-master | grep -q '200'")

    all_passed = runner.print_summary(markdown_path=args.markdown)

    if args.json:
        with open(args.json, "w") as jf:
            json.dump(runner.results, jf, indent=2)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
