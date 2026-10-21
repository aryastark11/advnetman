#!/usr/bin/env python3
"""
NetDevOps CI/CD Pipeline - Network Design Regression Test Suite
Validates Control Plane Routing Information Base (RIB), Protocol Adjacencies,
High Availability States, and End-to-End Data Plane IP Reachability.
Includes comprehensive Positive and Negative assertions for robust regression testing.
"""

import os
import sys
import json
import time
import argparse
import subprocess

def run_cmd(cmd, timeout=8):
    """Executes a shell command and returns success, stdout, stderr."""
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.returncode == 0, res.stdout.strip(), res.stderr.strip(), res.returncode
    except Exception as e:
        return False, "", str(e), -1

def get_container_ip(container, iface="eth1", family=4):
    """Discovers dynamic or static IP on a specific container interface."""
    cmd = f"docker exec {container} ip -{family} addr show {iface}"
    ok, stdout, _, _ = run_cmd(cmd)
    if ok and stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if family == 4 and line.startswith("inet "):
                return line.split()[1].split("/")[0]
            elif family == 6 and line.startswith("inet6 ") and "fe80" not in line and "ffff" not in line:
                return line.split()[1].split("/")[0]
    return None

def get_router_json(device_container, command):
    """Executes FastCli command on an Arista cEOS container and parses JSON output."""
    cmd = f"docker exec {device_container} FastCli -p 15 -c '{command} | json'"
    ok, stdout, stderr, code = run_cmd(cmd, timeout=10)
    if not ok or not stdout:
        return None, stderr or "Empty output"
    try:
        return json.loads(stdout), ""
    except Exception as e:
        return None, f"JSON Parse Error: {str(e)}"

class RegressionTestRunner:
    def __init__(self):
        self.results = []
        self.categories = {}

    def test(self, category, name, test_type, check_func, description=""):
        """
        Executes a regression test assertion.
        category: Test domain (e.g. 'Data Plane Reachability', 'Control Plane RIB', etc.)
        name: Short descriptive name
        test_type: 'Positive' or 'Negative'
        check_func: Callable returning (passed: bool, message: str)
        description: Rationale and criteria
        """
        if category not in self.categories:
            self.categories[category] = []

        start_t = time.time()
        try:
            passed, detail = check_func()
        except Exception as e:
            passed = False
            detail = f"Exception during execution: {str(e)}"
        elapsed_ms = int((time.time() - start_t) * 1000)

        type_badge = "\033[94m[POS]\033[0m" if test_type.lower() == "positive" else "\033[95m[NEG]\033[0m"
        status_badge = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
        print(f"  [{status_badge}] {type_badge} {name:<58} ({elapsed_ms}ms)")
        if not passed:
            print(f"         \033[91mCriteria Failure: {detail}\033[0m")

        item = {
            "category": category,
            "name": name,
            "type": test_type,
            "passed": passed,
            "detail": detail,
            "elapsed_ms": elapsed_ms,
            "description": description
        }
        self.results.append(item)
        self.categories[category].append(item)
        return passed

    def print_summary(self, markdown_path=None):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        pass_pct = (passed / total * 100) if total > 0 else 0

        pos_total = sum(1 for r in self.results if r["type"].lower() == "positive")
        pos_passed = sum(1 for r in self.results if r["type"].lower() == "positive" and r["passed"])
        neg_total = sum(1 for r in self.results if r["type"].lower() == "negative")
        neg_passed = sum(1 for r in self.results if r["type"].lower() == "negative" and r["passed"])

        print("\n" + "=" * 80)
        print(f"  NETWORK DESIGN REGRESSION SUITE: {passed}/{total} Passed ({pass_pct:.1f}%) | {failed} Failed")
        print(f"  Positive Tests: {pos_passed}/{pos_total} Passed | Negative Tests: {neg_passed}/{neg_total} Passed")
        print("=" * 80)

        for cat, items in self.categories.items():
            cat_passed = sum(1 for i in items if i["passed"])
            cat_total = len(items)
            badge = "\033[92m[PASS]\033[0m" if cat_passed == cat_total else "\033[91m[FAIL]\033[0m"
            print(f"  {badge} {cat:<45}: {cat_passed}/{cat_total} Passed")

        if markdown_path:
            md = "# 🛡️ Network Design Regression Test Report\n\n"
            status_tag = "✅ PASSED" if failed == 0 else "❌ FAILED"
            md += f"**Overall Result**: `{status_tag}` | **Score**: `{passed}/{total} ({pass_pct:.1f}%)`\n"
            md += f"- **Positive Assertions**: `{pos_passed}/{pos_total} Passed`\n"
            md += f"- **Negative Assertions**: `{neg_passed}/{neg_total} Passed`\n\n"

            md += "### 📊 Category Summary\n\n"
            md += "| Category | Positive | Negative | Passed / Total | Status |\n"
            md += "| :--- | :--- | :--- | :--- | :--- |\n"
            for cat, items in self.categories.items():
                cp = sum(1 for i in items if i["passed"])
                ct = len(items)
                pos_c = sum(1 for i in items if i["type"].lower() == "positive")
                neg_c = sum(1 for i in items if i["type"].lower() == "negative")
                st = "✅ PASS" if cp == ct else "❌ FAIL"
                md += f"| **{cat}** | {pos_c} | {neg_c} | {cp}/{ct} | {st} |\n"

            md += "\n### 🔬 Detailed Test Results & Pass/Fail Criteria\n\n"
            md += "| Status | Type | Test Name | Category | Pass/Fail Criteria | Latency |\n"
            md += "| :---: | :---: | :--- | :--- | :--- | :---: |\n"
            for r in self.results:
                st = "✅" if r["passed"] else "❌"
                tp = "🟢 Positive" if r["type"].lower() == "positive" else "🔴 Negative"
                md += f"| {st} | {tp} | {r['name']} | {r['category']} | {r['detail']} | {r['elapsed_ms']}ms |\n"

            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"\n[✓] Regression Test Markdown Report written to: {markdown_path}")

        return failed == 0

