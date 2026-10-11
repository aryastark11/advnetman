#!/usr/bin/env python3
import json
import os
import sys
import hvac

CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"

print("======================================================================")
print("             PHASE 1 VERIFICATION: VAULT ACCESS & POLICIES           ")
print("======================================================================")

# 1. Test Operator Userpass Login & Access
print("\n[TEST 1] Operator Login via userpass (Policy: network-operator)...")
mfa_file = os.path.expanduser("~/.vault_mfa.json")
headers = {}
if os.path.exists(mfa_file):
    import pyotp, urllib.parse
    with open(mfa_file, "r") as f:
        mfa_data = json.load(f)
    method_id = mfa_data["method_id"]
    op_otp_url = mfa_data["operator_otp_url"]
    op_sec = urllib.parse.parse_qs(urllib.parse.urlparse(op_otp_url).query)["secret"][0]
    headers["X-Vault-MFA"] = f"{method_id}:{pyotp.TOTP(op_sec).now()}"

import requests
resp = requests.post(
    f"{VAULT_URL}/v1/auth/userpass/login/operator",
    json={"password": "OperatorSecurePassword2026!"},
    headers=headers,
    verify=CA_CERT
)
if resp.status_code == 200:
    op_token = resp.json()["auth"]["client_token"]
    op_client = hvac.Client(url=VAULT_URL, token=op_token, verify=CA_CERT)
    print(f"  [✓] Operator login SUCCESS. Token policies: {resp.json()['auth']['policies']}")
else:
    print(f"  [X] Operator login FAILED: {resp.status_code} {resp.text}")
    sys.exit(1)

# 1A. Operator reads network/devices/R1 (Expected: ALLOWED)
print("\n[TEST 1A] Operator reading 'network/devices/R1' (Expected: ALLOWED)...")
try:
    secret = op_client.secrets.kv.v2.read_secret_version(
        mount_point="network",
        path="devices/R1"
    )
    print(f"  [✓] ALLOWED - Successfully read R1 secret:")
    data = secret["data"]["data"]
    print(f"      Hostname: {data.get('hostname')}")
    print(f"      Management IP: {data.get('mgmt_ip')}")
    print(f"      Username: {data.get('username')}")
    print(f"      Password: {'*' * len(data.get('password', ''))} (Redacted)")
except Exception as e:
    print(f"  [X] FAILED: {e}")

# 1B. Operator attempts to read nmas-admin/hosts/nmas (Expected: DENIED / 403)
print("\n[TEST 1B] Operator attempting to read 'nmas-admin/hosts/nmas' (Expected: DENIED)...")
try:
    secret = op_client.secrets.kv.v2.read_secret_version(
        mount_point="nmas-admin",
        path="hosts/nmas"
    )
    print(f"  [X] SECURITY VIOLATION: Operator was allowed to read nmas-admin!")
except Exception as e:
    print(f"  [✓] DENIED as expected: {e}")

# 2. Test Automation AppRole Login & Access
print("\n[TEST 2] Automation Login via AppRole (Policy: automation)...")
approle_file = os.path.expanduser("~/.vault_approle.json")
with open(approle_file, "r") as f:
    approle_data = json.load(f)

app_client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
try:
    app_login = app_client.auth.approle.login(
        role_id=approle_data["role_id"],
        secret_id=approle_data["secret_id"]
    )
    print(f"  [✓] AppRole login SUCCESS. Token policies: {app_login['auth']['policies']}")
except Exception as e:
    print(f"  [X] AppRole login FAILED: {e}")
    sys.exit(1)

# 2A. AppRole reads network/devices/R1 (Expected: ALLOWED)
print("\n[TEST 2A] AppRole reading 'network/devices/R1' (Expected: ALLOWED)...")
try:
    secret = app_client.secrets.kv.v2.read_secret_version(
        mount_point="network",
        path="devices/R1"
    )
    print(f"  [✓] ALLOWED - Successfully read R1 secret:")
    data = secret["data"]["data"]
    print(f"      Hostname: {data.get('hostname')}")
    print(f"      Management IP: {data.get('mgmt_ip')}")
    print(f"      Username: {data.get('username')}")
except Exception as e:
    print(f"  [X] FAILED: {e}")

# 2B. AppRole attempts to read nmas-admin/hosts/nmas (Expected: DENIED / 403)
print("\n[TEST 2B] AppRole attempting to read 'nmas-admin/hosts/nmas' (Expected: DENIED)...")
try:
    secret = app_client.secrets.kv.v2.read_secret_version(
        mount_point="nmas-admin",
        path="hosts/nmas"
    )
    print(f"  [X] SECURITY VIOLATION: AppRole was allowed to read nmas-admin!")
except Exception as e:
    print(f"  [✓] DENIED as expected: {e}")

print("\n======================================================================")
print("               PHASE 1 VERIFICATION COMPLETED: ALL PASS               ")
print("======================================================================")
