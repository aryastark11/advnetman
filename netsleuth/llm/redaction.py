import re

# Patterns for secrets to redact from configs and prompts
REDACTION_PATTERNS = [
    # Sha512 / Sha256 / MD5 password hashes in Arista configs: secret sha512 $6$...
    (r'(secret\s+(?:sha512|sha256|md5|0|5|8|9)?\s*)\S+', r'\1[REDACTED_PASSWORD_HASH]'),
    (r'(password\s+(?:0|5|7|8)?\s*)\S+', r'\1[REDACTED_PASSWORD]'),
    # SNMP communities
    (r'(snmp-server\s+community\s+)(\S+)', r'\1[REDACTED_COMMUNITY]'),
    # Generic tokens, keys, passwords
    (r'(?:token|secret_id|root_token|api_key)["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'token: "[REDACTED_SECRET]"'),
    (r'hvs\.[a-zA-Z0-9_-]{20,}', '[REDACTED_VAULT_TOKEN]'),
    (r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_API_KEY]'),
]

def redact_sensitive_data(text: str) -> str:
    if not text:
        return ""
    redacted = str(text)
    for pattern, replacement in REDACTION_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted
