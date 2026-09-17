#!/usr/bin/env python3
import subprocess
import sys
import time

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

def test(name, cmd):
    success, stdout, stderr = run_cmd(cmd)
    status = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
    print(f"[{status}] {name}")
    if not success:
        if stderr:
            print(f"       Error: {stderr}")
        elif stdout:
            print(f"       Output: {stdout}")
    return success

print("="*70)
print("   ADVANCED NETWORK AUTOMATION - LAB 1 VERIFICATION TEST SUITE   ")
print("="*70)

results = []

print("\n--- 1. HOST TO INTERNET WEB SERVER CONNECTIVITY ---")
results.append(test("H1 (VLAN 10) -> Web Server IPv4 Ping", "docker exec clab-lab1-h1 ping -c 2 -W 2 198.51.100.10"))
results.append(test("H1 (VLAN 10) -> Web Server HTTP GET", "docker exec clab-lab1-h1 curl -s -m 3 http://198.51.100.10 | grep -q 'Hello World'"))
results.append(test("H2 (VLAN 20) -> Web Server IPv4 Ping", "docker exec clab-lab1-h2 ping -c 2 -W 2 198.51.100.10"))
results.append(test("H2 (VLAN 20) -> Web Server HTTP GET", "docker exec clab-lab1-h2 curl -s -m 3 http://198.51.100.10 | grep -q 'Hello World'"))
results.append(test("H3 (VLAN 10) -> Web Server IPv4 Ping", "docker exec clab-lab1-h3 ping -c 2 -W 2 198.51.100.10"))
results.append(test("H3 (VLAN 10) -> Web Server HTTP GET", "docker exec clab-lab1-h3 curl -s -m 3 http://198.51.100.10 | grep -q 'Hello World'"))
results.append(test("H4 (VLAN 30: IPv6 Only) -> Web Server IPv6 Ping", "docker exec clab-lab1-h4 ping6 -c 2 -W 2 2001:db8:100::10"))
results.append(test("H4 (VLAN 30: IPv6 Only) -> Web Server HTTP GET (IPv6)", "docker exec clab-lab1-h4 curl -6 -s -m 3 http://[2001:db8:100::10] | grep -q 'Hello World'"))

print("\n--- 2. INTER-VLAN & INTRA-VLAN CONNECTIVITY ---")
results.append(test("H1 (VLAN 10) <-> H3 (VLAN 10) Intra-VLAN Ping", "docker exec clab-lab1-h1 ping -c 2 -W 2 10.10.10.103"))
results.append(test("H1 (VLAN 10) <-> H2 (VLAN 20) Inter-VLAN Ping", "docker exec clab-lab1-h1 ping -c 2 -W 2 10.10.20.102"))
results.append(test("H2 (VLAN 20) <-> H3 (VLAN 10) Inter-VLAN Ping", "docker exec clab-lab1-h2 ping -c 2 -W 2 10.10.10.103"))
results.append(test("H1 (VLAN 10) <-> H4 (VLAN 30) IPv6 Ping", "docker exec clab-lab1-h1 ping6 -c 2 -W 2 2001:db8:30::104"))
results.append(test("H2 (VLAN 20) <-> H4 (VLAN 30) IPv6 Ping", "docker exec clab-lab1-h2 ping6 -c 2 -W 2 2001:db8:30::104"))

print("\n--- 3. VLAN 30 IPV6-ONLY ENFORCEMENT CHECK ---")
success, out, _ = run_cmd("docker exec clab-lab1-h4 ip -4 addr show eth1")
vlan30_ipv4_free = (out == "")
status = "\033[92mPASS\033[0m" if vlan30_ipv4_free else "\033[91mFAIL\033[0m"
print(f"[{status}] H4 (VLAN 30) has NO IPv4 address configured (Strict IPv6-Only)")
results.append(vlan30_ipv4_free)

print("\n--- 4. NMAS (NETWORK MANAGEMENT & AUTOMATION STATION) REACHABILITY ---")
results.append(test("NMAS -> Web Server IPv4 Ping", "docker exec clab-lab1-nmas ping -c 2 -W 2 198.51.100.10"))
results.append(test("NMAS -> Web Server IPv6 Ping", "docker exec clab-lab1-nmas ping6 -c 2 -W 2 2001:db8:100::10"))
results.append(test("NMAS -> H1 (VLAN 10) Ping", "docker exec clab-lab1-nmas ping -c 2 -W 2 10.10.10.101"))
results.append(test("NMAS -> H4 (VLAN 30) IPv6 Ping", "docker exec clab-lab1-nmas ping6 -c 2 -W 2 2001:db8:30::104"))

print("\n--- 5. ROUTING PROTOCOL VALIDATIONS ---")
results.append(test("BGP Session R5 <-> R3 (IPv4/IPv6)", "docker exec clab-lab1-r5 FastCli -p 15 -c 'show ip bgp summary' | grep '172.16.35.1' | grep -i 'Estab'"))
results.append(test("BGP Session R5 <-> R4 (IPv4/IPv6)", "docker exec clab-lab1-r5 FastCli -p 15 -c 'show ip bgp summary' | grep '172.16.45.1' | grep -i 'Estab'"))
results.append(test("OSPF Area 0 Adjacencies Established on R1", "docker exec clab-lab1-r1 FastCli -p 15 -c 'show ip ospf neighbor' | grep -q 'FULL'"))
results.append(test("RIPv2 Routes Converged on R1", "docker exec clab-lab1-r1 FastCli -p 15 -c 'show ip rip database' | grep -q '10.10.'"))

print("\n" + "="*70)
passed = sum(1 for r in results if r)
total = len(results)
print(f"   SUMMARY: {passed}/{total} Tests Passed ({(passed/total)*100:.1f}%)")
print("="*70)

if passed == total:
    print("\n\033[92mALL TOPOLOGY AND PROTOCOL REQUIREMENTS MET PERFECTLY!\033[0m\n")
    sys.exit(0)
else:
    print(f"\n\033[91m{total - passed} test(s) failed.\033[0m\n")
    sys.exit(1)
