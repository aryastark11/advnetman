#!/usr/bin/env python3
import csv
import json
import os
import sys
import hvac

KEYS_FILE = os.path.expanduser("~/.vault_keys.json")
CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"

if not os.path.exists(KEYS_FILE):
    print(f"Keys file not found: {KEYS_FILE}", file=sys.stderr)
    sys.exit(1)

with open(KEYS_FILE, "r") as f:
    keys_data = json.load(f)

root_token = keys_data.get("root_token")
client = hvac.Client(url=VAULT_URL, token=root_token, verify=CA_CERT)

if not client.is_authenticated():
    print("Failed to authenticate with root token!", file=sys.stderr)
    sys.exit(1)

print("[+] Authenticated to Vault with Root Token.")

# 1. Enable Audit Device
try:
    client.sys.enable_audit_device(
        device_type="file",
        options={"file_path": "/vault/logs/audit.log"},
        path="file"
    )
    print("[+] Enabled file audit device at /vault/logs/audit.log")
except Exception as e:
    if "already in use" in str(e) or "path already in use" in str(e):
        print("[*] Audit device already enabled.")
    else:
        print(f"[-] Audit device: {e}")

# 2. Enable Secret Engines (KV-v2)
for mount_point in ["network", "nmas-admin"]:
    try:
        client.sys.enable_secrets_engine(
            backend_type="kv",
            path=mount_point,
            options={"version": "2"}
        )
        print(f"[+] Enabled KV-v2 engine at mount path: {mount_point}/")
    except Exception as e:
        if "path is already in use" in str(e):
            print(f"[*] KV-v2 mount '{mount_point}/' already exists.")
        else:
            print(f"[-] Secrets engine {mount_point}: {e}")

# 3. Create / Update Policies
policies_dir = "/home/student/Desktop/lab1/vault/policies"
for policy_name in ["network-operator", "automation", "admin"]:
    policy_path = os.path.join(policies_dir, f"{policy_name}.hcl")
    if os.path.exists(policy_path):
        with open(policy_path, "r") as f:
            policy_hcl = f.read()
        client.sys.create_or_update_policy(name=policy_name, policy=policy_hcl)
        print(f"[+] Policy '{policy_name}' installed from {policy_name}.hcl")

# 4. Enable Auth Methods
# 4A. userpass
try:
    client.sys.enable_auth_method(method_type="userpass", path="userpass")
    print("[+] Enabled 'userpass' auth method.")
except Exception as e:
    if "path is already in use" in str(e):
        print("[*] 'userpass' auth method already enabled.")
    else:
        print(f"[-] Auth method userpass: {e}")

# Create operator and admin users
client.auth.userpass.create_or_update_user(
    username="operator",
    password="OperatorSecurePassword2026!",
    policies=["network-operator"],
    mount_point="userpass"
)
print("[+] Created userpass account 'operator' (policy: network-operator)")

client.auth.userpass.create_or_update_user(
    username="admin",
    password="AdminMasterPassword2026!",
    policies=["admin"],
    mount_point="userpass"
)
print("[+] Created userpass account 'admin' (policy: admin)")

# 4B. approle
try:
    client.sys.enable_auth_method(method_type="approle", path="approle")
    print("[+] Enabled 'approle' auth method.")
except Exception as e:
    if "path is already in use" in str(e):
        print("[*] 'approle' auth method already enabled.")
    else:
        print(f"[-] Auth method approle: {e}")

# Configure automation AppRole
client.auth.approle.create_or_update_approle(
    role_name="automation",
    token_policies=["automation"],
    token_ttl="1h",
    token_max_ttl="4h",
    bind_secret_id=True,
    secret_id_num_uses=0,
    secret_id_ttl="24h",
    mount_point="approle"
)
print("[+] Configured AppRole 'automation' with policy 'automation' (TTL: 1h, Max TTL: 4h)")

# Fetch Role ID & Secret ID
role_id = client.auth.approle.read_role_id(role_name="automation", mount_point="approle")["data"]["role_id"]
secret_id_resp = client.auth.approle.generate_secret_id(role_name="automation", mount_point="approle")
secret_id = secret_id_resp["data"]["secret_id"]

approle_credentials = {
    "role_id": role_id,
    "secret_id": secret_id,
    "role_name": "automation"
}
approle_file = "/home/student/.vault_approle.json"
with open(approle_file, "w") as f:
    json.dump(approle_credentials, f, indent=2)
os.chmod(approle_file, 0o600)
print(f"[+] AppRole credentials saved to {approle_file} (mode 600, outside git)")

# 5. Populate Network Device Credentials from IPAM (ipam.csv)
ipam_csv = "/home/student/Desktop/lab1/ipam.csv"
if not os.path.exists(ipam_csv):
    ipam_csv = "/home/student/Desktop/lab1/ipam/ipam.csv"

if os.path.exists(ipam_csv):
    devices = {}
    with open(ipam_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dev_raw = row.get("Device/Host", "").strip()
            intf = row.get("Interface", "").strip()
            mgmt_ip = row.get("IPv4 Address/Prefix", "").strip()
            
            if "Management" in intf or "MGMT" in intf:
                name = dev_raw.replace("Switch ", "").replace("Host ", "").strip()
                if name.startswith("R") or name.startswith("S"):
                    ip = mgmt_ip.split("/")[0]
                    role = "router" if name.startswith("R") else "switch"
                    devices[name] = {
                        "hostname": name,
                        "mgmt_ip": ip,
                        "platform": "arista_eos",
                        "role": role,
                        "username": "admin",
                        "password": "admin",
                        "vault_path": f"network/devices/{name}"
                    }
    
    for name, dev_info in sorted(devices.items()):
        secret_subpath = f"devices/{name}"
        secret_payload = {
            "hostname": dev_info["hostname"],
            "mgmt_ip": dev_info["mgmt_ip"],
            "platform": dev_info["platform"],
            "role": dev_info["role"],
            "username": dev_info["username"],
            "password": dev_info["password"]
        }
        client.secrets.kv.v2.create_or_update_secret(
            mount_point="network",
            path=secret_subpath,
            secret=secret_payload
        )
        print(f"[+] Initialized device secret from ipam.csv: network/data/{secret_subpath} ({dev_info['mgmt_ip']})")

# 6. Populate Initial NMAS Admin Secrets in separate mount
client.secrets.kv.v2.create_or_update_secret(
    mount_point="nmas-admin",
    path="hosts/nmas",
    secret={
        "hostname": "nmas",
        "mgmt_ip": "172.20.20.100",
        "admin_user": "student",
        "ssh_key": "id_ed25519_nmas_internal",
        "sudo_access": "true"
    }
)
client.secrets.kv.v2.create_or_update_secret(
    mount_point="nmas-admin",
    path="cloud/aws",
    secret={
        "account_id": "5840-iac-lab",
        "access_key_id": "AKIA_DEMO_NMAS_KEY_ID",
        "secret_access_key": "AWS_DEMO_SECRET_KEY_NMAS"
    }
)
print("[+] Initialized NMAS admin secrets in 'nmas-admin/' mount.")
print("[✓] Vault setup completed successfully!")
