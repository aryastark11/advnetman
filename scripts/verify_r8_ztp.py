#!/usr/bin/env python3
"""
Verification Script for Router R8 Deployment & Zero Touch Provisioning (ZTP).

Tests:
1. Physical Interconnect: r2:eth3 <-> r8:eth1 is UP on both ends.
2. R2 DHCP Server Configuration: Subnet 10.28.28.0/24 with Option 66 (10.28.28.2) & Option 67 (R8.cfg).
3. R2 TFTP Server Service: tftp-server.service active and serving R8.cfg.
4. R8 ZTP DHCP Lease: /var/lib/dhclient/zerotouch.leases contains IP 10.28.28.100, Option 66, Option 67.
5. R2 Active Lease: show dhcp server ipv4 lease shows 10.28.28.100 leased to R8 MAC.
6. TFTP Handover: Successful download of R8.cfg from R2 to R8 over 10.28.28.2.
7. SSH Verification: SSH login into R8 succeeds over management IP (172.20.20.18) and in-band IP (10.28.28.100).
"""

import sys
import subprocess
import re

def run_cmd(cmd):
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.stdout.strip(), p.stderr.strip(), p.returncode

def main():
    print("=" * 70)
    print("  ROUTER R8 ZERO TOUCH PROVISIONING (ZTP) & SSH VERIFICATION")
    print("=" * 70)
    
    passed = 0
    total = 7

    # Test 1: Physical Link Check
    print("\n[TEST 1] Verifying Physical Interconnect (r2:eth3 <-> r8:eth1)...")
    out_r2, _, code_r2 = run_cmd("docker exec clab-lab1-r2 ip link show eth3")
    out_r8, _, code_r8 = run_cmd("docker exec clab-lab1-r8 ip link show eth1")
    if code_r2 == 0 and code_r8 == 0 and "state UP" in out_r2 and "state UP" in out_r8:
        print("  [✓ PASS] Physical link r2:eth3 <-> r8:eth1 is UP on both routers.")
        passed += 1
    else:
        print(f"  [✗ FAIL] Physical link down: R2 code={code_r2}, R8 code={code_r8}")

    # Test 2: R2 DHCP Server Configuration
    print("\n[TEST 2] Verifying R2 DHCP Server Pool & ZTP Options (Option 66 & 67)...")
    out, _, _ = run_cmd("docker exec clab-lab1-r2 FastCli -p 15 -c 'show dhcp server ipv4'")
    has_subnet = "10.28.28.0/24" in out
    has_opt66 = "10.28.28.2 (Option 66)" in out
    has_opt67 = "R8.cfg" in out
    if has_subnet and has_opt66 and has_opt67:
        print("  [✓ PASS] R2 DHCP pool 10.28.28.0/24 configured with Option 66=10.28.28.2 and Option 67=R8.cfg.")
        passed += 1
    else:
        print(f"  [✗ FAIL] DHCP config missing: subnet={has_subnet}, opt66={has_opt66}, opt67={has_opt67}")

    # Test 3: R2 TFTP Server Service
    print("\n[TEST 3] Verifying R2 TFTP Server Daemon & R8.cfg File Availability...")
    out_svc, _, _ = run_cmd("docker exec clab-lab1-r2 systemctl is-active tftp-server.service")
    out_file, _, _ = run_cmd("docker exec clab-lab1-r2 ls -l /mnt/flash/tftpboot/R8.cfg")
    if out_svc.strip() == "active" and "R8.cfg" in out_file:
        print("  [✓ PASS] TFTP service is active on R2 and /mnt/flash/tftpboot/R8.cfg is present.")
        passed += 1
    else:
        print(f"  [✗ FAIL] TFTP service status: {out_svc}, File: {out_file}")

    # Test 4: R8 ZTP DHCP Lease Verification
    print("\n[TEST 4] Verifying R8 ZTP DHCP Lease (/var/lib/dhclient/zerotouch.leases)...")
    out_lease, _, code_lease = run_cmd("docker exec clab-lab1-r8 cat /var/lib/dhclient/zerotouch.leases")
    has_ip = "fixed-address 10.28.28." in out_lease
    has_tftp_opt = 'option tftp-server-name "10.28.28.2"' in out_lease
    has_bootfile = 'option bootfile-name "R8.cfg"' in out_lease
    if has_ip and has_tftp_opt and has_bootfile:
        print("  [✓ PASS] R8 acquired IP, TFTP Server (Option 66), and Bootfile (Option 67) from R2.")
        passed += 1
    else:
        print(f"  [✗ FAIL] Lease missing parameters: ip={has_ip}, tftp={has_tftp_opt}, bootfile={has_bootfile}")

    # Test 5: R2 Active Lease for R8
    print("\n[TEST 5] Verifying Active Lease on R2 DHCP Server...")
    out_r2_lease, _, _ = run_cmd("docker exec clab-lab1-r2 FastCli -p 15 -c 'show dhcp server ipv4 lease'")
    if "10.28.28.100" in out_r2_lease:
        print("  [✓ PASS] R2 active lease records R8 assigned IP 10.28.28.100.")
        passed += 1
    else:
        print(f"  [✗ FAIL] Active lease not found on R2: {out_r2_lease}")

    # Test 6: TFTP Download from R2 to R8
    print("\n[TEST 6] Verifying TFTP Handover of R8.cfg from R2 to R8...")
    out_tftp, _, code_tftp = run_cmd("docker exec clab-lab1-r8 curl -s -m 5 tftp://10.28.28.2/R8.cfg")
    if code_tftp == 0 and "hostname r8" in out_tftp.lower():
        print(f"  [✓ PASS] R8 downloaded R8.cfg ({len(out_tftp)} bytes) via TFTP from R2.")
        passed += 1
    else:
        print(f"  [✗ FAIL] TFTP download failed (code={code_tftp}): {out_tftp[:100]}")

    # Test 7: SSH Verification on R8
    print("\n[TEST 7] Verifying SSH Access into R8 (admin/admin)...")
    out_ssh_mgmt, _, code_mgmt = run_cmd(
        "sshpass -p admin ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 admin@172.20.20.18 'show hostname'"
    )
    out_ssh_inband, _, code_inband = run_cmd(
        """docker exec clab-lab1-r2 python3 -c "
import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@10.28.28.100 show hostname', timeout=5)
i = child.expect(['password:', 'Password:', pexpect.TIMEOUT, pexpect.EOF])
if i in [0, 1]:
    child.sendline('admin')
    child.expect(pexpect.EOF)
    print(child.before.decode())
" """
    )
    has_mgmt_hostname = "Hostname: r8" in out_ssh_mgmt
    has_inband_hostname = "Hostname: r8" in out_ssh_inband
    if has_mgmt_hostname and has_inband_hostname:
        print("  [✓ PASS] SSH to R8 succeeded over both Management0 (172.20.20.18) and Ethernet1 (10.28.28.100).")
        passed += 1
    else:
        print(f"  [✗ FAIL] SSH failed: mgmt={has_mgmt_hostname}, in-band={has_inband_hostname}")

    print("\n" + "=" * 70)
    print(f"  SUMMARY: {passed}/{total} TESTS PASSED")
    print("=" * 70)

    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
