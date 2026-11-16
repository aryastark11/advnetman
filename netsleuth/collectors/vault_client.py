import os
import json
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("netsleuth.vault")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VAULT_URL = os.environ.get("VAULT_ADDR", "https://127.0.0.1:8200")
CA_CERT = os.path.join(BASE_DIR, "vault", "certs", "ca.crt")

class VaultManager:
    def __init__(self):
        self._client = None
        self._authenticated = False

    def get_client(self):
        if self._client and self._authenticated:
            return self._client

        try:
            import hvac
            client = hvac.Client(url=VAULT_URL, verify=CA_CERT if os.path.exists(CA_CERT) else False)
            
            # 1. Try AppRole
            approle_file = os.path.expanduser("~/.vault_approle.json")
            if os.path.exists(approle_file):
                try:
                    with open(approle_file, "r") as f:
                        data = json.load(f)
                    role_id = data.get("role_id")
                    secret_id = data.get("secret_id")
                    if role_id and secret_id:
                        client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                        if client.is_authenticated():
                            self._client = client
                            self._authenticated = True
                            return self._client
                except Exception as e:
                    logger.debug(f"AppRole login failed: {e}")

            # 2. Try root token if available
            keys_file = os.path.expanduser("~/.vault_keys.json")
            if os.path.exists(keys_file):
                try:
                    with open(keys_file, "r") as f:
                        kdata = json.load(f)
                    token = kdata.get("root_token")
                    if token:
                        client.token = token
                        if client.is_authenticated():
                            self._client = client
                            self._authenticated = True
                            return self._client
                except Exception as e:
                    logger.debug(f"Root token login failed: {e}")

            self._client = client
            return self._client
        except Exception as e:
            logger.warning(f"Vault client initialization error: {e}")
            return None

    def get_device_credentials(self, hostname: str) -> Tuple[str, str]:
        """Fetch username and password for a device from network/devices/<hostname>."""
        client = self.get_client()
        if client and self._authenticated:
            # Try upper case, lower case, original
            for name_variant in [hostname.upper(), hostname.lower(), hostname]:
                try:
                    secret = client.secrets.kv.v2.read_secret_version(
                        mount_point="network",
                        path=f"devices/{name_variant}"
                    )
                    data = secret.get("data", {}).get("data", {})
                    u = data.get("username", "admin")
                    p = data.get("password", "admin")
                    return u, p
                except Exception:
                    continue
        return "admin", "admin"

    def get_gemini_api_key(self) -> Optional[str]:
        """Fetch Gemini API key from environment or Vault."""
        # Check environment first
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            return env_key

        # Check Vault under nmas-admin/llm or nmas-admin/gemini
        client = self.get_client()
        if client and self._authenticated:
            for path in ["llm", "gemini"]:
                try:
                    secret = client.secrets.kv.v2.read_secret_version(
                        mount_point="nmas-admin",
                        path=path
                    )
                    data = secret.get("data", {}).get("data", {})
                    key = data.get("api_key") or data.get("gemini_api_key")
                    if key:
                        return key
                except Exception:
                    continue
        return None

vault_manager = VaultManager()
