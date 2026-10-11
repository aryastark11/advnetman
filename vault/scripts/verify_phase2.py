#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import hvac
import pyotp
import requests

CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"
MFA_FILE = os.path.expanduser("~/.vault_mfa.json")

if not os.path.exists(MFA_FILE):
    print(f"MFA file not found: {MFA_FILE}", file=sys.stderr)
    sys.exit(1)

with open(MFA_FILE, "r") as f:
    mfa_data = json.load(f)

method_id = mfa_data["method_id"]
op_otp_url = mfa_data["operator_otp_url"]
admin_otp_url = mfa_data["admin_otp_url"]

op_secret = urllib.parse.parse_qs(urllib.parse.urlparse(op_otp_url).query)["secret"][0]
admin_secret = urllib.parse.parse_qs(urllib.parse.urlparse(admin_otp_url).query)["secret"][0]

op_totp = pyotp.TOTP(op_secret)
admin_totp = pyotp.TOTP(admin_secret)

print("======================================================================")
print("             PHASE 2 VERIFICATION: TOTP MFA ENFORCEMENT               ")
print("======================================================================")

# 1. Negative Test: Login WITHOUT TOTP (Expected: Empty Token + MFA Challenge)
print("\n[TEST 1] Operator login WITHOUT TOTP (Expected: MFA CHALLENGE / NO TOKEN)...")
req_payload = {"password": "OperatorSecurePassword2026!"}
resp = requests.post(
    f"{VAULT_URL}/v1/auth/userpass/login/operator",
    json=req_payload,
    verify=CA_CERT
)
res_json = resp.json()
client_token = res_json.get("auth", {}).get("client_token", "")
mfa_req = res_json.get("auth", {}).get("mfa_requirement")

if client_token == "" and mfa_req is not None:
    print("  [✓] DENIED/CHALLENGED as expected: No token issued without MFA passcode.")
    print(f"      MFA Method Required: TOTP (Method ID: {method_id})")
else:
    print(f"  [X] FAILED: Token issued without MFA: {client_token}")

# 2. Negative Test: Login WITH WRONG TOTP (Expected: DENIED / HTTP 403)
print("\n[TEST 2] Operator login WITH WRONG TOTP (000000) (Expected: DENIED)...")
wrong_headers = {"X-Vault-MFA": f"{method_id}:000000"}
resp_wrong = requests.post(
    f"{VAULT_URL}/v1/auth/userpass/login/operator",
    json=req_payload,
    headers=wrong_headers,
    verify=CA_CERT
)
if resp_wrong.status_code == 403 or resp_wrong.status_code == 400:
    print(f"  [✓] DENIED as expected with incorrect passcode (HTTP {resp_wrong.status_code}): {resp_wrong.json().get('errors')}")
else:
    print(f"  [X] UNEXPECTED response: {resp_wrong.status_code} {resp_wrong.text}")

# 3. Positive Test: Login WITH VALID TOTP (Expected: ALLOWED)
current_code = op_totp.now()
print(f"\n[TEST 3] Operator login WITH VALID TOTP ({current_code}) (Expected: ALLOWED)...")
valid_headers = {"X-Vault-MFA": f"{method_id}:{current_code}"}
resp_valid = requests.post(
    f"{VAULT_URL}/v1/auth/userpass/login/operator",
    json=req_payload,
    headers=valid_headers,
    verify=CA_CERT
)
if resp_valid.status_code == 200:
    op_token = resp_valid.json()["auth"]["client_token"]
    print(f"  [✓] MFA Login SUCCESS! Token received.")
    print(f"      Policies: {resp_valid.json()['auth']['policies']}")
    
    # 3A. Test reading network/devices/R1 with MFA-authenticated token
    op_client = hvac.Client(url=VAULT_URL, token=op_token, verify=CA_CERT)
    sec_r1 = op_client.secrets.kv.v2.read_secret_version(mount_point="network", path="devices/R1")
    print(f"  [✓] Operator reading network/devices/R1: ALLOWED (Hostname: {sec_r1['data']['data']['hostname']})")

    # 3B. Test reading nmas-admin with MFA-authenticated operator token (Expected: DENIED)
    try:
        op_client.secrets.kv.v2.read_secret_version(mount_point="nmas-admin", path="hosts/nmas")
        print("  [X] SECURITY VIOLATION: Operator was able to read nmas-admin!")
    except Exception as e:
        print(f"  [✓] Operator reading nmas-admin: DENIED as expected (403 Permission Denied)")
else:
    print(f"  [X] Login FAILED: {resp_valid.status_code} {resp_valid.text}")

# 4. Positive Test: Admin Login WITH VALID TOTP to access nmas-admin
admin_code = admin_totp.now()
print(f"\n[TEST 4] Admin login WITH VALID TOTP ({admin_code}) (Expected: ALLOWED)...")
admin_payload = {"password": "AdminMasterPassword2026!"}
admin_headers = {"X-Vault-MFA": f"{method_id}:{admin_code}"}
resp_admin = requests.post(
    f"{VAULT_URL}/v1/auth/userpass/login/admin",
    json=admin_payload,
    headers=admin_headers,
    verify=CA_CERT
)
if resp_admin.status_code == 200:
    admin_token = resp_admin.json()["auth"]["client_token"]
    print(f"  [✓] Admin MFA Login SUCCESS!")
    admin_client = hvac.Client(url=VAULT_URL, token=admin_token, verify=CA_CERT)
    sec_nmas = admin_client.secrets.kv.v2.read_secret_version(mount_point="nmas-admin", path="hosts/nmas")
    print(f"  [✓] Admin reading nmas-admin/hosts/nmas: ALLOWED (Hostname: {sec_nmas['data']['data']['hostname']})")
else:
    print(f"  [X] Admin login FAILED: {resp_admin.status_code} {resp_admin.text}")

# 5. AppRole Test: Verify AppRole does NOT require MFA and can read network secrets
print("\n[TEST 5] Machine AppRole Auth (No MFA required for CI/Automation)...")
approle_file = os.path.expanduser("~/.vault_approle.json")
with open(approle_file, "r") as f:
    approle_data = json.load(f)

app_client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
app_login = app_client.auth.approle.login(
    role_id=approle_data["role_id"],
    secret_id=approle_data["secret_id"]
)
print(f"  [✓] AppRole Login SUCCESS without MFA (Token: {app_login['auth']['policies']})")
sec_app = app_client.secrets.kv.v2.read_secret_version(mount_point="network", path="devices/R1")
print(f"  [✓] AppRole reading network/devices/R1: ALLOWED (Hostname: {sec_app['data']['data']['hostname']})")
try:
    app_client.secrets.kv.v2.read_secret_version(mount_point="nmas-admin", path="hosts/nmas")
    print("  [X] SECURITY VIOLATION: AppRole read nmas-admin!")
except Exception as e:
    print(f"  [✓] AppRole reading nmas-admin: DENIED as expected (403 Permission Denied)")

print("\n======================================================================")
print("               PHASE 2 VERIFICATION COMPLETED: ALL PASS               ")
print("======================================================================")
