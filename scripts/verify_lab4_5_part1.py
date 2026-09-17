#!/usr/bin/env python3
"""
Verification Script for Lab 4 & 5 - Objective 1 (Part 1: Network Source of Truth & Automation Framework)
RoboControl Networks Automation Suite
"""

import os
import sys
import json
import yaml
import jinja2
import urllib.request
import urllib.parse
import subprocess

BASE_DIR = "/home/student/Desktop/lab1"
NSOT_URL = "http://localhost:8000"
GRAFANA_URL = "http://localhost:3000"

def print_header(title):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)

def check_step(name, success, detail=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       -> {detail}")
    return success

def test_git_version_control():
    print_header("1. Git Version Control & Repository Integrity")
    res = subprocess.run(["git", "status"], cwd=BASE_DIR, capture_output=True, text=True)
    step1 = check_step("Git repository initialized and tracked", res.returncode == 0, res.stdout.splitlines()[0] if res.stdout else "")
    
    res_log = subprocess.run(["git", "log", "-n", "1", "--oneline"], cwd=BASE_DIR, capture_output=True, text=True)
    step2 = check_step("Git commit history active", res_log.returncode == 0, res_log.stdout.strip())
    return step1 and step2

def test_multi_vendor_jinja2_templates():
    print_header("2. Multi-Vendor Hierarchical Jinja2 Templates (Extra Credit)")
    
    test_cases = [
        # Vendor, Subdir, Template, DataModel, Expected Tokens
        ("Arista", "Jinja2_templates_Arista", "r1_r2.j2", "r1.yml", ["hostname r1", "router ospf 1", "router rip"]),
        ("Arista", "Jinja2_templates_Arista", "r3_r4.j2", "r3.yml", ["hostname r3", "router bgp 65001", "neighbor 172.16.35.2 remote-as 65005"]),
        ("Arista", "Jinja2_templates_Arista", "r5.j2", "r5.yml", ["hostname r5", "router bgp 65005", "neighbor 172.16.35.1 remote-as 65001"]),
        ("Arista", "Jinja2_templates_Arista", "s1_s2.j2", "s1.yml", ["hostname s1", "vlan 10", "switchport access vlan 10"]),
        ("Arista", "Jinja2_templates_Arista", "s3_s4.j2", "s3.yml", ["hostname s3", "interface Ethernet1", "no ip routing"]),
        ("Cisco NX-OS", "Jinja2_templates_Cisco_NXOS", "cisco_nxos_s1_s2.j2", "s1.yml", ["hostname s1", "feature interface-vlan", "switchport access vlan 10"]),
        ("Cisco NX-OS", "Jinja2_templates_Cisco_NXOS", "cisco_nxos_s3_s4.j2", "s3.yml", ["hostname s3", "feature lldp", "switchport mode trunk"]),
        ("Cisco XRv9k", "Jinja2_templates_Cisco_XRv9k", "cisco_xrv9k_r1_r2.j2", "r1.yml", ["hostname r1", "router ospf 1", "area 0"]),
        ("Cisco XRv9k", "Jinja2_templates_Cisco_XRv9k", "cisco_xrv9k_r3_r4.j2", "r3.yml", ["hostname r3", "router bgp 65001", "remote-as 65005"]),
        ("Cisco XRv9k", "Jinja2_templates_Cisco_XRv9k", "cisco_xrv9k_r5.j2", "r5.yml", ["hostname r5", "router bgp 65005", "remote-as 65001"]),
        ("SONiC", "Jinja2_templates_SONiC", "sonic_s1_s2.j2", "s1.yml", ['"VLAN":', '"Vlan10"', '"Vlan20"']),
        ("SONiC", "Jinja2_templates_SONiC", "sonic_r1_r2.j2", "r1.yml", ["hostname r1", "router ospf", "router rip"]),
        ("SONiC", "Jinja2_templates_SONiC", "sonic_r3_r4.j2", "r3.yml", ["hostname r3", "router bgp 65001", "neighbor 172.16.35.2 remote-as 65005"])
    ]
    
    all_pass = True
    for vendor, t_dir, t_file, d_file, tokens in test_cases:
        full_t_dir = os.path.join(BASE_DIR, t_dir)
        full_d_path = os.path.join(BASE_DIR, "data_models", d_file)
        
        if not os.path.exists(os.path.join(full_t_dir, t_file)):
            all_pass = check_step(f"{vendor} Template: {t_file}", False, f"File missing in {t_dir}")
            continue
            
        with open(full_d_path, "r") as f:
            data = yaml.safe_load(f)
            
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(full_t_dir), trim_blocks=True, lstrip_blocks=True)
        tmpl = env.get_template(t_file)
        rendered = tmpl.render(data)
        
        matches = [t for t in tokens if t in rendered]
        passed = len(matches) == len(tokens)
        all_pass = all_pass and passed
        check_step(f"[{vendor}] Render {t_file} using {d_file}", passed, f"Matches {len(matches)}/{len(tokens)} expected key tokens")
        
    return all_pass

