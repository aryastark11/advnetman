#!/usr/bin/env python3
"""
Generates complete YAML data models and Jinja2 templates across tiers and vendors:
1. Arista cEOS (Jinja2_templates_Arista/)
2. Cisco 9000v NX-OS (Jinja2_templates_Cisco_NXOS/)
3. Cisco XRv 9000 (Jinja2_templates_Cisco_XRv9k/)
4. SONiC VS sonic-vs (Jinja2_templates_SONiC/)
"""

import os
import yaml

BASE_DIR = "/home/student/Desktop/lab1"
DATA_MODELS_DIR = os.path.join(BASE_DIR, "data_models")
ARISTA_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Arista")
NXOS_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_NXOS")
XRV_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_XRv9k")
SONIC_DIR = os.path.join(BASE_DIR, "Jinja2_templates_SONiC")

for d in [DATA_MODELS_DIR, ARISTA_DIR, NXOS_DIR, XRV_DIR, SONIC_DIR]:
    os.makedirs(d, exist_ok=True)

# ==============================================================================
# 1. YAML DATA MODELS
# ==============================================================================

data_models = {
    "r1.yml": {
        "hostname": "r1",
        "vendor": "arista",
        "tier": "distribution",
        "device_type": "router",
        "role": "Distribution Router (VLAN 10/20 Routing, RIPv2, OSPF Area 0)",
        "mgmt_ip": "172.20.20.11/24",
        "mgmt_ipv6": "2001:db8:ffff::5/64",
        "private_ip": "10.0.0.1",
        "public_ip": None,
        "ospf": {
            "process_id": 1,
            "router_id": "10.0.0.1",
            "redistribute": ["connected", "rip"]
        },
        "rip": {
            "enabled": True,
            "networks": ["10.10.10.0/24", "10.10.20.0/24"],
            "redistribute": ["ospf"]
        },
        "interfaces": [
            {
                "name": "Ethernet1",
                "cisco_name": "GigabitEthernet0/0/0/0",
                "sonic_name": "Ethernet0",
                "ip": "10.0.0.1/24",
                "ipv6": "2001:db8::1/64",
                "ospf_area": "0.0.0.0",
                "description": "Core Link to S3 (OSPF Area 0)"
            },
            {
                "name": "Ethernet2",
                "cisco_name": "GigabitEthernet0/0/0/1",
                "sonic_name": "Ethernet4",
                "routed": True,
                "description": "802.1Q Trunk Link to S1"
            }
        ],
        "subinterfaces": [
            {
                "parent": "Ethernet2",
                "sub_id": 10,
                "vlan_id": 10,
                "ip": "10.10.10.1/24",
                "ipv6": "2001:db8:10::1/64",
                "rip_enabled": True,
                "description": "VLAN 10 Gateway Sub-interface"
            },
            {
                "parent": "Ethernet2",
                "sub_id": 20,
                "vlan_id": 20,
                "ip": "10.10.20.1/24",
                "ipv6": "2001:db8:20::1/64",
                "rip_enabled": True,
                "description": "VLAN 20 Gateway Sub-interface"
            }
        ]
    },
    "r2.yml": {
        "hostname": "r2",
        "vendor": "arista",
        "tier": "distribution",
        "device_type": "router",
        "role": "Distribution Router & DHCP Server (VLAN 10/20/30, OSPF A0, DHCPv4/v6)",
        "mgmt_ip": "172.20.20.12/24",
        "mgmt_ipv6": "2001:db8:ffff::4/64",
        "private_ip": "10.0.0.2",
        "public_ip": None,
        "dhcp_server": [
            {
                "subnet": "10.10.10.0/24",
                "range_start": "10.10.10.100",
                "range_end": "10.10.10.200",
                "default_gateway": "10.10.10.1",
                "dns_server": "198.51.100.10"
            },
            {
                "subnet": "10.10.20.0/24",
                "range_start": "10.10.20.100",
                "range_end": "10.10.20.200",
                "default_gateway": "10.10.20.1",
                "dns_server": "198.51.100.10"
            },
            {
                "subnet_v6": "2001:db8:10::/64",
                "range_start": "2001:db8:10::100",
                "range_end": "2001:db8:10::200"
            },
            {
                "subnet_v6": "2001:db8:20::/64",
                "range_start": "2001:db8:20::100",
                "range_end": "2001:db8:20::200"
            },
            {
                "subnet_v6": "2001:db8:30::/64",
                "range_start": "2001:db8:30::100",
                "range_end": "2001:db8:30::200"
            }
        ],
        "ospf": {
            "process_id": 1,
            "router_id": "10.0.0.2",
            "redistribute": ["connected", "rip"]
        },
        "rip": {
            "enabled": True,
            "networks": ["10.10.10.0/24", "10.10.20.0/24"],
            "redistribute": ["ospf"]
        },
        "interfaces": [
            {
                "name": "Ethernet1",
                "cisco_name": "GigabitEthernet0/0/0/0",
                "sonic_name": "Ethernet0",
                "ip": "10.0.0.2/24",
                "ipv6": "2001:db8::2/64",
                "ospf_area": "0.0.0.0",
                "description": "Core Link to S4 (OSPF Area 0)"
            },
            {
                "name": "Ethernet2",
                "cisco_name": "GigabitEthernet0/0/0/1",
                "sonic_name": "Ethernet4",
                "routed": True,
                "description": "802.1Q Trunk Link to S2"
            }
        ],
        "subinterfaces": [
            {
                "parent": "Ethernet2",
                "sub_id": 10,
                "vlan_id": 10,
                "ip": "10.10.10.2/24",
                "ipv6": "2001:db8:10::2/64",
                "dhcp_ipv4": True,
                "dhcp_ipv6": True,
                "description": "VLAN 10 Sub-interface (DHCPv4/v6 Relay/Server)"
            },
            {
                "parent": "Ethernet2",
                "sub_id": 20,
                "vlan_id": 20,
                "ip": "10.10.20.2/24",
                "ipv6": "2001:db8:20::2/64",
                "dhcp_ipv4": True,
                "dhcp_ipv6": True,
                "description": "VLAN 20 Sub-interface (DHCPv4/v6 Relay/Server)"
            },
            {
                "parent": "Ethernet2",
                "sub_id": 30,
                "vlan_id": 30,
                "ipv6": "2001:db8:30::2/64",
                "dhcp_ipv6": True,
                "description": "VLAN 30 Sub-interface (IPv6-Only DHCP)"
            }
        ]
    },
    "r3.yml": {
        "hostname": "r3",
        "vendor": "arista",
        "tier": "asbr",
        "device_type": "router",
        "role": "Autonomous System Boundary Router (eBGP AS 65001 <-> 65005, OSPF A0)",
        "mgmt_ip": "172.20.20.13/24",
        "mgmt_ipv6": "2001:db8:ffff::a/64",
        "private_ip": "10.0.0.3",
        "public_ip": None,
        "bgp": {
            "local_asn": 65001,
            "router_id": "10.0.0.3",
            "neighbors": [
                {"ip": "172.16.35.2", "remote_as": 65005, "afi": "ipv4", "description": "eBGP to R5"},
                {"ip": "2001:db8:35::2", "remote_as": 65005, "afi": "ipv6", "description": "eBGP to R5"}
            ],
            "networks_ipv4": ["10.0.0.0/8"],
            "networks_ipv6": ["2001:db8::/32"],
            "redistribute": ["connected", "ospf"]
        },
        "ospf": {
            "process_id": 1,
            "router_id": "10.0.0.3",
            "default_originate": True,
            "redistribute": ["bgp", "connected"]
        },
        "interfaces": [
            {
                "name": "Ethernet1",
                "cisco_name": "GigabitEthernet0/0/0/0",
                "sonic_name": "Ethernet0",
                "ip": "172.16.35.1/30",
                "ipv6": "2001:db8:35::1/64",
                "description": "eBGP Link to R5 (PE AS 65005)"
            },
            {
                "name": "Ethernet2",
                "cisco_name": "GigabitEthernet0/0/0/1",
                "sonic_name": "Ethernet4",
                "ip": "10.0.0.3/24",
                "ipv6": "2001:db8::3/64",
                "ospf_area": "0.0.0.0",
                "description": "Core Link to S3 (OSPF Area 0)"
            }
        ]
    },
    "r4.yml": {
        "hostname": "r4",
        "vendor": "arista",
        "tier": "asbr",
        "device_type": "router",
        "role": "Autonomous System Boundary Router (eBGP AS 65001 <-> 65005, OSPF A0)",
        "mgmt_ip": "172.20.20.14/24",
        "mgmt_ipv6": "2001:db8:ffff::b/64",
        "private_ip": "10.0.0.4",
        "public_ip": None,
        "bgp": {
            "local_asn": 65001,
            "router_id": "10.0.0.4",
            "neighbors": [
                {"ip": "172.16.45.2", "remote_as": 65005, "afi": "ipv4", "description": "eBGP to R5"},
                {"ip": "2001:db8:45::2", "remote_as": 65005, "afi": "ipv6", "description": "eBGP to R5"}
            ],
            "networks_ipv4": ["10.0.0.0/8"],
            "networks_ipv6": ["2001:db8::/32"],
            "redistribute": ["connected", "ospf"]
        },
        "ospf": {
            "process_id": 1,
            "router_id": "10.0.0.4",
            "default_originate": True,
            "redistribute": ["bgp", "connected"]
        },
        "interfaces": [
            {
                "name": "Ethernet1",
                "cisco_name": "GigabitEthernet0/0/0/0",
                "sonic_name": "Ethernet0",
                "ip": "172.16.45.1/30",
                "ipv6": "2001:db8:45::1/64",
                "description": "eBGP Link to R5 (PE AS 65005)"
            },
            {
                "name": "Ethernet2",
                "cisco_name": "GigabitEthernet0/0/0/1",
                "sonic_name": "Ethernet4",
                "ip": "10.0.0.4/24",
                "ipv6": "2001:db8::4/64",
                "ospf_area": "0.0.0.0",
                "description": "Core Link to S4 (OSPF Area 0)"
            }
        ]
    },
    "r5.yml": {
        "hostname": "r5",
        "vendor": "arista",
        "tier": "pe_router",
        "device_type": "router",
        "role": "Provider Edge Router (AS 65005, Public DMZ Web Server Transit)",
        "mgmt_ip": "172.20.20.15/24",
        "mgmt_ipv6": "2001:db8:ffff::e/64",
        "private_ip": "172.16.35.2",
        "public_ip": "198.51.100.1",
        "bgp": {
            "local_asn": 65005,
            "router_id": "198.51.100.1",
            "neighbors": [
                {"ip": "172.16.35.1", "remote_as": 65001, "default_originate": True, "afi": "ipv4", "description": "eBGP to R3 (ASBR 65001)"},
                {"ip": "172.16.45.1", "remote_as": 65001, "default_originate": True, "afi": "ipv4", "description": "eBGP to R4 (ASBR 65001)"},
                {"ip": "2001:db8:35::1", "remote_as": 65001, "default_originate": True, "afi": "ipv6", "description": "eBGP to R3 (ASBR 65001)"},
                {"ip": "2001:db8:45::1", "remote_as": 65001, "default_originate": True, "afi": "ipv6", "description": "eBGP to R4 (ASBR 65001)"}
            ],
            "networks_ipv4": ["198.51.100.0/24"],
            "networks_ipv6": ["2001:db8:100::/64"],
            "redistribute": ["connected"]
        },
        "interfaces": [
            {
                "name": "Ethernet1",
                "cisco_name": "GigabitEthernet0/0/0/0",
                "sonic_name": "Ethernet0",
                "ip": "198.51.100.1/24",
                "ipv6": "2001:db8:100::1/64",
                "description": "Public DMZ Link to Internet Web Server"
            },
            {
                "name": "Ethernet2",
                "cisco_name": "GigabitEthernet0/0/0/1",
                "sonic_name": "Ethernet4",
                "ip": "172.16.35.2/30",
                "ipv6": "2001:db8:35::2/64",
                "description": "eBGP Link to R3 (AS 65001)"
            },
            {
                "name": "Ethernet3",
                "cisco_name": "GigabitEthernet0/0/0/2",
                "sonic_name": "Ethernet8",
                "ip": "172.16.45.2/30",
                "ipv6": "2001:db8:45::2/64",
                "description": "eBGP Link to R4 (AS 65001)"
            }
        ]
    },
    "s1.yml": {
        "hostname": "s1",
        "vendor": "arista",
        "tier": "access_switch",
        "device_type": "switch",
        "role": "Access Switch (VLANs 10, 20, 30, Trunk to R1 & S2)",
        "mgmt_ip": "172.20.20.21/24",
        "mgmt_ipv6": "2001:db8:ffff::7/64",
        "private_ip": "172.20.20.21",
        "public_ip": None,
        "vlans": [
            {"id": 10, "name": "VLAN10"},
            {"id": 20, "name": "VLAN20"},
            {"id": 30, "name": "VLAN30"}
        ],
        "ports": [
            {"name": "Ethernet1", "cisco_name": "Ethernet1/1", "sonic_name": "Ethernet0", "mode": "trunk", "allowed_vlans": "10,20", "description": "Trunk to R1 (Distribution)"},
            {"name": "Ethernet2", "cisco_name": "Ethernet1/2", "sonic_name": "Ethernet4", "mode": "trunk", "allowed_vlans": "10,20,30", "description": "Inter-Switch Trunk to S2"},
            {"name": "Ethernet3", "cisco_name": "Ethernet1/3", "sonic_name": "Ethernet8", "mode": "access", "access_vlan": 10, "description": "Access Port for Host H1 (VLAN 10)"},
            {"name": "Ethernet4", "cisco_name": "Ethernet1/4", "sonic_name": "Ethernet12", "mode": "access", "access_vlan": 20, "description": "Access Port for Host H2 (VLAN 20)"}
        ]
    },
    "s2.yml": {
        "hostname": "s2",
        "vendor": "arista",
        "tier": "access_switch",
        "device_type": "switch",
        "role": "Access Switch (VLANs 10, 20, 30, Trunk to R2 & S1)",
        "mgmt_ip": "172.20.20.22/24",
        "mgmt_ipv6": "2001:db8:ffff::8/64",
        "private_ip": "172.20.20.22",
        "public_ip": None,
        "vlans": [
            {"id": 10, "name": "VLAN10"},
            {"id": 20, "name": "VLAN20"},
            {"id": 30, "name": "VLAN30"}
        ],
        "ports": [
            {"name": "Ethernet1", "cisco_name": "Ethernet1/1", "sonic_name": "Ethernet0", "mode": "trunk", "allowed_vlans": "10,20,30", "description": "Trunk to R2 (Distribution / DHCP)"},
            {"name": "Ethernet2", "cisco_name": "Ethernet1/2", "sonic_name": "Ethernet4", "mode": "trunk", "allowed_vlans": "10,20,30", "description": "Inter-Switch Trunk to S1"},
            {"name": "Ethernet3", "cisco_name": "Ethernet1/3", "sonic_name": "Ethernet8", "mode": "access", "access_vlan": 10, "description": "Access Port for Host H3 (VLAN 10)"},
            {"name": "Ethernet4", "cisco_name": "Ethernet1/4", "sonic_name": "Ethernet12", "mode": "access", "access_vlan": 30, "description": "Access Port for Host H4 (VLAN 30 IPv6)"}
        ]
    },
    "s3.yml": {
        "hostname": "s3",
        "vendor": "arista",
        "tier": "core_switch",
        "device_type": "switch",
        "role": "Core Switch (OSPF Area 0 Backbone Bridge: R3, R1, S4, NMAS)",
        "mgmt_ip": "172.20.20.23/24",
        "mgmt_ipv6": "2001:db8:ffff::f/64",
        "private_ip": "172.20.20.23",
        "public_ip": None,
        "ports": [
            {"name": "Ethernet1", "cisco_name": "Ethernet1/1", "sonic_name": "Ethernet0", "description": "Core Link to R3 (ASBR)"},
            {"name": "Ethernet2", "cisco_name": "Ethernet1/2", "sonic_name": "Ethernet4", "description": "Core Cross-Link to S4"},
            {"name": "Ethernet3", "cisco_name": "Ethernet1/3", "sonic_name": "Ethernet8", "description": "Core Link to R1 (Distribution)"},
            {"name": "Ethernet4", "cisco_name": "Ethernet1/4", "sonic_name": "Ethernet12", "description": "Management & Monitoring Link to NMAS"}
        ]
    },
    "s4.yml": {
        "hostname": "s4",
        "vendor": "arista",
        "tier": "core_switch",
        "device_type": "switch",
        "role": "Core Switch (OSPF Area 0 Backbone Bridge: R4, R2, S3)",
        "mgmt_ip": "172.20.20.24/24",
        "mgmt_ipv6": "2001:db8:ffff::10/64",
        "private_ip": "172.20.20.24",
        "public_ip": None,
        "ports": [
            {"name": "Ethernet1", "cisco_name": "Ethernet1/1", "sonic_name": "Ethernet0", "description": "Core Link to R4 (ASBR)"},
            {"name": "Ethernet2", "cisco_name": "Ethernet1/2", "sonic_name": "Ethernet4", "description": "Core Cross-Link to S3"},
            {"name": "Ethernet3", "cisco_name": "Ethernet1/3", "sonic_name": "Ethernet8", "description": "Core Link to R2 (Distribution / DHCP)"}
        ]
    }
}

