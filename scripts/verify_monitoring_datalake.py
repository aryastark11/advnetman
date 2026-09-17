import subprocess
import sys
import json

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

def test(name, cmd_or_func):
    if callable(cmd_or_func):
        try:
            success, msg = cmd_or_func()
        except Exception as e:
            success, msg = False, str(e)
    else:
        success, stdout, stderr = run_cmd(cmd_or_func)
        msg = stdout if success else (stderr or stdout)

    status = "[92mPASS[0m" if success else "[91mFAIL[0m"
    print(f"[{status}] {name}")
    if not success and msg:
        print(f"       Details: {msg[:160]}")
    return success

print("="*75)
print("   LABS 2 & 3: MONITORING, STREAMING TELEMETRY & DATA LAKE VERIFICATION   ")
print("="*75)

results = []

print("\n--- OBJECTIVE 1: SNMP MONITORING & SYSLOG EVENTS ---")
def test_snmp_polls():
    success, out, _ = run_cmd("docker exec clab-lab1-nmas snmpget -v 2c -c public -t 2 10.0.0.1 1.3.6.1.2.1.1.5.0")
    return success and "r1" in out, out
results.append(test("SNMP Polling on Core Router R1 (sysName OID 1.3.6.1.2.1.1.5.0)", test_snmp_polls))

def test_snmp_uptime():
    success, out, _ = run_cmd("docker exec clab-lab1-nmas snmpget -v 2c -c public -t 2 10.0.0.1 1.3.6.1.2.1.1.3.0")
    return success and ("Timeticks" in out or "sysUpTime" in out), out
results.append(test("SNMP Polling System & Uptime OID on R1", test_snmp_uptime))

def test_snmp_traps_in_datalake():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/traps"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) > 0, f"Total traps received: {len(data)}"
    return False, out
results.append(test("SNMP Traps Received & Logged in NMAS Data Lake", test_snmp_traps_in_datalake))

def test_syslog_in_datalake():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/syslog"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) > 0, f"Total syslog events: {len(data)}"
    return False, out
results.append(test("Syslog Events Ingested into NMAS Data Lake", test_syslog_in_datalake))

def test_critical_syslogs():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/syslog/critical"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) >= 1, f"Critical syslog events: {len(data)}"
    return False, out
results.append(test("Critical Syslog Alert Isolation & Indexing", test_critical_syslogs))

print("\n--- OBJECTIVE 2: STREAMING TELEMETRY & NETCONF STATE ---")
def test_grpc_gnmi_capabilities():
    cmd = "docker exec clab-lab1-nmas gnmic -a 172.20.20.11:6030 -u admin -p admin --insecure capabilities"
    success, out, _ = run_cmd(cmd)
    return success and "openconfig" in out, "gNMI gRPC capabilities retrieved"
results.append(test("gRPC / gNMI Server Active on Core Router R1 (Port 6030)", test_grpc_gnmi_capabilities))

def test_grpc_gnmi_get():
    cmd = "docker exec clab-lab1-nmas gnmic -a 172.20.20.11:6030 -u admin -p admin --insecure --encoding json_ietf get --path /system/config/hostname"
    success, out, _ = run_cmd(cmd)
    return success and '"system/config/hostname": "r1"' in out, "gNMI get returned system hostname"
results.append(test("gRPC / gNMI OpenConfig State Query (get /system/config/hostname)", test_grpc_gnmi_get))

def test_grpc_in_datalake():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/grpc"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) > 0, f"gRPC telemetry records: {len(data)}"
    return False, out
results.append(test("gRPC Streaming Telemetry Ingested into NMAS Data Lake", test_grpc_in_datalake))

def test_telemetry_in_datalake():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/telemetry"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) > 0, f"Telemetry stream snapshots: {len(data)}"
    return False, out
results.append(test("Streaming Telemetry Snapshots Ingested into Data Lake", test_telemetry_in_datalake))

def test_netconf_state_in_datalake():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/netconf"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) > 0, f"NetConf state snapshots: {len(data)}"
    return False, out
results.append(test("NetConf / OpenConfig Interface State Stored in Data Lake", test_netconf_state_in_datalake))

print("\n--- OBJECTIVE 3: DATA LAKE, ISOLATED BACKUP NODE & 7-DAY RETENTION ---")
def test_datalake_storage_partitions():
    success, out, _ = run_cmd("docker exec clab-lab1-nmas ls -1 /opt/nmas/datalake")
    required = ["snmp", "traps", "syslog", "telemetry", "netconf", "grpc", "datalake.db"]
    found_all = all(r in out for r in required)
    return success and found_all, f"Found partitions: {out.split()}"
results.append(test("NMAS Data Lake Directory Partitions & SQLite DB Initialized", test_datalake_storage_partitions))

def test_nmas_to_backup_link():
    success, out, _ = run_cmd("docker exec clab-lab1-nmas ping -c 2 -W 1 10.99.99.2")
    return success, out
results.append(test("NMAS Dedicated Point-to-Point Link to Backup Node (10.99.99.1 -> 10.99.99.2)", test_nmas_to_backup_link))

def test_backup_isolation():
    s1, out1, _ = run_cmd("docker exec clab-lab1-h1 ping -c 1 -W 1 10.99.99.2 || true")
    s2, out2, _ = run_cmd("docker exec clab-lab1-r1 ping 10.99.99.2 -c 1 -t 1 || true")
    isolated = ("Destination Net Unreachable" in out1 or "100% packet loss" in out1) and ("Time to live exceeded" in out2 or "100% packet loss" in out2)
    return isolated, "Backup node is completely unreachable from other endpoints and routers."
results.append(test("Backup Node Security Isolation (Accessible ONLY by NMAS)", test_backup_isolation))

def test_backup_synchronization():
    success, out, _ = run_cmd("docker exec clab-lab1-backup-server ls -1 /opt/backup/datalake")
    required = ["snmp", "traps", "syslog", "datalake_backup.db"]
    found_all = all(r in out for r in required)
    return success and found_all, f"Backup files present: {out.split()}"
results.append(test("Data Lake Automated Replication to Isolated Backup Node", test_backup_synchronization))

def test_retention_policy_enforcement():
    cmd = "docker exec clab-lab1-nmas curl -s http://127.0.0.1:8080/api/datalake/retention"
    success, out, _ = run_cmd(cmd)
    if success:
        data = json.loads(out)
        return len(data) >= 1, f"Retention cycle logs: {len(data)}"
    return False, out
results.append(test("7-Day Retention Policy Daemon Enforcing Cleanup & Purge", test_retention_policy_enforcement))

print("\n" + "="*75)
passed = sum(1 for r in results if r)
total = len(results)
print(f"   SUMMARY: {passed}/{total} Monitoring & Data Lake Tests Passed ({(passed/total)*100:.1f}%)")
print("="*75)

if passed == total:
    print("\n[92mALL OBJECTIVES (1, 2, 3) AND DATA LAKE BACKUP/RETENTION VERIFIED![0m\n")
    sys.exit(0)
else:
    print(f"\n[91m{total - passed} test(s) failed.[0m\n")
    sys.exit(1)
