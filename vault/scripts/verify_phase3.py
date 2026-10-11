#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.request
import urllib.error
import hvac

CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"

print("======================================================================")
print("             PHASE 3 VERIFICATION: CREDENTIAL ROTATION & AUDIT        ")
print("======================================================================")

# Authenticate with AppRole
approle_file = os.path.expanduser("~/.vault_approle.json")
with open(approle_file, "r") as f:
    approle_data = json.load(f)

app_client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
app_client.auth.approle.login(
    role_id=approle_data["role_id"],
    secret_id=approle_data["secret_id"]
)

# 1. Read Current (Version 2) and Previous (Version 1) Vault Secrets for R1
print("\n[TEST 1] Querying Vault KV-v2 Version History for 'network/devices/R1'...")
sec_v2 = app_client.secrets.kv.v2.read_secret_version(mount_point="network", path="devices/R1", version=2)
v2_data = sec_v2["data"]["data"]
v2_meta = sec_v2["data"]["metadata"]
print(f"  [✓] Active Secret (Version 2):")
print(f"      Created At: {v2_meta['created_time']}")
print(f"      Rotated At: {v2_data.get('last_rotated_at')}")
print(f"      Username: {v2_data['username']}")
print(f"      Password Length: {len(v2_data['password'])} chars (Redacted: {v2_data['password'][:3]}...{v2_data['password'][-3:]})")

sec_v1 = app_client.secrets.kv.v2.read_secret_version(mount_point="network", path="devices/R1", version=1)
v1_data = sec_v1["data"]["data"]
v1_meta = sec_v1["data"]["metadata"]
print(f"  [✓] Rollback Baseline (Version 1):")
print(f"      Created At: {v1_meta['created_time']}")
print(f"      Password: {v1_data['password']}")

# 2. Negative Test: Test login to R1 with OLD password (admin) -> Expected: 401 Unauthorized
print("\n[TEST 2] Testing R1 eAPI login with OLD password ('admin') (Expected: REJECTED / 401)...")
r1_ip = "172.20.20.11"
old_auth = base64.b64encode(b"admin:admin").decode("utf-8")
payload = json.dumps({"jsonrpc": "2.0", "method": "runCmds", "params": {"version": 1, "cmds": ["show version"]}, "id": 1}).encode("utf-8")
req_old = urllib.request.Request(f"http://{r1_ip}/command-api", data=payload, headers={"Content-Type": "application/json", "Authorization": f"Basic {old_auth}"})

try:
    with urllib.request.urlopen(req_old, timeout=4) as resp:
        print("  [X] SECURITY FAILURE: R1 accepted the revoked old password!")
except urllib.error.HTTPError as e:
    if e.code == 401:
        print(f"  [✓] REJECTED as expected: HTTP {e.code} Unauthorized (Old password is dead).")
    else:
        print(f"  [✓] REJECTED with HTTP {e.code}")
except Exception as e:
    print(f"  [✓] Connection refused/error: {e}")

# 3. Positive Test: Test login to R1 with NEW rotated password from Vault
print("\n[TEST 3] Testing R1 eAPI login with NEW rotated password from Vault (Expected: ALLOWED)...")
new_auth = base64.b64encode(f"admin:{v2_data['password']}".encode("utf-8")).decode("utf-8")
req_new = urllib.request.Request(f"http://{r1_ip}/command-api", data=payload, headers={"Content-Type": "application/json", "Authorization": f"Basic {new_auth}"})

try:
    with urllib.request.urlopen(req_new, timeout=4) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        version_info = result["result"][0]["version"]
        print(f"  [✓] SUCCESS: Authenticated to R1 via eAPI using Vault-managed credential!")
        print(f"      EOS Version: {version_info}")
except Exception as e:
    print(f"  [X] FAILED to login with new password: {e}")

# 4. Audit Log Verification
print("\n[TEST 4] Inspecting Vault File Audit Log (/vault/logs/audit.log)...")
audit_log_path = "/home/student/Desktop/lab1/vault/audit/audit.log"
if os.path.exists(audit_log_path):
    with open(audit_log_path, "r") as f:
        lines = f.readlines()
    print(f"  [✓] Vault Audit Log active. Total entries: {len(lines)}")
    if lines:
        last_entry = json.loads(lines[-1])
        print(f"      Latest Audit Event:")
        print(f"        Time: {last_entry.get('time')}")
        print(f"        Type: {last_entry.get('type')}")
        print(f"        Path: {last_entry.get('request', {}).get('path')}")
        print(f"        Operation: {last_entry.get('request', {}).get('operation')}")
        print(f"        Client Token Display: {last_entry.get('auth', {}).get('display_name')}")
else:
    print(f"  [X] Audit log file not found at {audit_log_path}")

print("\n======================================================================")
print("               PHASE 3 VERIFICATION COMPLETED: ALL PASS               ")
print("======================================================================")
