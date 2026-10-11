#!/usr/bin/env python3
import json
import os
import sys
import hvac
import pyotp
import qrcode

KEYS_FILE = os.path.expanduser("~/.vault_keys.json")
CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"

with open(KEYS_FILE, "r") as f:
    keys_data = json.load(f)

root_token = keys_data["root_token"]
client = hvac.Client(url=VAULT_URL, token=root_token, verify=CA_CERT)

print("[+] Authenticated with Root Token for MFA setup.")

# 1. Create TOTP MFA Method with generous validation attempts & skew
totp_method = client.write(
    "identity/mfa/method/totp",
    issuer="NMAS-Vault-5840",
    period="30",
    key_size=20,
    digits=6,
    skew=1,
    max_validation_attempts=10,
    algorithm="SHA1"
)
method_id = totp_method["data"]["method_id"]
print(f"[+] Created TOTP MFA Method. Method ID: {method_id}")

# 2. Get Userpass Auth Accessor
auth_methods = client.sys.list_auth_methods()
userpass_accessor = auth_methods["userpass/"]["accessor"]
print(f"[+] Found Userpass Auth Accessor: {userpass_accessor}")

# 3. Create or Get Identity Entity for 'operator' and 'admin'
def get_or_create_entity(username, policy):
    try:
        read_resp = client.read(f"identity/entity/name/{username}")
        if read_resp and "data" in read_resp:
            return read_resp["data"]["id"]
    except Exception:
        pass
    write_resp = client.write(f"identity/entity", name=username, policies=[policy])
    if isinstance(write_resp, dict) and "data" in write_resp:
        return write_resp["data"]["id"]
    read_resp = client.read(f"identity/entity/name/{username}")
    return read_resp["data"]["id"]

entity_op_id = get_or_create_entity("operator", "network-operator")
try:
    client.write(
        "identity/entity-alias",
        name="operator",
        canonical_id=entity_op_id,
        mount_accessor=userpass_accessor
    )
except Exception:
    pass
print(f"[+] Bound Entity 'operator' (ID: {entity_op_id}) to Userpass Accessor")

entity_admin_id = get_or_create_entity("admin", "admin")
try:
    client.write(
        "identity/entity-alias",
        name="admin",
        canonical_id=entity_admin_id,
        mount_accessor=userpass_accessor
    )
except Exception:
    pass
print(f"[+] Bound Entity 'admin' (ID: {entity_admin_id}) to Userpass Accessor")

# 4. Generate TOTP enrollment for operator & admin
enroll_op = client.write(
    "identity/mfa/method/totp/admin-generate",
    entity_id=entity_op_id,
    method_id=method_id
)
op_otp_url = enroll_op["data"]["url"]
print(f"[+] Generated Operator TOTP Enrollment URL: {op_otp_url}")

enroll_admin = client.write(
    "identity/mfa/method/totp/admin-generate",
    entity_id=entity_admin_id,
    method_id=method_id
)
admin_otp_url = enroll_admin["data"]["url"]
print(f"[+] Generated Admin TOTP Enrollment URL: {admin_otp_url}")

# Generate ASCII QR Code for CLI terminal display
print("\n[+] Operator TOTP ASCII QR Code for Authenticator App Enrollment:")
qr = qrcode.QRCode()
qr.add_data(op_otp_url)
qr.print_ascii(invert=True)

# Save MFA configuration details outside git
mfa_state = {
    "method_id": method_id,
    "userpass_accessor": userpass_accessor,
    "operator_entity_id": entity_op_id,
    "operator_otp_url": op_otp_url,
    "admin_entity_id": entity_admin_id,
    "admin_otp_url": admin_otp_url
}
mfa_file = os.path.expanduser("~/.vault_mfa.json")
with open(mfa_file, "w") as f:
    json.dump(mfa_state, f, indent=2)
os.chmod(mfa_file, 0o600)
print(f"[+] Saved MFA state securely to {mfa_file} (mode 600, outside git)")

# 5. Enforce Login MFA on Userpass Auth Method
enforcement = client.write(
    "identity/mfa/login-enforcement/userpass-totp",
    auth_method_accessors=[userpass_accessor],
    mfa_method_ids=[method_id]
)
print("[+] Login MFA Enforcement applied to 'userpass' auth mount!")
print("[✓] Phase 2 MFA Configuration Complete!")
