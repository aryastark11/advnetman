#!/usr/bin/env python3
"""
Helper script to generate the current 2FA TOTP token for netops
and show the full concatenated password for SSH login to network devices.
"""
import json
import os
import sys
import time
import pyotp

CONFIG_FILE = "/home/student/Desktop/lab1/radius/privacyidea_tokens.json"

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        tokens = json.load(f)

    user = "netops"
    if len(sys.argv) > 1:
        user = sys.argv[1].lower()

    if user not in tokens:
        print(f"User '{user}' not found in {CONFIG_FILE}. Available: {list(tokens.keys())}")
        sys.exit(1)

    user_info = tokens[user]
    base_pass = user_info.get("password", "")
    secret = user_info.get("secret", "")
    totp = pyotp.TOTP(secret)

    current_otp = totp.now()
    remaining = int(30 - (time.time() % 30))

    print("==================================================")
    print(f"  2FA TOTP Token Generator for User: {user}")
    print("==================================================")
    print(f"Base Password   : {base_pass}")
    print(f"Current OTP     : {current_otp}  ({remaining}s remaining)")
    print(f"SSH Combined    : {base_pass}{current_otp}")
    print("--------------------------------------------------")
    print(f"Test SSH to R1  : ssh netops@172.20.20.11")
    print(f"Password prompt : Enter '{base_pass}{current_otp}'")
    print("==================================================")

if __name__ == "__main__":
    main()
