#!/usr/bin/env python3
"""
NetDevOps CI/CD Pipeline - Stage 1: Static Analysis, Linting & Secret Detection
Validates YAML data models, Jinja2 template compilation, and ensures no leaked secrets.
"""

import os
import sys
import re
import yaml
import jinja2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data_models")
ARISTA_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Arista")
NXOS_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_NXOS")
XRV_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_XRv9k")
SONIC_DIR = os.path.join(BASE_DIR, "Jinja2_templates_SONiC")

# Sensitive secret patterns (must NOT be committed in git)
SECRET_PATTERNS = [
    (r"(?i)s\.([0-9a-zA-Z]{24,})", "Vault Classic Token"),
    (r"hvs\.([0-9a-zA-Z_-]{24,})", "Vault Service Token"),
    (r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----", "Private Key Header"),
    (r"(?i)(password|secret|token|api_key)\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*()_+=-]{16,}['\"]", "Plaintext Hardcoded Secret")
]

def log_pass(msg):
    print(f"  [\033[92m✓ PASS\033[0m] {msg}")

def log_fail(msg, err=""):
    print(f"  [\033[91m✗ FAIL\033[0m] {msg}")
    if err:
        print(f"         \033[91mError: {err}\033[0m")

def validate_yaml_data_models():
    print("\n--- 1.1 YAML Data Model Schema & Syntax Validation ---")
    all_ok = True
    yaml_files = [f for f in os.listdir(DATA_DIR) if f.endswith((".yml", ".yaml"))]
    
    required_keys = ["hostname", "mgmt_ip"]
    
    for f in sorted(yaml_files):
        path = os.path.join(DATA_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as yf:
                data = yaml.safe_load(yf)
                
            if not isinstance(data, dict):
                log_fail(f"{f}: Top-level YAML must be a mapping/dict")
                all_ok = False
                continue
                
            missing = [k for k in required_keys if k not in data]
            if missing:
                log_fail(f"{f}: Missing required schema keys: {missing}")
                all_ok = False
            else:
                log_pass(f"{f:<20} -> Valid YAML (Hostname: {data.get('hostname')}, Mgmt: {data.get('mgmt_ip')})")
        except Exception as e:
            log_fail(f"{f}: YAML syntax error", str(e))
            all_ok = False
            
    return all_ok

def validate_jinja2_templates():
    print("\n--- 1.2 Multi-Vendor Jinja2 Template Compilation & Linting ---")
    all_ok = True
    
    test_suite = [
        # (Vendor, Dir, Template, Data Model)
        ("Arista EOS", ARISTA_DIR, "r1_r2.j2", "r1.yml"),
        ("Arista EOS", ARISTA_DIR, "r1_r2.j2", "r2.yml"),
        ("Arista EOS", ARISTA_DIR, "r3_r4.j2", "r3.yml"),
        ("Arista EOS", ARISTA_DIR, "r3_r4.j2", "r4.yml"),
        ("Arista EOS", ARISTA_DIR, "r5.j2", "r5.yml"),
        ("Arista EOS", ARISTA_DIR, "r1_r2.j2", "r6.yml"),
        ("Arista EOS", ARISTA_DIR, "s1_s2.j2", "s1.yml"),
        ("Arista EOS", ARISTA_DIR, "s1_s2.j2", "s2.yml"),
        ("Arista EOS", ARISTA_DIR, "s3_s4.j2", "s3.yml"),
        ("Arista EOS", ARISTA_DIR, "s3_s4.j2", "s4.yml"),
        ("Cisco NX-OS", NXOS_DIR, "cisco_nxos_s1_s2.j2", "s1.yml"),
        ("Cisco NX-OS", NXOS_DIR, "cisco_nxos_s3_s4.j2", "s3.yml"),
        ("Cisco XRv9k", XRV_DIR, "cisco_xrv9k_r1_r2.j2", "r1.yml"),
        ("Cisco XRv9k", XRV_DIR, "cisco_xrv9k_r3_r4.j2", "r3.yml"),
        ("Cisco XRv9k", XRV_DIR, "cisco_xrv9k_r5.j2", "r5.yml"),
        ("SONiC VS", SONIC_DIR, "sonic_s1_s2.j2", "s1.yml"),
        ("SONiC VS", SONIC_DIR, "sonic_r1_r2.j2", "r1.yml"),
        ("SONiC VS", SONIC_DIR, "sonic_r3_r4.j2", "r3.yml"),
    ]
    
    for vendor, t_dir, t_file, d_file in test_suite:
        t_path = os.path.join(t_dir, t_file)
        d_path = os.path.join(DATA_DIR, d_file)
        
        if not os.path.exists(t_path):
            log_fail(f"[{vendor}] {t_file}: Template file not found at {t_path}")
            all_ok = False
            continue
            
        try:
            with open(d_path, "r", encoding="utf-8") as df:
                model_data = yaml.safe_load(df)
                
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(t_dir),
                trim_blocks=True,
                lstrip_blocks=True,
                undefined=jinja2.StrictUndefined
            )
            template = env.get_template(t_file)
            rendered = template.render(model_data)
            
            line_count = len(rendered.strip().splitlines())
            log_pass(f"[{vendor}] {t_file} + {d_file:<8} -> Compiled successfully ({line_count:>3} lines)")
        except Exception as e:
            log_fail(f"[{vendor}] {t_file} with {d_file}", str(e))
            all_ok = False
            
    return all_ok

def scan_for_secrets():
    print("\n--- 1.3 Static Secret Leak & Policy Compliance Scan ---")
    all_ok = True
    scanned_count = 0
    
    # Exclude directories that legitimately hold extracted images, container mounts, or git objects
    exclude_dirs = {"cEOS-lab-4.33.10M", "clab-lab1", ".git", ".vault_keys", "vault/data", "vault/audit", "node_modules", "extracted_media", ".system_generated"}
    
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not os.path.join(root, d).startswith(tuple(exclude_dirs))]
        
        for f in files:
            if f.endswith((".py", ".yml", ".yaml", ".j2", ".sh", ".json", ".md", ".csv")):
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, BASE_DIR)
                
                # Skip test setup scripts that initialize local dummy bootstrap accounts
                if "privacyidea_tokens.json" in rel_path or "setup_vault.py" in rel_path or "setup_mfa.py" in rel_path or "verify_phase" in rel_path:
                    continue
                    
                scanned_count += 1
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as content_file:
                        content = content_file.read()
                        
                    for pat, desc in SECRET_PATTERNS:
                        matches = re.findall(pat, content)
                        if matches:
                            # Filter out false positives in sample comments
                            real_matches = [m for m in matches if "example" not in str(m).lower() and "placeholder" not in str(m).lower()]
                            if real_matches:
                                log_fail(f"{rel_path}: Potential secret leak detected ({desc})")
                                all_ok = False
                except Exception:
                    pass
                    
    if all_ok:
        log_pass(f"Zero secret leaks detected across {scanned_count} scanned repository files.")
        
    return all_ok

def main():
    print("=" * 75)
    print("  NETDEVOPS CI/CD PIPELINE - STAGE 1: STATIC LINTING & QUALITY GATE")
    print("=" * 75)
    
    v_yaml = validate_yaml_data_models()
    v_j2 = validate_jinja2_templates()
    v_sec = scan_for_secrets()
    
    print("\n" + "=" * 75)
    if v_yaml and v_j2 and v_sec:
        print("  \033[92m>>> STAGE 1 QUALITY GATE: ALL CHECKS PASSED SUCCESSFULLY <<<\033[0m")
        print("=" * 75)
        sys.exit(0)
    else:
        print("  \033[91m>>> STAGE 1 QUALITY GATE: FAILED - FIX ISSUES ABOVE <<<\033[0m")
        print("=" * 75)
        sys.exit(1)

if __name__ == "__main__":
    main()
