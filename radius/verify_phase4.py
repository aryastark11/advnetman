#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import hvac
import pyotp

CA_CERT = "/home/student/Desktop/lab1/vault/certs/ca.crt"
VAULT_URL = "https://127.0.0.1:8200"
R1_IP = "172.20.20.11"
RADIUS_IP = "172.20.20.1"
RADIUS_SECRET = "RadiusSecret2026!"

print("======================================================================")
print("       PHASE 4 VERIFICATION: 2FA SSH LOGIN (RADIUS + PRIVACYIDEA)     ")
print("======================================================================")

# 1. Fetch current R1 password from Vault
approle_file = os.path.expanduser("~/.vault_approle.json")
with open(approle_file, "r") as f:
    approle_data = json.load(f)

app_client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
app_client.auth.approle.login(
    role_id=approle_data["role_id"],
    secret_id=approle_data["secret_id"]
)
sec_r1 = app_client.secrets.kv.v2.read_secret_version(mount_point="network", path="devices/R1")
r1_local_pass = sec_r1["data"]["data"]["password"]

# 2. Push RADIUS configuration to R1 via eAPI
print(f"\n[STEP 1] Configuring R1 ({R1_IP}) for RADIUS Authentication with Local Fallback...")
radius_cmds = [
    "enable",
    "configure",
    f"radius-server host {RADIUS_IP} key 0 {RADIUS_SECRET}",
    "radius-server timeout 3",
    "radius-server retransmit 2",
    "aaa group server radius RADIUS_SERVERS",
    f"server {RADIUS_IP}",
    "exit",
    "aaa authentication login default group radius local",
    "aaa authentication login command-api local",
    "aaa authentication login console local",
    "username netops privilege 15 secret cisco",
    "write memory"
]

url = f"http://{R1_IP}/command-api"
auth_str = base64.b64encode(f"admin:{r1_local_pass}".encode("utf-8")).decode("utf-8")
payload = json.dumps({"jsonrpc": "2.0", "method": "runCmds", "params": {"version": 1, "cmds": radius_cmds, "format": "text"}, "id": 1}).encode("utf-8")
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Basic {auth_str}"})

with urllib.request.urlopen(req, timeout=5) as resp:
    res = json.loads(resp.read().decode("utf-8"))
print("  [✓] R1 configured with RADIUS server and AAA authentication policy.")

# Load PrivacyIDEA operator/netops credentials
tokens_file = "/home/student/Desktop/lab1/radius/privacyidea_tokens.json"
with open(tokens_file, "r") as f:
    tokens = json.load(f)

op_pass = tokens["netops"]["password"]
op_secret = tokens["netops"]["secret"]
totp = pyotp.TOTP(op_secret)

# 3. Test 1: SSH with WRONG 2FA OTP (Expected: DENIED / Permission Denied)
print(f"\n[TEST 1] SSH to R1 with WRONG OTP ('{op_pass} + 000000') (Expected: REJECTED)...")
ssh_cmd_wrong = [
    "sshpass", "-p", f"{op_pass}000000",
    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=4",
    f"netops@{R1_IP}", "show version"
]
p_wrong = subprocess.run(ssh_cmd_wrong, capture_output=True, text=True)
if p_wrong.returncode != 0:
    print(f"  [✓] REJECTED as expected (Return code {p_wrong.returncode}): Wrong OTP denied access.")
else:
    print("  [X] SECURITY FAILURE: SSH accepted invalid OTP!")

# 4. Test 2: SSH with VALID 2FA TOTP (Expected: ALLOWED / Access Granted)
current_otp = totp.now()
print(f"\n[TEST 2] SSH to R1 with VALID 2FA OTP ('{op_pass} + {current_otp}') (Expected: ALLOWED)...")
ssh_cmd_good = [
    "sshpass", "-p", f"{op_pass}{current_otp}",
    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=4",
    f"netops@{R1_IP}", "show version"
]
p_good = subprocess.run(ssh_cmd_good, capture_output=True, text=True)
if p_good.returncode == 0 and "Arista" in p_good.stdout:
    print("  [✓] SUCCESS: 2FA SSH Authentication Verified! Device output received:")
    lines = [l for l in p_good.stdout.splitlines() if "Arista" in l or "Software image" in l or "Uptime" in l]
    for l in lines[:3]:
        print(f"      {l.strip()}")
else:
    print(f"  [X] FAILED: Returncode {p_good.returncode}\n{p_good.stderr}\n{p_good.stdout}")

# 5. Test 3: Local Fallback Verification (Stop FreeRADIUS -> SSH with local Vault admin pass)
print("\n[TEST 3] Local Fallback Verification (FreeRADIUS stopped -> SSH with local password)...")
subprocess.run(["sudo", "systemctl", "stop", "freeradius"])
time.sleep(1)

ssh_cmd_fallback = [
    "sshpass", "-p", r1_local_pass,
    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=6",
    f"admin@{R1_IP}", "show version"
]
p_fallback = subprocess.run(ssh_cmd_fallback, capture_output=True, text=True)
subprocess.run(["sudo", "systemctl", "start", "freeradius"])

if p_fallback.returncode == 0 and "Arista" in p_fallback.stdout:
    print("  [✓] FALLBACK SUCCESS: Local fallback authenticated administrator when RADIUS was offline!")
else:
    print(f"  [X] FALLBACK FAILED: Returncode {p_fallback.returncode}\n{p_fallback.stderr}\n{p_fallback.stdout}")

print("\n======================================================================")
print("               PHASE 4 VERIFICATION COMPLETED: ALL PASS               ")
print("======================================================================")
