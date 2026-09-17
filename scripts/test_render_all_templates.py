#!/usr/bin/env python3
import os
import yaml
import jinja2

BASE_DIR = "/home/student/Desktop/lab1"
DATA_DIR = os.path.join(BASE_DIR, "data_models")
ARISTA_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Arista")
NXOS_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_NXOS")
XRV_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_XRv9k")
SONIC_DIR = os.path.join(BASE_DIR, "Jinja2_templates_SONiC")

def render_template(template_dir, template_file, data_file):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template_file)
    with open(os.path.join(DATA_DIR, data_file)) as f:
        data = yaml.safe_load(f)
    return template.render(data)

print("="*75)
print("   TESTING TEMPLATE RENDERING ACROSS TIERS & VENDORS   ")
print("="*75)

test_cases = [
    # (Vendor / Tier, Template Dir, Template File, Data File)
    ("Arista Distribution (R1)", ARISTA_DIR, "r1_r2.j2", "r1.yml"),
    ("Arista Distribution / DHCP (R2)", ARISTA_DIR, "r1_r2.j2", "r2.yml"),
    ("Arista ASBR (R3)", ARISTA_DIR, "r3_r4.j2", "r3.yml"),
    ("Arista ASBR (R4)", ARISTA_DIR, "r3_r4.j2", "r4.yml"),
    ("Arista PE WAN (R5)", ARISTA_DIR, "r5.j2", "r5.yml"),
    ("Arista Access Switch (S1)", ARISTA_DIR, "s1_s2.j2", "s1.yml"),
    ("Arista Core Switch (S3)", ARISTA_DIR, "s3_s4.j2", "s3.yml"),
    
    # Cisco NX-OS (Extra Credit)
    ("Cisco NX-OS Access Switch (S1)", NXOS_DIR, "cisco_nxos_s1_s2.j2", "s1.yml"),
    ("Cisco NX-OS Core Switch (S3)", NXOS_DIR, "cisco_nxos_s3_s4.j2", "s3.yml"),
    
    # Cisco XRv 9000 (Extra Credit)
    ("Cisco XRv9k Distribution (R1)", XRV_DIR, "cisco_xrv9k_r1_r2.j2", "r1.yml"),
    ("Cisco XRv9k ASBR (R3)", XRV_DIR, "cisco_xrv9k_r3_r4.j2", "r3.yml"),
    ("Cisco XRv9k PE WAN (R5)", XRV_DIR, "cisco_xrv9k_r5.j2", "r5.yml"),
    
    # SONiC VS (Extra Credit)
    ("SONiC Access Switch (S1)", SONIC_DIR, "sonic_s1_s2.j2", "s1.yml"),
    ("SONiC Distribution (R1)", SONIC_DIR, "sonic_r1_r2.j2", "r1.yml"),
    ("SONiC ASBR (R3)", SONIC_DIR, "sonic_r3_r4.j2", "r3.yml"),
]

all_passed = True
for name, t_dir, t_file, d_file in test_cases:
    try:
        output = render_template(t_dir, t_file, d_file)
        lines = len(output.strip().splitlines())
        print(f"[\033[92mPASS\033[0m] {name:<35} -> {lines:>3} lines rendered")
    except Exception as e:
        print(f"[\033[91mFAIL\033[0m] {name:<35} -> Error: {e}")
        all_passed = False

print("="*75)
if all_passed:
    print("\033[92mALL 15 TEMPLATE RENDERING TEST CASES PASSED!\033[0m")
else:
    print("\033[91mSOME TESTS FAILED!\033[0m")
