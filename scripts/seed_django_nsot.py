#!/usr/bin/env python3
"""
Populates Django NSoT database with all 16 network devices,
Jinja2 templates, and baseline Golden Configurations.
"""

import os
import sys
import django
import yaml
from datetime import datetime

# Setup Django Environment
BASE_DIR = "/home/student/Desktop/lab1"
sys.path.append(os.path.join(BASE_DIR, "nsot_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nsot_project.settings")
django.setup()

from automation.models import Device, TemplateModel, GoldenConfig
from automation.views import pull_live_config_from_node

DATA_MODELS_DIR = os.path.join(BASE_DIR, "data_models")
ARISTA_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Arista")
NXOS_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_NXOS")
XRV_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_XRv9k")
SONIC_DIR = os.path.join(BASE_DIR, "Jinja2_templates_SONiC")
GOLDEN_CONFIGS_DIR = os.path.join(BASE_DIR, "golden_configs")
os.makedirs(GOLDEN_CONFIGS_DIR, exist_ok=True)

print("="*75)
print("   SEEDING DJANGO NETWORK SOURCE OF TRUTH (NSoT) DATABASE   ")
print("="*75)

# 1. Seed Templates
templates_data = [
    # Arista
    ("r1_r2.j2", "arista", "Tier 1: Distribution Routers (R1-R2)", ARISTA_DIR, "Arista EOS Distribution Template with OSPF, RIP, and DHCP options."),
    ("r3_r4.j2", "arista", "Tier 2: ASBR Core Routers (R3-R4)", ARISTA_DIR, "Arista EOS ASBR Template with eBGP AS 65001 <-> AS 65005 & OSPF A0."),
    ("r5.j2", "arista", "Tier 3: PE WAN Gateway (R5)", ARISTA_DIR, "Arista EOS PE WAN Gateway Template with eBGP AS 65005 and Public DMZ."),
    ("s1_s2.j2", "arista", "Tier 4: Access Switches (S1-S2)", ARISTA_DIR, "Arista EOS Access Switch Template with VLANs 10,20,30 and 802.1Q Trunks."),
    ("s3_s4.j2", "arista", "Tier 5: Core Backbone Switches (S3-S4)", ARISTA_DIR, "Arista EOS Core Switch Template with Core Transit and cross-links."),
    
    # Cisco NX-OS
    ("cisco_nxos_s1_s2.j2", "cisco_nxos", "Tier 4: Access Switches (S1-S2)", NXOS_DIR, "Cisco NX-OS 9000v Access Switch Template with VLANs, Trunks & Rapid-PVST."),
    ("cisco_nxos_s3_s4.j2", "cisco_nxos", "Tier 5: Core Backbone Switches (S3-S4)", NXOS_DIR, "Cisco NX-OS 9000v Core Switch Template with Core VLAN bridging."),
    
    # Cisco XRv 9000
    ("cisco_xrv9k_r1_r2.j2", "cisco_xrv", "Tier 1: Distribution Routers (R1-R2)", XRV_DIR, "Cisco IOS-XRv 9000 Distribution Router Template with OSPF, RIP, sub-interfaces."),
    ("cisco_xrv9k_r3_r4.j2", "cisco_xrv", "Tier 2: ASBR Core Routers (R3-R4)", XRV_DIR, "Cisco IOS-XRv 9000 ASBR Template with BGP 65001 & OSPF."),
    ("cisco_xrv9k_r5.j2", "cisco_xrv", "Tier 3: PE WAN Gateway (R5)", XRV_DIR, "Cisco IOS-XRv 9000 PE Router Template with BGP 65005 & DMZ."),
    
    # SONiC
    ("sonic_s1_s2.j2", "sonic", "Tier 4: Access Switches (S1-S2)", SONIC_DIR, "SONiC VS config_db.json Template for VLANs and Port Assignments."),
    ("sonic_r1_r2.j2", "sonic", "Tier 1: Distribution Routers (R1-R2)", SONIC_DIR, "SONiC FRR Routing Template for Distribution Routers."),
    ("sonic_r3_r4.j2", "sonic", "Tier 2: ASBR Core Routers (R3-R4)", SONIC_DIR, "SONiC FRR Routing Template for ASBR BGP & OSPF Routers.")
]

for name, vendor, tier, path_dir, desc in templates_data:
    fpath = os.path.join(path_dir, name)
    if os.path.exists(fpath):
        with open(fpath, "r") as f:
            content = f.read()
        tmpl_obj, created = TemplateModel.objects.update_or_create(
            name=name,
            defaults={
                "vendor": vendor,
                "tier": tier,
                "content": content,
                "description": desc
            }
        )
        print(f"[TEMPLATE] {'Created' if created else 'Updated'}: [{vendor.upper()}] {name}")

# 2. Seed All 16 Devices
raw_devices = [
    # Routers
    {"name": "r1", "type": "router", "vendor": "arista", "tier": "distribution", "role": "Distribution Router (VLAN 10/20 Routing, RIPv2, OSPF Area 0)", "mgmt_ip": "172.20.20.11/24", "private_ip": "10.0.0.1", "public_ip": None, "routing_protocols": "OSPF, RIPv2", "bgp_asn": None, "router_id": "10.0.0.1", "template_name": "r1_r2.j2"},
    {"name": "r2", "type": "router", "vendor": "arista", "tier": "distribution", "role": "Distribution Router & DHCP Server (VLAN 10/20/30, OSPF A0, DHCPv4/v6)", "mgmt_ip": "172.20.20.12/24", "private_ip": "10.0.0.2", "public_ip": None, "routing_protocols": "OSPF, RIPv2, DHCP Server", "bgp_asn": None, "router_id": "10.0.0.2", "template_name": "r1_r2.j2"},
    {"name": "r3", "type": "router", "vendor": "arista", "tier": "asbr", "role": "Autonomous System Boundary Router (eBGP AS 65001 <-> 65005, OSPF A0)", "mgmt_ip": "172.20.20.13/24", "private_ip": "10.0.0.3", "public_ip": None, "routing_protocols": "BGP, OSPF", "bgp_asn": 65001, "router_id": "10.0.0.3", "template_name": "r3_r4.j2"},
    {"name": "r4", "type": "router", "vendor": "arista", "tier": "asbr", "role": "Autonomous System Boundary Router (eBGP AS 65001 <-> 65005, OSPF A0)", "mgmt_ip": "172.20.20.14/24", "private_ip": "10.0.0.4", "public_ip": None, "routing_protocols": "BGP, OSPF", "bgp_asn": 65001, "router_id": "10.0.0.4", "template_name": "r3_r4.j2"},
    {"name": "r5", "type": "router", "vendor": "arista", "tier": "pe_router", "role": "Provider Edge Router (AS 65005, Public DMZ Web Server Transit)", "mgmt_ip": "172.20.20.15/24", "private_ip": "172.16.35.2", "public_ip": "198.51.100.1", "routing_protocols": "BGP", "bgp_asn": 65005, "router_id": "198.51.100.1", "template_name": "r5.j2"},
    
    # Switches
    {"name": "s1", "type": "switch", "vendor": "arista", "tier": "access_switch", "role": "Access Switch (VLANs 10, 20, 30, Trunk to R1 & S2)", "mgmt_ip": "172.20.20.21/24", "private_ip": "172.20.20.21", "public_ip": None, "vlans": "10,20,30", "template_name": "s1_s2.j2"},
    {"name": "s2", "type": "switch", "vendor": "arista", "tier": "access_switch", "role": "Access Switch (VLANs 10, 20, 30, Trunk to R2 & S1)", "mgmt_ip": "172.20.20.22/24", "private_ip": "172.20.20.22", "public_ip": None, "vlans": "10,20,30", "template_name": "s1_s2.j2"},
    {"name": "s3", "type": "switch", "vendor": "arista", "tier": "core_switch", "role": "Core Switch (OSPF Area 0 Backbone Bridge: R3, R1, S4, NMAS)", "mgmt_ip": "172.20.20.23/24", "private_ip": "172.20.20.23", "public_ip": None, "template_name": "s3_s4.j2"},
    {"name": "s4", "type": "switch", "vendor": "arista", "tier": "core_switch", "role": "Core Switch (OSPF Area 0 Backbone Bridge: R4, R2, S3)", "mgmt_ip": "172.20.20.24/24", "private_ip": "172.20.20.24", "public_ip": None, "template_name": "s3_s4.j2"},
    
    # End Hosts
    {"name": "h1", "type": "host", "vendor": "linux", "tier": "host", "role": "VLAN 10 Test Host", "mgmt_ip": "172.20.20.101/24", "private_ip": "10.10.10.101/24", "vlans": "10"},
    {"name": "h2", "type": "host", "vendor": "linux", "tier": "host", "role": "VLAN 20 Test Host", "mgmt_ip": "172.20.20.102/24", "private_ip": "10.10.20.102/24", "vlans": "20"},
    {"name": "h3", "type": "host", "vendor": "linux", "tier": "host", "role": "VLAN 10 Test Host", "mgmt_ip": "172.20.20.103/24", "private_ip": "10.10.10.103/24", "vlans": "10"},
    {"name": "h4", "type": "host", "vendor": "linux", "tier": "host", "role": "VLAN 30 IPv6-Only Test Host", "mgmt_ip": "172.20.20.104/24", "private_ip": "IPv6-Only (2001:db8:30::104/64)", "vlans": "30"},
    
    # Management & Dedicated Servers
    {"name": "nmas", "type": "nmas", "vendor": "linux", "tier": "management", "role": "Network Management & Automation Station", "mgmt_ip": "172.20.20.100/24", "private_ip": "10.0.0.100/24"},
    {"name": "web-server", "type": "server", "vendor": "linux", "tier": "management", "role": "Internet Public Web Server", "mgmt_ip": "172.20.20.200/24", "private_ip": "198.51.100.10/24", "public_ip": "198.51.100.10"},
    {"name": "backup-server", "type": "backup", "vendor": "linux", "tier": "management", "role": "Isolated Data Lake Backup Node (10.99.99.2/30)", "mgmt_ip": "172.20.20.199/24", "private_ip": "10.99.99.2/30"}
]

for dev_data in raw_devices:
    name = dev_data["name"]
    
    # Load YAML model if available
    yaml_file = os.path.join(DATA_MODELS_DIR, f"{name}.yml")
    yaml_text = ""
    if os.path.exists(yaml_file):
        with open(yaml_file, "r") as f:
            yaml_text = f.read()

    dev, created = Device.objects.update_or_create(
        name=name,
        defaults={
            "device_type": dev_data["type"],
            "vendor": dev_data["vendor"],
            "tier": dev_data.get("tier", "distribution"),
            "role": dev_data.get("role", ""),
            "mgmt_ip": dev_data.get("mgmt_ip"),
            "private_ip": dev_data.get("private_ip"),
            "public_ip": dev_data.get("public_ip"),
            "routing_protocols": dev_data.get("routing_protocols", ""),
            "bgp_asn": dev_data.get("bgp_asn"),
            "router_id": dev_data.get("router_id"),
            "vlans": dev_data.get("vlans", ""),
            "template_name": dev_data.get("template_name", ""),
            "custom_config_yaml": yaml_text,
            "status": "Online"
        }
    )

    # Pull live running config
    ok, live_cfg = pull_live_config_from_node(dev)
    if ok:
        dev.running_config = live_cfg
        dev.last_config_pulled_at = datetime.now()
        dev.save()

        # Create initial Golden Configuration snapshot
        tag = "v1.0-baseline"
        gc, _ = GoldenConfig.objects.update_or_create(
            device=dev,
            version_tag=tag,
            defaults={
                "config_content": live_cfg,
                "change_summary": f"Initial automated baseline golden config for {name.upper()}",
                "created_by": "RoboControl Automation Seeder"
            }
        )
        with open(os.path.join(GOLDEN_CONFIGS_DIR, f"{name}_{tag}.cfg"), "w") as gf:
            gf.write(live_cfg)

    print(f"[DEVICE] {'Created' if created else 'Updated'}: {name.upper()} ({dev.get_device_type_display()} - {dev.get_vendor_display()})")

print("\n" + "="*75)
print(f"   DATABASE SEEDING COMPLETE: {Device.objects.count()} Devices, {TemplateModel.objects.count()} Templates, {GoldenConfig.objects.count()} Golden Configs")
print("="*75)
