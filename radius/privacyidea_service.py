#!/usr/bin/env python3
"""
PrivacyIDEA Authentication Service (CSCI 5840 Lab 4/5)
Provides 2FA TOTP token validation and REST API compatible with privacyIDEA FreeRADIUS plugin.
Built using standard library http.server for maximum reliability.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
import urllib.parse
import pyotp

DB_FILE = "/home/student/Desktop/lab1/radius/privacyidea_tokens.json"

def load_tokens():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "operator": {
            "realm": "operator-realm",
            "password": "OperatorSecurePassword2026!",
            "secret": "JBSWY3DPEHPK3PXP",
            "description": "NMAS Operator Hardware/App TOTP Token"
        },
        "admin": {
            "realm": "admin-realm",
            "password": "AdminMasterPassword2026!",
            "secret": "JBSWY3DPEHPK3PXQ",
            "description": "NMAS Admin Master TOTP Token"
        }
    }

class PrivacyIdeaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write(f"[privacyidea-api] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def do_POST(self):
        if self.path.startswith("/validate/check"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            # Parse form-encoded data
            parsed = urllib.parse.parse_qs(post_data.decode("utf-8", errors="ignore"))
            user = parsed.get("user", [""])[0]
            pass_input = parsed.get("pass", [""])[0]

            tokens = load_tokens()
            user_info = tokens.get(user.lower())

            is_valid = False
            if user_info and pass_input:
                base_password = user_info["password"]
                totp_secret = user_info["secret"]
                totp = pyotp.TOTP(totp_secret)

                # Check if password + OTP concatenated
                if pass_input.startswith(base_password):
                    otp_part = pass_input[len(base_password):]
                    if totp.verify(otp_part, valid_window=2):
                        is_valid = True
                elif totp.verify(pass_input, valid_window=2):
                    is_valid = True

            if is_valid:
                resp = {
                    "jsonrpc": "2.0",
                    "result": {"status": True, "value": True},
                    "detail": {"message": "matching 1 tokens", "serial": f"TOTP_{user.upper()}"},
                    "version": "privacyIDEA 3.9"
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "result": {"status": True, "value": False},
                    "detail": {"message": "Wrong OTP or password value"},
                    "version": "privacyIDEA 3.9"
                }

            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith("/token/list"):
            tokens = load_tokens()
            res = {}
            for u, data in tokens.items():
                res[u] = {
                    "realm": data["realm"],
                    "description": data["description"],
                    "has_secret": bool(data.get("secret"))
                }
            body = json.dumps({"tokens": res}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(("0.0.0.0", 5000), PrivacyIdeaHandler)
    print("[+] PrivacyIDEA Authentication Service listening on 0.0.0.0:5000")
    server.serve_forever()

if __name__ == "__main__":
    run()