for fname, data in data_models.items():
    fpath = os.path.join(DATA_MODELS_DIR, fname)
    with open(fpath, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

print(f"Generated {len(data_models)} YAML data models in {DATA_MODELS_DIR}")

# ==============================================================================
# 2. ARISTA JINJA2 TEMPLATES (Jinja2_templates_Arista/)
# ==============================================================================

# Tier 1: Distribution Routers (r1_r2.j2)
arista_r1_r2_template = """! Arista EOS Jinja2 Template: Distribution Routers (R1-R2)
! Generated for: {{ hostname }}
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$0EpeAr86ZqgoZ07r$xiDp3lefZnL6ZYJ3h1ZfuVyLAbj6C.i9G5nCgmI62QuGlXqSjPPJSur6O77/CkgMHP/p7P1RqKBGk8neu4SMO.
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname {{ hostname }}
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
{% if dhcp_server is defined and dhcp_server %}
dhcp server
{% for pool in dhcp_server %}
{% if pool.subnet is defined %}
   subnet {{ pool.subnet }}
      range {{ pool.range_start }} {{ pool.range_end }}
      dns server {{ pool.dns_server }}
      default-gateway {{ pool.default_gateway }}
   !
{% endif %}
{% if pool.subnet_v6 is defined %}
   subnet {{ pool.subnet_v6 }}
      range {{ pool.range_start }} {{ pool.range_end }}
   !
{% endif %}
{% endfor %}
!
{% endif %}
{% for intf in interfaces %}
interface {{ intf.name }}
   no switchport
{% if intf.ip is defined %}
   ip address {{ intf.ip }}
{% endif %}
{% if intf.ipv6 is defined %}
   ipv6 enable
   ipv6 address {{ intf.ipv6 }}
{% endif %}
{% if intf.ospf_area is defined %}
   ip ospf area {{ intf.ospf_area }}
   ipv6 ospf 1 area {{ intf.ospf_area }}
{% endif %}
!
{% endfor %}
{% for sub in subinterfaces %}
interface {{ sub.parent }}.{{ sub.sub_id }}
   encapsulation dot1q vlan {{ sub.vlan_id }}
{% if sub.ip is defined %}
   ip address {{ sub.ip }}
{% endif %}
{% if sub.dhcp_ipv4 is defined and sub.dhcp_ipv4 %}
   dhcp server ipv4
{% endif %}
{% if sub.dhcp_ipv6 is defined and sub.dhcp_ipv6 %}
   dhcp server ipv6
{% endif %}
{% if sub.ipv6 is defined %}
   ipv6 enable
   ipv6 address {{ sub.ipv6 }}
{% endif %}
!
{% endfor %}
interface Management1
   ip address {{ mgmt_ip }}
   ipv6 address {{ mgmt_ipv6 }}
!
ip routing
!
ipv6 unicast-routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
{% if ospf is defined and ospf %}
router ospf {{ ospf.process_id }}
   router-id {{ ospf.router_id }}
{% for r in ospf.redistribute %}
   redistribute {{ r }}
{% endfor %}
   max-lsa 12000
!
ipv6 router ospf {{ ospf.process_id }}
   router-id {{ ospf.router_id }}
   redistribute connected
!
{% endif %}
{% if rip is defined and rip.enabled %}
router rip
{% for net in rip.networks %}
   network {{ net }}
{% endfor %}
{% for r in rip.redistribute %}
   redistribute {{ r }}
{% endfor %}
   no shutdown
!
{% endif %}
end
"""

# Tier 2: ASBR Core Routers (r3_r4.j2)
arista_r3_r4_template = """! Arista EOS Jinja2 Template: ASBR Core Routers (R3-R4)
! Generated for: {{ hostname }}
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$jF9WaU./THpbYlMP$GDdLOuLqfND5Z7q4gfIBfXIR5mucIteYDCkMNpCGTDPUiBwfY.udz5A/ZO9WjbN9SEurJI1M4mJ4LokecC36c1
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname {{ hostname }}
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
{% for intf in interfaces %}
interface {{ intf.name }}
   no switchport
{% if intf.ip is defined %}
   ip address {{ intf.ip }}
{% endif %}
{% if intf.ipv6 is defined %}
   ipv6 enable
   ipv6 address {{ intf.ipv6 }}
{% endif %}
{% if intf.ospf_area is defined %}
   ip ospf area {{ intf.ospf_area }}
   ipv6 ospf 1 area {{ intf.ospf_area }}
{% endif %}
!
{% endfor %}
interface Management1
   ip address {{ mgmt_ip }}
   ipv6 address {{ mgmt_ipv6 }}
!
ip routing
!
ipv6 unicast-routing
!
{% if bgp is defined and bgp %}
router bgp {{ bgp.local_asn }}
   router-id {{ bgp.router_id }}
{% for n in bgp.neighbors %}
   neighbor {{ n.ip }} remote-as {{ n.remote_as }}
{% endfor %}
   !
   address-family ipv4
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv4' %}
      neighbor {{ n.ip }} activate
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv4 %}
      network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
      redistribute {{ r }}
{% endfor %}
   !
   address-family ipv6
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv6' %}
      neighbor {{ n.ip }} activate
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv6 %}
      network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
      redistribute {{ r }}
{% endfor %}
!
{% endif %}
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
{% if ospf is defined and ospf %}
router ospf {{ ospf.process_id }}
   router-id {{ ospf.router_id }}
{% for r in ospf.redistribute %}
   redistribute {{ r }}
{% endfor %}
   max-lsa 12000
{% if ospf.default_originate %}
   default-information originate always
{% endif %}
!
ipv6 router ospf {{ ospf.process_id }}
   router-id {{ ospf.router_id }}
   redistribute bgp
   redistribute connected
{% if ospf.default_originate %}
   default-information originate always
{% endif %}
!
{% endif %}
end
"""

# Tier 3: PE WAN Router (r5.j2)
arista_r5_template = """! Arista EOS Jinja2 Template: Provider Edge (PE) Router (R5)
! Generated for: {{ hostname }}
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$m2wcxO0dPfHBmcpZ$LUcxn7jXyPDk6Ze8FESKKOAma1fiH6EiCuw4RnbFWe/Mg.rxebhx9nAtQev7opVMIpyB2wH9Qffq9XHKSP0PD1
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname {{ hostname }}
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
{% for intf in interfaces %}
interface {{ intf.name }}
   no switchport
{% if intf.ip is defined %}
   ip address {{ intf.ip }}
{% endif %}
{% if intf.ipv6 is defined %}
   ipv6 enable
   ipv6 address {{ intf.ipv6 }}
{% endif %}
!
{% endfor %}
interface Management1
   ip address {{ mgmt_ip }}
   ipv6 address {{ mgmt_ipv6 }}
!
ip routing
!
ipv6 unicast-routing
!
{% if bgp is defined and bgp %}
router bgp {{ bgp.local_asn }}
   router-id {{ bgp.router_id }}
{% for n in bgp.neighbors %}
   neighbor {{ n.ip }} remote-as {{ n.remote_as }}
{% endfor %}
   !
   address-family ipv4
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv4' %}
      neighbor {{ n.ip }} activate
{% if n.default_originate %}
      neighbor {{ n.ip }} default-originate
{% endif %}
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv4 %}
      network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
      redistribute {{ r }}
{% endfor %}
   !
   address-family ipv6
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv6' %}
      neighbor {{ n.ip }} activate
{% if n.default_originate %}
      neighbor {{ n.ip }} default-originate
{% endif %}
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv6 %}
      network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
      redistribute {{ r }}
{% endfor %}
!
{% endif %}
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

# Tier 4: Access Switches (s1_s2.j2)
arista_s1_s2_template = """! Arista EOS Jinja2 Template: Access Switches (S1-S2)
! Generated for: {{ hostname }}
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$DsBMK/MANkiZ0KR.$V2DWNZU0O6WAf5pA9sTXtucl77FbyCdTcrKnuMhPBWlCwmX18WbY0nBhFTn4hZi8VpTv.KRk77WTN3NqR2VzU/
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname {{ hostname }}
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
{% for v in vlans %}
vlan {{ v.id }}
   name {{ v.name }}
!
{% endfor %}
{% for p in ports %}
interface {{ p.name }}
   description {{ p.description }}
{% if p.mode == 'trunk' %}
   switchport trunk allowed vlan {{ p.allowed_vlans }}
   switchport mode trunk
{% elif p.mode == 'access' %}
   switchport access vlan {{ p.access_vlan }}
{% endif %}
!
{% endfor %}
interface Management1
   ip address {{ mgmt_ip }}
   ipv6 address {{ mgmt_ipv6 }}
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

# Tier 5: Core Switches (s3_s4.j2)
arista_s3_s4_template = """! Arista EOS Jinja2 Template: Core Backbone Switches (S3-S4)
! Generated for: {{ hostname }}
!
no aaa root
!
username admin privilege 15 role network-admin secret sha512 $6$CXEfjZB6r1hJTpgQ$ys7lfpM0Cz.knyilVCc6AUcE58EeAFLnOGx7EQO8kEsgAvBRVQF/ZeQAE7cjmogGDQluy0opY.fTp7tCY2YM/0
!
transceiver qsfp default-mode 4x10G
!
service routing protocols model multi-agent
!
hostname {{ hostname }}
!
spanning-tree mode mstp
!
system l1
   unsupported speed action error
   unsupported error-correction action error
!
{% for p in ports %}
interface {{ p.name }}
   description {{ p.description }}
!
{% endfor %}
interface Management1
   ip address {{ mgmt_ip }}
   ipv6 address {{ mgmt_ipv6 }}
!
no ip routing
!
router multicast
   ipv4
      software-forwarding kernel
   !
   ipv6
      software-forwarding kernel
!
end
"""

templates_arista = {
    "r1_r2.j2": arista_r1_r2_template,
    "r3_r4.j2": arista_r3_r4_template,
    "r5.j2": arista_r5_template,
    "s1_s2.j2": arista_s1_s2_template,
    "s3_s4.j2": arista_s3_s4_template
}

for name, content in templates_arista.items():
    with open(os.path.join(ARISTA_DIR, name), "w") as f:
        f.write(content.strip() + "\n")

print(f"Generated {len(templates_arista)} Arista Jinja2 templates in {ARISTA_DIR}")

# ==============================================================================
# 3. CISCO NX-OS JINJA2 TEMPLATES (Jinja2_templates_Cisco_NXOS/)
# ==============================================================================

cisco_nxos_s1_s2_template = """! Cisco NX-OS 9000v Template: Access Switches (S1-S2 Equivalent)
! Device: {{ hostname }} (Cisco Nexus 9000v Series)
!
feature lldp
feature interface-vlan
feature lacp
!
hostname {{ hostname }}
!
cisco-fabric default
spanning-tree mode rapid-pvst
!
{% for v in vlans %}
vlan {{ v.id }}
  name {{ v.name }}
!
{% endfor %}
{% for p in ports %}
interface {{ p.cisco_name }}
  description {{ p.description }}
{% if p.mode == 'trunk' %}
  switchport
  switchport mode trunk
  switchport trunk allowed vlan {{ p.allowed_vlans }}
  no shutdown
{% elif p.mode == 'access' %}
  switchport
  switchport mode access
  switchport access vlan {{ p.access_vlan }}
  spanning-tree port type edge
  no shutdown
{% endif %}
!
{% endfor %}
interface mgmt0
  description Out-of-band Management
  vrf member management
  ip address {{ mgmt_ip.split('/')[0] }} 255.255.255.0
  no shutdown
!
line console
line vty
!
"""

cisco_nxos_s3_s4_template = """! Cisco NX-OS 9000v Template: Core Switches (S3-S4 Equivalent)
! Device: {{ hostname }} (Cisco Nexus 9000v Series)
!
feature lldp
feature interface-vlan
feature lacp
!
hostname {{ hostname }}
!
cisco-fabric default
spanning-tree mode rapid-pvst
!
vlan 1
  name Default_Core_Transit
!
{% for p in ports %}
interface {{ p.cisco_name }}
  description {{ p.description }}
  switchport
  switchport mode trunk
  switchport trunk allowed vlan 1-4094
  no shutdown
!
{% endfor %}
interface mgmt0
  description Out-of-band Management
  vrf member management
  ip address {{ mgmt_ip.split('/')[0] }} 255.255.255.0
  no shutdown
!
"""

templates_nxos = {
    "cisco_nxos_s1_s2.j2": cisco_nxos_s1_s2_template,
    "cisco_nxos_s3_s4.j2": cisco_nxos_s3_s4_template
}

for name, content in templates_nxos.items():
    with open(os.path.join(NXOS_DIR, name), "w") as f:
        f.write(content.strip() + "\n")

print(f"Generated {len(templates_nxos)} Cisco NX-OS Jinja2 templates in {NXOS_DIR}")

# ==============================================================================
# 4. CISCO IOS-XR (XRv 9000) JINJA2 TEMPLATES (Jinja2_templates_Cisco_XRv9k/)
# ==============================================================================

cisco_xrv_r1_r2_template = """! Cisco IOS-XRv 9000 Template: Distribution Routers (R1-R2 Equivalent)
! Hostname: {{ hostname }}
!
hostname {{ hostname }}
!
{% for intf in interfaces %}
interface {{ intf.cisco_name }}
 description {{ intf.description }}
{% if intf.ip is defined %}
 ipv4 address {{ intf.ip.split('/')[0] }} 255.255.255.0
{% endif %}
{% if intf.ipv6 is defined %}
 ipv6 address {{ intf.ipv6 }}
{% endif %}
 no shutdown
!
{% endfor %}
{% for sub in subinterfaces %}
interface GigabitEthernet0/0/0/1.{{ sub.sub_id }}
 description {{ sub.description }}
 encapsulation dot1q {{ sub.vlan_id }}
{% if sub.ip is defined %}
 ipv4 address {{ sub.ip.split('/')[0] }} 255.255.255.0
{% endif %}
{% if sub.ipv6 is defined %}
 ipv6 address {{ sub.ipv6 }}
{% endif %}
 no shutdown
!
{% endfor %}
interface MgmtEth0/RP0/CPU0/0
 ipv4 address {{ mgmt_ip.split('/')[0] }} 255.255.255.0
 no shutdown
!
{% if ospf is defined and ospf %}
router ospf {{ ospf.process_id }}
 router-id {{ ospf.router_id }}
 redistribute connected
 redistribute rip
 area 0
  interface GigabitEthernet0/0/0/0
  !
 !
!
{% endif %}
{% if rip is defined and rip.enabled %}
router rip
{% for sub in subinterfaces %}
 interface GigabitEthernet0/0/0/1.{{ sub.sub_id }}
  broadcast-for-v2
 !
{% endfor %}
 redistribute ospf {{ ospf.process_id }}
!
{% endif %}
"""

cisco_xrv_r3_r4_template = """! Cisco IOS-XRv 9000 Template: ASBR Routers (R3-R4 Equivalent)
! Hostname: {{ hostname }}
!
hostname {{ hostname }}
!
{% for intf in interfaces %}
interface {{ intf.cisco_name }}
 description {{ intf.description }}
{% if intf.ip is defined %}
 ipv4 address {{ intf.ip.split('/')[0] }} 255.255.255.252
{% endif %}
{% if intf.ipv6 is defined %}
 ipv6 address {{ intf.ipv6 }}
{% endif %}
 no shutdown
!
{% endfor %}
interface MgmtEth0/RP0/CPU0/0
 ipv4 address {{ mgmt_ip.split('/')[0] }} 255.255.255.0
 no shutdown
!
route-policy PASS-ALL
  pass
end-policy
!
{% if bgp is defined and bgp %}
router bgp {{ bgp.local_asn }}
 bgp router-id {{ bgp.router_id }}
 address-family ipv4 unicast
  redistribute connected
  redistribute ospf {{ ospf.process_id }}
 !
 address-family ipv6 unicast
  redistribute connected
  redistribute ospfv3 {{ ospf.process_id }}
 !
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv4' %}
 neighbor {{ n.ip }}
  remote-as {{ n.remote_as }}
  description {{ n.description }}
  address-family ipv4 unicast
   route-policy PASS-ALL in
   route-policy PASS-ALL out
  !
 !
{% elif n.afi == 'ipv6' %}
 neighbor {{ n.ip }}
  remote-as {{ n.remote_as }}
  description {{ n.description }}
  address-family ipv6 unicast
   route-policy PASS-ALL in
   route-policy PASS-ALL out
  !
 !
{% endif %}
{% endfor %}
!
{% endif %}
{% if ospf is defined and ospf %}
router ospf {{ ospf.process_id }}
 router-id {{ ospf.router_id }}
 redistribute bgp {{ bgp.local_asn }}
 default-information originate always
 area 0
  interface GigabitEthernet0/0/0/1
  !
 !
!
{% endif %}
"""

cisco_xrv_r5_template = """! Cisco IOS-XRv 9000 Template: Provider Edge (PE) Router (R5 Equivalent)
! Hostname: {{ hostname }}
!
hostname {{ hostname }}
!
{% for intf in interfaces %}
interface {{ intf.cisco_name }}
 description {{ intf.description }}
{% if intf.ip is defined %}
 ipv4 address {{ intf.ip.split('/')[0] }} 255.255.255.0
{% endif %}
{% if intf.ipv6 is defined %}
 ipv6 address {{ intf.ipv6 }}
{% endif %}
 no shutdown
!
{% endfor %}
interface MgmtEth0/RP0/CPU0/0
 ipv4 address {{ mgmt_ip.split('/')[0] }} 255.255.255.0
 no shutdown
!
route-policy PASS-ALL
  pass
end-policy
!
{% if bgp is defined and bgp %}
router bgp {{ bgp.local_asn }}
 bgp router-id {{ bgp.router_id }}
 address-family ipv4 unicast
  network 198.51.100.0/24
  redistribute connected
 !
 address-family ipv6 unicast
  network 2001:db8:100::/64
  redistribute connected
 !
{% for n in bgp.neighbors %}
 neighbor {{ n.ip }}
  remote-as {{ n.remote_as }}
  description {{ n.description }}
{% if n.afi == 'ipv4' %}
  address-family ipv4 unicast
   default-originate
   route-policy PASS-ALL in
   route-policy PASS-ALL out
  !
{% elif n.afi == 'ipv6' %}
  address-family ipv6 unicast
   default-originate
   route-policy PASS-ALL in
   route-policy PASS-ALL out
  !
{% endif %}
 !
{% endfor %}
!
{% endif %}
"""

templates_xrv = {
    "cisco_xrv9k_r1_r2.j2": cisco_xrv_r1_r2_template,
    "cisco_xrv9k_r3_r4.j2": cisco_xrv_r3_r4_template,
    "cisco_xrv9k_r5.j2": cisco_xrv_r5_template
}

for name, content in templates_xrv.items():
    with open(os.path.join(XRV_DIR, name), "w") as f:
        f.write(content.strip() + "\n")

print(f"Generated {len(templates_xrv)} Cisco XRv 9000 Jinja2 templates in {XRV_DIR}")

# ==============================================================================
# 5. SONiC VS (sonic-vs) JINJA2 TEMPLATES (Jinja2_templates_SONiC/)
# ==============================================================================

sonic_s1_s2_template = """{
  "DEVICE_METADATA": {
    "localhost": {
      "hostname": "{{ hostname }}",
      "hwsku": "Force10-S6000",
      "platform": "x86_64-kvm_x86_64-r0",
      "mac": "00:01:02:03:04:05",
      "type": "ToRRouter"
    }
  },
  "VLAN": {
{% for v in vlans %}
    "Vlan{{ v.id }}": {
      "vlanid": "{{ v.id }}",
      "description": "{{ v.name }}"
    }{% if not loop.last %},{% endif %}
{% endfor %}
  },
  "VLAN_MEMBER": {
{% for p in ports %}
{% if p.mode == 'trunk' %}
{% for vid in p.allowed_vlans.split(',') %}
    "Vlan{{ vid }}|{{ p.sonic_name }}": {
      "tagging_mode": "tagged"
    }{% if not (loop.last and loop.parent.last) %},{% endif %}
{% endfor %}
{% elif p.mode == 'access' %}
    "Vlan{{ p.access_vlan }}|{{ p.sonic_name }}": {
      "tagging_mode": "untagged"
    }{% if not loop.last %},{% endif %}
{% endif %}
{% endfor %}
  },
  "PORT": {
{% for p in ports %}
    "{{ p.sonic_name }}": {
      "admin_status": "up",
      "alias": "{{ p.name }}",
      "description": "{{ p.description }}",
      "speed": "10000"
    }{% if not loop.last %},{% endif %}
{% endfor %}
  },
  "MGMT_INTERFACE": {
    "eth0|{{ mgmt_ip }}": {
      "gwaddr": "172.20.20.1"
    }
  }
}
"""

sonic_r1_r2_template = """! SONiC FRR Routing Configuration Template: Distribution Routers (R1-R2 Equivalent)
! Device: {{ hostname }}
!
frr version 8.4
frr defaults traditional
hostname {{ hostname }}
log syslog informational
service integrated-vtysh-config
!
{% for intf in interfaces %}
interface {{ intf.sonic_name }}
 description {{ intf.description }}
{% if intf.ip is defined %}
 ip address {{ intf.ip }}
{% endif %}
{% if intf.ipv6 is defined %}
 ipv6 address {{ intf.ipv6 }}
{% endif %}
!
{% endfor %}
{% for sub in subinterfaces %}
interface {{ sub.parent }}.{{ sub.sub_id }}
 description {{ sub.description }}
{% if sub.ip is defined %}
 ip address {{ sub.ip }}
{% endif %}
{% if sub.ipv6 is defined %}
 ipv6 address {{ sub.ipv6 }}
{% endif %}
!
{% endfor %}
{% if ospf is defined and ospf %}
router ospf
 ospf router-id {{ ospf.router_id }}
{% for r in ospf.redistribute %}
 redistribute {{ r }}
{% endfor %}
 network 10.0.0.0/24 area 0.0.0.0
!
router ospf6
 ospf6 router-id {{ ospf.router_id }}
 redistribute connected
 interface {{ interfaces[0].sonic_name }} area 0.0.0.0
!
{% endif %}
{% if rip is defined and rip.enabled %}
router rip
{% for net in rip.networks %}
 network {{ net }}
{% endfor %}
 redistribute ospf
!
{% endif %}
line vty
!
"""

sonic_r3_r4_template = """! SONiC FRR Routing Configuration Template: ASBR Routers (R3-R4 Equivalent)
! Device: {{ hostname }}
!
frr version 8.4
frr defaults traditional
hostname {{ hostname }}
log syslog informational
service integrated-vtysh-config
!
{% for intf in interfaces %}
interface {{ intf.sonic_name }}
 description {{ intf.description }}
{% if intf.ip is defined %}
 ip address {{ intf.ip }}
{% endif %}
{% if intf.ipv6 is defined %}
 ipv6 address {{ intf.ipv6 }}
{% endif %}
!
{% endfor %}
{% if bgp is defined and bgp %}
router bgp {{ bgp.local_asn }}
 bgp router-id {{ bgp.router_id }}
 no bgp default ipv4-unicast
{% for n in bgp.neighbors %}
 neighbor {{ n.ip }} remote-as {{ n.remote_as }}
 neighbor {{ n.ip }} description {{ n.description }}
{% endfor %}
 !
 address-family ipv4 unicast
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv4' %}
  neighbor {{ n.ip }} activate
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv4 %}
  network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
  redistribute {{ r }}
{% endfor %}
 exit-address-family
 !
 address-family ipv6 unicast
{% for n in bgp.neighbors %}
{% if n.afi == 'ipv6' %}
  neighbor {{ n.ip }} activate
{% endif %}
{% endfor %}
{% for net in bgp.networks_ipv6 %}
  network {{ net }}
{% endfor %}
{% for r in bgp.redistribute %}
  redistribute {{ r }}
{% endfor %}
 exit-address-family
!
{% endif %}
{% if ospf is defined and ospf %}
router ospf
 ospf router-id {{ ospf.router_id }}
 redistribute bgp
 redistribute connected
 default-information originate always
 network 10.0.0.0/24 area 0.0.0.0
!
{% endif %}
line vty
!
"""

templates_sonic = {
    "sonic_s1_s2.j2": sonic_s1_s2_template,
    "sonic_r1_r2.j2": sonic_r1_r2_template,
    "sonic_r3_r4.j2": sonic_r3_r4_template
}

for name, content in templates_sonic.items():
    with open(os.path.join(SONIC_DIR, name), "w") as f:
        f.write(content.strip() + "\n")

print(f"Generated {len(templates_sonic)} SONiC Jinja2 templates in {SONIC_DIR}")


host_models = {
    "h1.yml": {
        "hostname": "h1",
        "vendor": "linux",
        "device_type": "host",
        "role": "End Host (VLAN 10)",
        "mgmt_ip": "172.20.20.101/24",
        "private_ip": "10.10.10.101/24",
        "ipv6": "2001:db8:10::101/64",
        "default_gateway": "10.10.10.1",
        "default_gateway_v6": "2001:db8:10::1",
        "vlan_id": 10,
        "dns": "198.51.100.10"
    },
    "h2.yml": {
        "hostname": "h2",
        "vendor": "linux",
        "device_type": "host",
        "role": "End Host (VLAN 20)",
        "mgmt_ip": "172.20.20.102/24",
        "private_ip": "10.10.20.102/24",
        "ipv6": "2001:db8:20::102/64",
        "default_gateway": "10.10.20.1",
        "default_gateway_v6": "2001:db8:20::1",
        "vlan_id": 20,
        "dns": "198.51.100.10"
    },
    "h3.yml": {
        "hostname": "h3",
        "vendor": "linux",
        "device_type": "host",
        "role": "End Host (VLAN 10)",
        "mgmt_ip": "172.20.20.103/24",
        "private_ip": "10.10.10.103/24",
        "ipv6": "2001:db8:10::103/64",
        "default_gateway": "10.10.10.1",
        "default_gateway_v6": "2001:db8:10::1",
        "vlan_id": 10,
        "dns": "198.51.100.10"
    },
    "h4.yml": {
        "hostname": "h4",
        "vendor": "linux",
        "device_type": "host",
        "role": "End Host (VLAN 30 IPv6-Only)",
        "mgmt_ip": "172.20.20.104/24",
        "private_ip": "IPv6-Only",
        "ipv6": "2001:db8:30::104/64",
        "default_gateway": None,
        "default_gateway_v6": "2001:db8:30::2",
        "vlan_id": 30,
        "dns": "2001:db8:100::10"
    },
    "nmas.yml": {
        "hostname": "nmas",
        "vendor": "linux",
        "device_type": "nmas",
        "role": "Network Management & Automation Station",
        "mgmt_ip": "172.20.20.100/24",
        "private_ip": "10.0.0.100/24",
        "ipv6": "2001:db8:0::100/64",
        "backup_link_ip": "10.99.99.1/30",
        "default_gateway": "10.0.0.3",
        "default_gateway_v6": "2001:db8:0::3"
    },
    "web_server.yml": {
        "hostname": "web-server",
        "vendor": "linux",
        "device_type": "server",
        "role": "Internet Web & DNS Server",
        "mgmt_ip": "172.20.20.200/24",
        "private_ip": "198.51.100.10/24",
        "public_ip": "198.51.100.10",
        "ipv6": "2001:db8:100::10/64",
        "default_gateway": "198.51.100.1",
        "default_gateway_v6": "2001:db8:100::1"
    },
    "backup_server.yml": {
        "hostname": "backup-server",
        "vendor": "linux",
        "device_type": "backup",
        "role": "Isolated Data Lake Backup Node",
        "mgmt_ip": "172.20.20.199/24",
        "private_ip": "10.99.99.2/30",
        "isolated": True,
        "allowed_peers": ["10.99.99.1"]
    }
}

for fname, data in host_models.items():
    fpath = os.path.join(DATA_MODELS_DIR, fname)
    with open(fpath, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

print(f"Added host/server YAML data models ({len(host_models)} files). Total models now {len(data_models) + len(host_models)}")
