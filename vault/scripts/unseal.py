#!/usr/bin/env python3
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
    data = json.load(f)

unseal_keys = data.get("unseal_keys_b64", data.get("unseal_keys_hex", []))

client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
if not client.sys.is_sealed():
    print("Vault is already unsealed!")
    sys.exit(0)

print(f"Unsealing Vault at {VAULT_URL}...")
for i, key in enumerate(unseal_keys[:2], start=1):
    res = client.sys.submit_unseal_key(key=key)
    print(f"Key {i} applied: sealed={res.get('sealed')}, progress={res.get('progress')}")
    if not res.get("sealed"):
        print("Vault successfully unsealed!")
        break