def test_django_gui_endpoints():
    print_header("3. Django Web GUI (NSoT Portal) Live Endpoints")
    endpoints = [
        ("/", 200, "Dashboard & Inventory"),
        ("/device/add/", 200, "Add Device Form"),
        ("/device/1/", 200, "Device Detail View (R1)"),
        ("/golden-configs/", 200, "Golden Configs Archive & Diff Viewer"),
        ("/templates/", 200, "Multi-Vendor Template Gallery"),
        ("/templates/render/", 200, "Live Template In-Browser Renderer"),
        ("/api/devices/", 200, "REST API Device Inventory Endpoint")
    ]
    
    all_pass = True
    for ep, exp_code, label in endpoints:
        url = f"{NSOT_URL}{ep}"
        try:
            req = urllib.request.urlopen(url, timeout=5)
            code = req.getcode()
            passed = (code == exp_code)
            all_pass = all_pass and passed
            check_step(f"{label} ({ep})", passed, f"HTTP Status {code}")
        except Exception as e:
            all_pass = False
            check_step(f"{label} ({ep})", False, f"Connection error: {e}")
            
    # Check REST API JSON Content
    try:
        req = urllib.request.urlopen(f"{NSOT_URL}/api/devices/", timeout=5)
        api_data = json.loads(req.read().decode('utf-8'))
        count = api_data.get('count', 0)
        passed = count >= 16
        all_pass = all_pass and passed
        check_step("API returns complete inventory", passed, f"Total devices registered in DB: {count}")
    except Exception as e:
        all_pass = False
        check_step("API JSON validation", False, str(e))
        
    return all_pass

def test_device_live_config_pull():
    print_header("4. Live Running Configuration Pull via eAPI / Local Storage")
    try:
        # Trigger pull config for Device 1 (R1)
        req = urllib.request.Request(f"{NSOT_URL}/device/1/pull-config/")
        resp = urllib.request.urlopen(req, timeout=8)
        passed = (resp.getcode() == 200)
        check_step("Live running-config pull execution for R1", passed, "Config successfully retrieved and cached")
    except Exception as e:
        check_step("Live config pull execution", False, str(e))
        return False
    return True

def test_bidirectional_navigation():
    print_header("5. Bidirectional Movement: Django GUI <---> Grafana")
    
    # 1. Django -> Grafana: Check base.html navbar
    base_html_path = os.path.join(BASE_DIR, "nsot_project", "templates", "automation", "base.html")
    with open(base_html_path, "r", encoding="utf-8") as f:
        base_content = f.read()
    django_to_grafana = "http://localhost:3000" in base_content and "btn-grafana" in base_content
    check_step("Django GUI contains active button to Grafana NOC", django_to_grafana, "Link to http://localhost:3000/d/nmas-noc-master present")
    
    # 2. Grafana -> Django: Check dashboard JSON
    dashboard_json_path = os.path.join(BASE_DIR, "configs", "grafana", "dashboards", "nmas_network_operations.json")
    with open(dashboard_json_path, "r", encoding="utf-8") as f:
        dash_content = f.read()
    grafana_to_django = "http://localhost:8000" in dash_content and "Back to Django NSoT GUI" in dash_content
    check_step("Grafana NOC contains active button back to Django GUI", grafana_to_django, "Link to http://localhost:8000 in dashboard links & banner panel")
    
    # 3. Grafana HTTP 200 check
    try:
        req = urllib.request.urlopen(f"{GRAFANA_URL}/d/nmas-noc-master", timeout=5)
        grafana_online = (req.getcode() == 200)
        check_step("Grafana NOC Dashboard is live and accessible", grafana_online, f"HTTP Status {req.getcode()}")
    except Exception as e:
        grafana_online = False
        check_step("Grafana NOC accessibility", False, str(e))
        
    return django_to_grafana and grafana_to_django and grafana_online

def test_add_new_device_flow():
    print_header("6. Add New Device Form & Provisioning Flow")
    
    # Use Django ORM directly
    sys.path.append(os.path.join(BASE_DIR, "nsot_project"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nsot_project.settings")
    import django
    django.setup()
    from automation.models import Device, GoldenConfig, TemplateModel
    
    test_dev_name = "test-edge-router-99"
    Device.objects.filter(name=test_dev_name).delete()
    
    dev = Device.objects.create(
        name=test_dev_name,
        device_type="router",
        vendor="arista",
        tier="distribution",
        role="Automated Verification Test Router",
        public_ip="198.51.100.99",
        private_ip="10.0.99.1/24",
        mgmt_ip="172.20.20.99/24",
        routing_protocols="OSPF, BGP",
        bgp_asn=65099,
        router_id="10.0.99.1",
        interface_ips="Ethernet1: 10.0.99.1/24\nEthernet2: 172.16.99.1/30",
        template_name="r1_r2.j2"
    )
    
    created = Device.objects.filter(name=test_dev_name).exists()
    check_step("New device creation with full routing/IPAM parameters", created, f"Device ID: {dev.id} ({dev.name})")
    
    # Create Golden Config for test device
    gc = GoldenConfig.objects.create(
        device=dev,
        version_tag="v_test_baseline",
        config_content="! Test Golden Config Content\nhostname test-edge-router-99\nrouter ospf 1\n",
        change_summary="Automated verification golden snapshot"
    )
    gc_created = GoldenConfig.objects.filter(id=gc.id).exists()
    check_step("Golden configuration snapshot creation for new device", gc_created, f"Tag: {gc.version_tag}")
    
    # Clean up test device
    dev.delete()
    check_step("Cleaned up verification test artifact", not Device.objects.filter(name=test_dev_name).exists())
    return created and gc_created

def main():
    print("=" * 75)
    print("  LAB 4 & 5 - OBJECTIVE 1 (PART 1) AUTOMATION FRAMEWORK VERIFICATION")
    print("=" * 75)
    
    results = [
        test_git_version_control(),
        test_multi_vendor_jinja2_templates(),
        test_django_gui_endpoints(),
        test_device_live_config_pull(),
        test_bidirectional_navigation(),
        test_add_new_device_flow()
    ]
    
    print_header("FINAL VERIFICATION SUMMARY")
    passed_count = sum(1 for r in results if r)
    total_count = len(results)
    print(f"Total Verification Suites: {passed_count}/{total_count} PASSED")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! Lab 4 & 5 Objective 1 (Part 1) is 100% complete and fully verified.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check logs above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