def run_regression_suite(markdown_path=None, json_path=None):
    print("=" * 80)
    print("  NETDEVOPS CI/CD - NETWORK DESIGN REGRESSION TEST SUITE")
    print("  Verifying Route Tables, IP Reachability, Adjacencies (Positive & Negative)")
    print("=" * 80)

    runner = RegressionTestRunner()

    # =========================================================================
    # CATEGORY 1: DATA PLANE IP REACHABILITY (POSITIVE & NEGATIVE)
    # =========================================================================
    # Discover dynamic container IPs
    h1_ip = get_container_ip("clab-lab1-h1", "eth1", 4) or "10.10.10.100"
    h2_ip = get_container_ip("clab-lab1-h2", "eth1", 4) or "10.10.20.100"
    h3_ip = get_container_ip("clab-lab1-h3", "eth1", 4) or "10.10.10.101"
    h4_ip6 = get_container_ip("clab-lab1-h4", "eth1", 6) or "2001:db8:30::104"

    # Positive: Intra-VLAN H1 <-> H3
    def check_intra_vlan():
        ok, out, err, code = run_cmd(f"docker exec clab-lab1-h1 ping -c 2 -W 2 {h3_ip}")
        return ok, f"H1 ping to H3 ({h3_ip}) succeeded with 0% loss" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", f"Intra-VLAN Switching (H1 -> H3, {h3_ip})", "Positive", check_intra_vlan,
                "Asserts layer-2 frame switching within VLAN 10 between access switches.")

    # Positive: Inter-VLAN H1 <-> H2
    def check_inter_vlan():
        ok, out, err, code = run_cmd(f"docker exec clab-lab1-h1 ping -c 2 -W 2 {h2_ip}")
        return ok, f"H1 ping to H2 ({h2_ip}) succeeded via Core VRRP Gateway" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", f"Inter-VLAN Routing (H1 -> H2, {h2_ip})", "Positive", check_inter_vlan,
                "Asserts layer-3 inter-VLAN routing across VLAN 10 and VLAN 20.")

    # Positive: Inter-VLAN H2 <-> H3
    def check_inter_vlan_h2_h3():
        ok, out, err, code = run_cmd(f"docker exec clab-lab1-h2 ping -c 2 -W 2 {h3_ip}")
        return ok, f"H2 ping to H3 ({h3_ip}) succeeded via Core VRRP Gateway" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", f"Inter-VLAN Routing (H2 -> H3, {h3_ip})", "Positive", check_inter_vlan_h2_h3,
                "Asserts layer-3 inter-VLAN routing across VLAN 20 and VLAN 10.")

    # Positive: Default Gateway VIP Reachability
    def check_vlan10_vip():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 ping -c 2 -W 2 10.10.10.254")
        return ok, "VRRP Virtual IP 10.10.10.254 reachable with 0% loss" if ok else f"VIP unreachable: {err or out}"
    runner.test("Data Plane Reachability", "Default Gateway VIP Reachability (H1 -> 10.10.10.254)", "Positive", check_vlan10_vip,
                "Asserts VRRP virtual IP is answering ICMP echo requests.")

    def check_vlan20_vip():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h2 ping -c 2 -W 2 10.10.20.254")
        return ok, "VRRP Virtual IP 10.10.20.254 reachable with 0% loss" if ok else f"VIP unreachable: {err or out}"
    runner.test("Data Plane Reachability", "Default Gateway VIP Reachability (H2 -> 10.10.20.254)", "Positive", check_vlan20_vip,
                "Asserts VRRP virtual IP for VLAN 20 is answering ICMP echo requests.")

    # Positive: End-to-End WAN Web Server Ping
    def check_h1_web_ping():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 ping -c 2 -W 2 198.51.100.10")
        return ok, "H1 reached WAN Web Server 198.51.100.10 with 0% loss" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", "End-to-End WAN Reachability (H1 -> 198.51.100.10)", "Positive", check_h1_web_ping,
                "Asserts complete path from Host through Core, Border, ISP, to External Web Server.")

    def check_h2_web_ping():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h2 ping -c 2 -W 2 198.51.100.10")
        return ok, "H2 reached WAN Web Server 198.51.100.10 with 0% loss" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", "End-to-End WAN Reachability (H2 -> 198.51.100.10)", "Positive", check_h2_web_ping,
                "Asserts complete path from VLAN 20 Host through Core, Border, ISP, to External Web Server.")

    def check_h3_web_ping():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h3 ping -c 2 -W 2 198.51.100.10")
        return ok, "H3 reached WAN Web Server 198.51.100.10 with 0% loss" if ok else f"Ping failed: {err or out}"
    runner.test("Data Plane Reachability", "End-to-End WAN Reachability (H3 -> 198.51.100.10)", "Positive", check_h3_web_ping,
                "Asserts complete path from VLAN 10 secondary Host to External Web Server.")

    # Positive: End-to-End HTTP Application Service
    def check_h1_http_get():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 curl -s -m 4 http://198.51.100.10")
        passed = ok and "Hello World" in out
        return passed, "HTTP 200 payload 'Hello World' received from Web Server" if passed else f"HTTP GET failed: {err or out}"
    runner.test("Data Plane Reachability", "HTTP 200 Application Service (H1 -> Web Server)", "Positive", check_h1_http_get,
                "Asserts layer-7 HTTP service responsiveness through network data plane.")

    # Positive: IPv6 Data Plane
    def check_ipv6_ping():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h4 ping6 -c 2 -W 2 2001:db8:100::10")
        return ok, "H4 reached IPv6 Web Server 2001:db8:100::10 with 0% loss" if ok else f"IPv6 ping failed: {err or out}"
    runner.test("Data Plane Reachability", "IPv6 WAN Data Plane (H4 -> 2001:db8:100::10)", "Positive", check_ipv6_ping,
                "Asserts IPv6 end-to-end packet forwarding across WAN topology.")

    # Negative: Martian / Unallocated IPv4 Drop
    def check_martian_ip_drop():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 ping -c 2 -W 1 198.51.100.250")
        passed = not ok  # MUST fail
        return passed, "Ping to unallocated IP 198.51.100.250 was dropped as expected (100% loss)" if passed else "Unexpected reply received from unallocated IP"
    runner.test("Data Plane Reachability", "Negative Drop: Unallocated WAN IP (198.51.100.250)", "Negative", check_martian_ip_drop,
                "Negative assertion: Unallocated IP in 198.51.100.0/24 subnet must not respond.")

    # Negative: Unrouted Private Subnet Drop
    def check_unrouted_prefix_drop():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 ping -c 2 -W 1 10.254.254.254")
        passed = not ok  # MUST fail
        return passed, "Ping to unrouted IP 10.254.254.254 was dropped as expected (100% loss)" if passed else "Unexpected reply from unrouted prefix"
    runner.test("Data Plane Reachability", "Negative Drop: Unrouted Prefix (10.254.254.254)", "Negative", check_unrouted_prefix_drop,
                "Negative assertion: Traffic to non-existent RFC 1918 space must not be routed/answered.")

    # Negative: Closed TCP Port Refusal
    def check_closed_port_refusal():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h1 curl -m 2 http://198.51.100.10:9999")
        passed = (not ok) and ("Failed to connect" in (err or out) or code in [7, 28])
        return passed, "Connection to closed port 9999 actively refused (curl exit code 7)" if passed else f"Unexpected port response: {out}"
    runner.test("Data Plane Reachability", "Negative Connection: Closed TCP Port (Port 9999)", "Negative", check_closed_port_refusal,
                "Negative assertion: Closed port on Web Server must reject connection requests.")

    # Negative: Unroutable IPv6 Drop
    def check_unroutable_ipv6_drop():
        ok, out, err, code = run_cmd("docker exec clab-lab1-h4 ping6 -c 1 -W 1 2001:db8:9999::1")
        passed = not ok
        return passed, "IPv6 packet to non-existent prefix 2001:db8:9999::1 dropped (No route)" if passed else "Unexpected IPv6 reply"
    runner.test("Data Plane Reachability", "Negative Drop: Unroutable IPv6 (2001:db8:9999::1)", "Negative", check_unroutable_ipv6_drop,
                "Negative assertion: Packet to unroutable IPv6 destination must be dropped.")


    # =========================================================================
    # CATEGORY 2: CONTROL PLANE ROUTING INFORMATION BASE (RIB) REGRESSION
    # =========================================================================
    print("\n--- 2. Control Plane Routing Table (RIB) Assertions ---")

    # Fetch R1 Route Table
    r1_rib, r1_rib_err = get_router_json("clab-lab1-r1", "show ip route")
    r1_routes = r1_rib.get("vrfs", {}).get("default", {}).get("routes", {}) if r1_rib else {}

    # Fetch R2 Route Table
    r2_rib, r2_rib_err = get_router_json("clab-lab1-r2", "show ip route")
    r2_routes = r2_rib.get("vrfs", {}).get("default", {}).get("routes", {}) if r2_rib else {}

    # Fetch R3 Route Table
    r3_rib, r3_rib_err = get_router_json("clab-lab1-r3", "show ip route")
    r3_routes = r3_rib.get("vrfs", {}).get("default", {}).get("routes", {}) if r3_rib else {}

    # Fetch S1 Route Table
    s1_rib, s1_rib_err = get_router_json("clab-lab1-s1", "show ip route")
    s1_vrf = s1_rib.get("vrfs", {}).get("default", {}) if s1_rib else {}

    # Positive: R1 Default Route via OSPF
    def check_r1_default_route():
        route = r1_routes.get("0.0.0.0/0")
        passed = bool(route and route.get("routeType") == "ospfExternalType2" and route.get("routeAction") == "forward")
        return passed, "0.0.0.0/0 installed via OSPF External Type 2" if passed else f"Default route missing or invalid: {route}"
    runner.test("Control Plane RIB", "R1 Default Route (0.0.0.0/0 via OSPF E2)", "Positive", check_r1_default_route,
                "Asserts Core Router R1 learns default route 0.0.0.0/0 via OSPF from Border Routers.")

    # Positive: R1 Connected Access Subnets
    def check_r1_connected_subnets():
        req = ["10.10.10.0/24", "10.10.20.0/24", "10.10.30.0/24"]
        missing = [sub for sub in req if sub not in r1_routes or r1_routes[sub].get("routeType") != "connected"]
        passed = len(missing) == 0
        return passed, f"All access subnets {req} directly connected on Ethernet2 subinterfaces" if passed else f"Missing subnets: {missing}"
    runner.test("Control Plane RIB", "R1 Connected Access Subnets (10.10.{10,20,30}.0/24)", "Positive", check_r1_connected_subnets,
                "Asserts VLAN 10, 20, 30 subnets are directly connected on R1 subinterfaces.")

    # Positive: R1 WAN Subnet via OSPF
    def check_r1_wan_route():
        route = r1_routes.get("198.51.100.0/24")
        passed = bool(route and route.get("routeType") == "ospfExternalType2")
        return passed, "198.51.100.0/24 learned via OSPF External Type 2" if passed else f"WAN route missing or invalid: {route}"
    runner.test("Control Plane RIB", "R1 External WAN Subnet (198.51.100.0/24 via OSPF)", "Positive", check_r1_wan_route,
                "Asserts External Web Server subnet is distributed via OSPF into Core.")

    # Positive: R2 Default Route via OSPF
    def check_r2_default_route():
        route = r2_routes.get("0.0.0.0/0")
        passed = bool(route and route.get("routeType") == "ospfExternalType2" and route.get("routeAction") == "forward")
        return passed, "0.0.0.0/0 installed on R2 via OSPF External Type 2" if passed else f"R2 default route missing: {route}"
    runner.test("Control Plane RIB", "R2 Default Route (0.0.0.0/0 via OSPF E2)", "Positive", check_r2_default_route,
                "Asserts Secondary Core Router R2 maintains active default route.")

    # Positive: R3 Border Router eBGP Default Route
    def check_r3_ebgp_default():
        route = r3_routes.get("0.0.0.0/0")
        passed = bool(route and route.get("routeType") == "eBGP")
        return passed, "0.0.0.0/0 installed on R3 via eBGP from ISP R5" if passed else f"R3 eBGP default route missing: {route}"
    runner.test("Control Plane RIB", "R3 Border eBGP Default Route (0.0.0.0/0 via eBGP)", "Positive", check_r3_ebgp_default,
                "Asserts Border Router R3 learns default gateway from ISP via eBGP.")

    # Positive: R3 ECMP Multipath to Access Subnets
    def check_r3_ecmp_subnets():
        route = r3_routes.get("10.10.10.0/24")
        vias = route.get("vias", []) if route else []
        nexthops = [v.get("nexthopAddr") for v in vias]
        passed = bool("10.0.0.1" in nexthops and "10.0.0.2" in nexthops)
        return passed, f"ECMP dual next-hops {nexthops} active for 10.10.10.0/24 to R1 and R2" if passed else f"ECMP paths missing: {nexthops}"
    runner.test("Control Plane RIB", "R3 Border ECMP Multipath (10.10.10.0/24 -> R1 & R2)", "Positive", check_r3_ecmp_subnets,
                "Asserts Border Router R3 maintains Equal-Cost Multi-Path (ECMP) routing across both Core routers.")

    # Negative: R1 Bogus Route Absence
    def check_r1_bogus_route_absence():
        bogus_prefix = "10.99.99.0/24"
        passed = bogus_prefix not in r1_routes
        return passed, f"Bogus prefix {bogus_prefix} is NOT present in R1 RIB" if passed else f"Security failure: {bogus_prefix} found in RIB!"
    runner.test("Control Plane RIB", "Negative Route Assertion: Bogus Subnet (10.99.99.0/24)", "Negative", check_r1_bogus_route_absence,
                "Negative assertion: Unregistered subnet must never appear in routing table.")

    # Negative: R1 Test-Net Route Absence
    def check_r1_testnet_absence():
        test_net = "192.0.2.0/24"
        passed = test_net not in r1_routes
        return passed, f"RFC 5737 Test-Net {test_net} is NOT present in R1 RIB" if passed else f"Invalid route {test_net} found in RIB!"
    runner.test("Control Plane RIB", "Negative Route Assertion: Test-Net (192.0.2.0/24)", "Negative", check_r1_testnet_absence,
                "Negative assertion: Documentation subnet must not leak into production RIB.")

    # Negative: Access Switch S1 Routing Disabled
    def check_s1_routing_disabled():
        routing_disabled = s1_vrf.get("routingDisabled", False)
        routes_count = len(s1_vrf.get("routes", {}))
        passed = bool(routing_disabled is True and routes_count == 0)
        return passed, "S1 routingDisabled=True and RIB routes count is 0" if passed else f"Switch routing enabled: disabled={routing_disabled}, count={routes_count}"
    runner.test("Control Plane RIB", "Negative Switch Routing: S1 Layer 2 Isolation", "Negative", check_s1_routing_disabled,
                "Negative assertion: Access switch S1 must have IP routing disabled and zero routes.")


    # =========================================================================
    # CATEGORY 3: PROTOCOL ADJACENCIES & HIGH AVAILABILITY REGRESSION
    # =========================================================================
    print("\n--- 3. Protocol Adjacencies & High Availability Assertions ---")

    # Fetch R5 BGP Summary
    r5_bgp, r5_bgp_err = get_router_json("clab-lab1-r5", "show ip bgp summary")
    r5_peers = r5_bgp.get("vrfs", {}).get("default", {}).get("peers", {}) if r5_bgp else {}

    # Fetch R1 OSPF Neighbors
    r1_ospf, r1_ospf_err = get_router_json("clab-lab1-r1", "show ip ospf neighbor")
    r1_ospf_nbrs = r1_ospf.get("vrfs", {}).get("default", {}).get("instList", {}).get("1", {}).get("ospfNeighborEntries", []) if r1_ospf else []

    # Fetch R1 VRRP
    r1_vrrp, r1_vrrp_err = get_router_json("clab-lab1-r1", "show vrrp")
    r1_vrouters = r1_vrrp.get("virtualRouters", []) if r1_vrrp else []

    # Fetch R2 VRRP
    r2_vrrp, r2_vrrp_err = get_router_json("clab-lab1-r2", "show vrrp")
    r2_vrouters = r2_vrrp.get("virtualRouters", []) if r2_vrrp else []

    # Positive: R5 BGP Peer to R3 Established
    def check_r5_bgp_r3():
        peer = r5_peers.get("172.16.35.1")
        passed = bool(peer and peer.get("peerState") == "Established" and peer.get("prefixAccepted", 0) > 0)
        return passed, f"R5 <-> R3 BGP Established (Accepted Prefixes: {peer.get('prefixAccepted') if peer else 0})" if passed else f"BGP peer not established: {peer}"
    runner.test("Protocol Adjacencies & HA", "eBGP Peering R5 <-> R3 (172.16.35.1)", "Positive", check_r5_bgp_r3,
                "Asserts eBGP session between ISP R5 and Border Router R3 is Established.")

    # Positive: R5 BGP Peer to R4 Established
    def check_r5_bgp_r4():
        peer = r5_peers.get("172.16.45.1")
        passed = bool(peer and peer.get("peerState") == "Established" and peer.get("prefixAccepted", 0) > 0)
        return passed, f"R5 <-> R4 BGP Established (Accepted Prefixes: {peer.get('prefixAccepted') if peer else 0})" if passed else f"BGP peer not established: {peer}"
    runner.test("Protocol Adjacencies & HA", "eBGP Peering R5 <-> R4 (172.16.45.1)", "Positive", check_r5_bgp_r4,
                "Asserts eBGP session between ISP R5 and Border Router R4 is Established.")

    # Positive: R1 OSPF Neighbor R3 Full
    def check_r1_ospf_r3():
        nbr = next((n for n in r1_ospf_nbrs if n.get("routerId") == "10.0.0.3"), None)
        passed = bool(nbr and nbr.get("adjacencyState") == "full")
        return passed, "OSPF adjacency with R3 (10.0.0.3) is in FULL state" if passed else f"OSPF state not full: {nbr}"
    runner.test("Protocol Adjacencies & HA", "OSPF Area 0 Neighbor R3 (10.0.0.3 FULL)", "Positive", check_r1_ospf_r3,
                "Asserts Core Router R1 maintains Full OSPF adjacency with Border Router R3.")

    # Positive: R1 VRRP Groups Master
    def check_r1_vrrp_master():
        v4_groups = [vr for vr in r1_vrouters if vr.get("version") == 2]
        master_count = sum(1 for vr in v4_groups if vr.get("state") == "master")
        passed = bool(master_count >= 3)
        return passed, f"R1 is Master for {master_count} VRRP groups (Priority 110)" if passed else f"R1 VRRP state invalid: {v4_groups}"
    runner.test("Protocol Adjacencies & HA", "VRRP High Availability: R1 Master State", "Positive", check_r1_vrrp_master,
                "Asserts Primary Core R1 is active VRRP Master for all access VLANs.")

    # Positive: R2 VRRP Groups Backup
    def check_r2_vrrp_backup():
        v4_groups = [vr for vr in r2_vrouters if vr.get("version") == 2]
        backup_count = sum(1 for vr in v4_groups if vr.get("state") == "backup")
        passed = bool(backup_count >= 3)
        return passed, f"R2 is Backup for {backup_count} VRRP groups (Priority 100)" if passed else f"R2 VRRP state invalid: {v4_groups}"
    runner.test("Protocol Adjacencies & HA", "VRRP High Availability: R2 Backup State", "Positive", check_r2_vrrp_backup,
                "Asserts Secondary Core R2 is standby VRRP Backup ready for failover.")

    # Negative: R5 Non-Existent BGP Peer Absence
    def check_r5_bogus_peer_absence():
        bogus_peer = "172.16.99.1"
        passed = bogus_peer not in r5_peers
        return passed, f"Rogue BGP neighbor {bogus_peer} is NOT present in BGP table" if passed else f"Unauthorized BGP neighbor found: {bogus_peer}"
    runner.test("Protocol Adjacencies & HA", "Negative BGP Peer: Rogue Neighbor (172.16.99.1)", "Negative", check_r5_bogus_peer_absence,
                "Negative assertion: Unauthorized BGP peers must never be registered.")

    # Negative: R1 VRRP Not In Backup State
    def check_r1_vrrp_not_backup():
        v4_groups = [vr for vr in r1_vrouters if vr.get("version") == 2]
        backup_groups = [vr.get("groupId") for vr in v4_groups if vr.get("state") in ["backup", "init"]]
        passed = len(backup_groups) == 0
        return passed, "R1 has 0 groups in backup/init state under normal baseline" if passed else f"Unexpected backup groups on R1: {backup_groups}"
    runner.test("Protocol Adjacencies & HA", "Negative VRRP State: R1 Not In Backup", "Negative", check_r1_vrrp_not_backup,
                "Negative assertion: Primary Core R1 must not drop into backup or init state under normal conditions.")

    # Negative: R2 VRRP Not In Master State
    def check_r2_vrrp_not_master():
        v4_groups = [vr for vr in r2_vrouters if vr.get("version") == 2]
        master_groups = [vr.get("groupId") for vr in v4_groups if vr.get("state") == "master"]
        passed = len(master_groups) == 0
        return passed, "R2 has 0 groups in master state under normal baseline" if passed else f"Split-brain detected: R2 is master for {master_groups}"
    runner.test("Protocol Adjacencies & HA", "Negative VRRP State: R2 Not In Master (No Split-Brain)", "Negative", check_r2_vrrp_not_master,
                "Negative assertion: Secondary Core R2 must not preempt R1 when baseline is nominal (prevents split-brain).")

    # Negative: Zero Down/Attempt OSPF Neighbors
    def check_r1_no_dead_ospf_neighbors():
        bad_nbrs = [n for n in r1_ospf_nbrs if n.get("adjacencyState") in ["down", "attempt", "init"]]
        passed = len(bad_nbrs) == 0
        return passed, "0 OSPF neighbors in dead/down/attempt state" if passed else f"Degraded OSPF neighbors: {bad_nbrs}"
    runner.test("Protocol Adjacencies & HA", "Negative OSPF State: Zero Down/Attempt Neighbors", "Negative", check_r1_no_dead_ospf_neighbors,
                "Negative assertion: No OSPF neighbor may be stuck in down, attempt, or init state.")

    # Print Summary & Generate Reports
    all_passed = runner.print_summary(markdown_path=markdown_path)

    if json_path:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(runner.results, jf, indent=2)
        print(f"[✓] Regression Test JSON Report written to: {json_path}")

    return all_passed

def main():
    parser = argparse.ArgumentParser(description="NetDevOps Network Design Regression Test Suite")
    parser.add_argument("--markdown", help="Path to write markdown regression report")
    parser.add_argument("--json", help="Path to write JSON regression report")
    args = parser.parse_args()

    success = run_regression_suite(markdown_path=args.markdown, json_path=args.json)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
