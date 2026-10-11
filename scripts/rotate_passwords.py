#!/usr/bin/env python3
"""
CSCI 5840 - Network Automation & Security
Automatic Device Credential Rotation Engine
Safety Contract: Device First -> eAPI Verification -> Vault KV-v2 Update -> Audit Trail
"""

import argparse
import csv
import json
import logging
import logging.handlers
import os
import secrets
import string
import sys
import time
import urllib.request
import urllib.error
import base64
import hvac

# Setup logging (Console + Syslog)
logger = logging.getLogger("vault-rotator")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)

try:
    syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
    syslog_handler.setFormatter(logging.Formatter("vault-rotator: [%(levelname)s] %(message)s"))
    logger.addHandler(syslog_handler)
except Exception:
    pass

def generate_strong_password(length=28):
    """Generates a 28-character cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure diverse character classes
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*-_=+" for c in password)):
            return password

def eapi_run_commands(mgmt_ip, username, password, cmds, timeout=6):
    """Executes Arista eAPI JSON-RPC commands."""
    url = f"http://{mgmt_ip}/command-api"
    auth_str = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": cmds,
            "format": "text"
        },
        "id": "vault-rotate-eapi"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_str}"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_vault_client(vault_url, ca_cert, approle_file=None):
    """Authenticates to Vault using machine AppRole."""
    approle_file = approle_file or os.path.expanduser("~/.vault_approle.json")
    if not os.path.exists(approle_file):
        raise FileNotFoundError(f"AppRole credentials not found at {approle_file}")

    with open(approle_file, "r") as f:
        approle_data = json.load(f)

    client = hvac.Client(url=vault_url, verify=ca_cert)
    login_resp = client.auth.approle.login(
        role_id=approle_data["role_id"],
        secret_id=approle_data["secret_id"]
    )
    if not client.is_authenticated():
        raise PermissionError("Vault AppRole authentication failed!")
    return client

def rotate_device_credential(client, device_info, dry_run=False):
    """
    Executes the non-negotiable safety contract:
    1. Read current credential from Vault
    2. Test current connectivity
    3. Generate 28-char strong password
    4. Apply new secret on device via eAPI
    5. Verify new credential via eAPI
    6. Write new credential to Vault KV-v2
    """
    hostname = device_info["hostname"]
    mgmt_ip = device_info["mgmt_ip"]
    username = device_info.get("username", "admin")
    vault_subpath = f"devices/{hostname}"

    logger.info(f"--- Starting Credential Rotation for {hostname} ({mgmt_ip}) ---")

    # Step 1: Read current Vault secret
    try:
        current_vault_data = client.secrets.kv.v2.read_secret_version(
            mount_point="network",
            path=vault_subpath
        )["data"]["data"]
        current_password = current_vault_data.get("password", "admin")
        current_version = current_vault_data.get("version", 1)
        logger.info(f"[{hostname}] Read active credential from Vault (version {current_version})")
    except Exception as e:
        logger.warning(f"[{hostname}] No existing Vault secret ({e}); fallback to default 'admin'")
        current_password = "admin"
        current_vault_data = {
            "hostname": hostname,
            "mgmt_ip": mgmt_ip,
            "platform": device_info.get("platform", "arista_eos"),
            "role": device_info.get("role", "device"),
            "username": username
        }

    # Step 2: Verify current login on device
    try:
        eapi_run_commands(mgmt_ip, username, current_password, ["enable", "show version"])
        logger.info(f"[{hostname}] Pre-rotation authentication check: PASSED")
    except Exception as e:
        logger.error(f"[{hostname}] Pre-rotation connection failed with current password: {e}")
        return False

    # Step 3: Generate new secure password
    new_password = generate_strong_password(length=28)

    if dry_run:
        logger.info(f"[{hostname}] [DRY-RUN] Would push new 28-char secret to device and update Vault.")
        logger.info(f"[{hostname}] [DRY-RUN] Target Vault Path: network/data/{vault_subpath}")
        return True

    # Step 4: Push new secret to device via eAPI
    logger.info(f"[{hostname}] Pushing new secret to device via eAPI...")
    config_cmds = [
        "enable",
        "configure",
        f"username {username} privilege 15 secret {new_password}",
        "write memory"
    ]
    try:
        eapi_run_commands(mgmt_ip, username, current_password, config_cmds)
        logger.info(f"[{hostname}] Device config updated with new secret.")
    except Exception as e:
        logger.critical(f"[{hostname}] FAILED to update device configuration: {e}")
        logger.error(f"[{hostname}] Aborting rotation. Vault remains untouched at previous version.")
        return False

    # Step 5: Verification - Brand-new eAPI session using NEW password
    logger.info(f"[{hostname}] Verifying new credential with fresh eAPI handshake...")
    time.sleep(0.5)
    try:
        verify_resp = eapi_run_commands(mgmt_ip, username, new_password, ["enable", "show version"])
        if "result" in verify_resp:
            logger.info(f"[{hostname}] Verification handshake SUCCESSFUL with new credentials!")
    except Exception as e:
        logger.critical(f"[{hostname}] VERIFICATION FAILED with new password: {e}")
        logger.critical(f"[{hostname}] EMERGENCY: Device and Vault may be out of sync. Not updating Vault.")
        return False

    # Step 6: Write new credential to Vault KV-v2 (Automatic versioning)
    logger.info(f"[{hostname}] Updating Vault KV-v2 secret...")
    new_payload = dict(current_vault_data)
    new_payload["password"] = new_password
    new_payload["last_rotated_at"] = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
    
    try:
        vault_resp = client.secrets.kv.v2.create_or_update_secret(
            mount_point="network",
            path=vault_subpath,
            secret=new_payload
        )
        new_ver = vault_resp["data"]["version"]
        logger.info(f"[{hostname}] Vault updated successfully (New Version: {new_ver})")
        logger.info(f"[{hostname}] Credential rotation COMPLETED SUCCESSFULLY!")
        return True
    except Exception as e:
        logger.critical(f"[{hostname}] Failed to write new secret to Vault: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Automated Network Device Password Rotation (Vault + eAPI)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate rotation without making changes")
    parser.add_argument("--device", help="Rotate only a specific target device (e.g., R1)")
    parser.add_argument("--stagger", type=float, default=2.0, help="Delay in seconds between devices (default: 2s)")
    parser.add_argument("--csv", default="/home/student/Desktop/lab1/ipam.csv", help="Path to IPAM CSV file")
    parser.add_argument("--vault-url", default="https://127.0.0.1:8200", help="Vault URL")
    parser.add_argument("--ca-cert", default="/home/student/Desktop/lab1/vault/certs/ca.crt", help="Vault CA Cert")
    parser.add_argument("--approle-file", default=os.path.expanduser("~/.vault_approle.json"), help="AppRole JSON")
    args = parser.parse_args()

    logger.info("======================================================================")
    logger.info("          STARTING AUTOMATED CREDENTIAL ROTATION ENGINE               ")
    logger.info(f" Mode: {'DRY-RUN (Safe Simulation)' if args.dry_run else 'LIVE EXECUTION'}")
    logger.info("======================================================================")

    # Authenticate to Vault
    try:
        client = get_vault_client(args.vault_url, args.ca_cert, args.approle_file)
        logger.info("[+] Authenticated to Vault via AppRole (Policy: automation)")
    except Exception as e:
        logger.critical(f"Failed to authenticate to Vault: {e}")
        sys.exit(1)

    # Read IPAM CSV
    csv_file = args.csv
    if not os.path.exists(csv_file):
        csv_file = "/home/student/Desktop/lab1/ipam/ipam.csv"
    if not os.path.exists(csv_file):
        csv_file = "/home/student/Desktop/lab1/ipam/devices.csv"
    if not os.path.exists(csv_file):
        logger.critical(f"IPAM CSV file not found: {args.csv}")
        sys.exit(1)

    devices_dict = {}
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dev_raw = row.get("Device/Host", row.get("hostname", "")).strip()
            intf = row.get("Interface", "").strip()
            mgmt_ip_field = row.get("IPv4 Address/Prefix", row.get("mgmt_ip", "")).strip()
            
            # Handle standard ipam.csv structure
            if "Management" in intf or "MGMT" in intf or "mgmt_ip" in row:
                name = dev_raw.replace("Switch ", "").replace("Host ", "").strip()
                if name.startswith("R") or name.startswith("S") or (row.get("platform") == "arista_eos"):
                    ip = mgmt_ip_field.split("/")[0]
                    role = "router" if name.startswith("R") else "switch"
                    devices_dict[name] = {
                        "hostname": name,
                        "mgmt_ip": ip,
                        "platform": "arista_eos",
                        "role": role,
                        "username": row.get("username", "admin"),
                        "vault_path": f"network/devices/{name}"
                    }

    devices = [v for k, v in sorted(devices_dict.items())]

    if args.device:
        devices = [d for d in devices if d["hostname"].upper() == args.device.upper()]
        if not devices:
            logger.error(f"Device '{args.device}' not found in {csv_file}")
            sys.exit(1)

    success_count = 0
    total_count = len(devices)

    for i, dev in enumerate(devices):
        if i > 0 and args.stagger > 0:
            logger.info(f"Staggering rotation: sleeping {args.stagger}s...")
            time.sleep(args.stagger)

        ok = rotate_device_credential(client, dev, dry_run=args.dry_run)
        if ok:
            success_count += 1

    logger.info("======================================================================")
    logger.info(f" ROTATION SUMMARY: {success_count}/{total_count} Devices Processed Successfully")
    logger.info("======================================================================")

    if success_count < total_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
