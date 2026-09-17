# Lab 4 & 5: Network Automation Framework & Source of Truth (NSoT)
## Objective 1 (Part 1) Implementation & Architecture Guide

---

## 1. Executive Summary & Objectives

This document details the design, architecture, and operational workflows for **Objective 1 (Part 1)** of the Network Automation Framework. Objective 1 establishes a production-grade **Network Source of Truth (NSoT)** and **Infrastructure-as-Code (IaC)** provisioning system supporting multi-vendor network fabrics.

### Key Deliverables Implemented:
1. **Version Control Management**: Complete Git-based version control tracking all device configurations, Jinja2 templates, YAML data models, and web applications.
2. **Django NSoT Web GUI**:
   - Live at `http://localhost:8000/`.
   - Modern, soothing dark-slate / teal / emerald UI theme.
   - Dynamic inventory management covering all 16 topology devices (Routers `R1`–`R5`, Switches `S1`–`S4`, End Hosts `H1`–`H4`, NMAS station, Web Server, Backup Server).
   - **Live Configuration Pull**: Real-time extraction of running configurations from Arista cEOS nodes via JSON-RPC eAPI and Linux containers.
   - **Dynamic Device Provisioning**: Interactive form supporting device types (Router, Switch, Host, NMAS, Server), vendor selection, IPAM parameters (Public, Private, Mgmt IPs), protocol parameters (OSPF, BGP ASN, Router ID, Interface IPs, VLANs), and multi-file uploads (`.cfg` running config and `.j2` templates).
   - **Golden Configuration Archive**: Database and filesystem snapshot versioning (`golden_configs/`) with automated diff comparator.
   - **Live In-Browser Template Renderer**: Interactive Jinja2 + YAML modeling studio.
3. **Bidirectional Navigation (Django <---> Grafana)**:
   - Django Web GUI includes a prominent navbar button linking to Grafana NOC (`http://localhost:3000/d/nmas-noc-master`).
   - Grafana NOC includes a navigation banner button and top-header dashboard link returning to Django NSoT (`http://localhost:8000`).
4. **Hierarchical Multi-Vendor Jinja2 Templates (Extra Credit Included)**:
   - **Tier 1 (Distribution Routers R1-R2)**: Arista EOS, Cisco XRv9k, SONiC VS
   - **Tier 2 (ASBR Core Routers R3-R4)**: Arista EOS, Cisco XRv9k, SONiC VS
   - **Tier 3 (PE WAN Router R5)**: Arista EOS, Cisco XRv9k
   - **Tier 4 (Access Switches S1-S2)**: Arista EOS, Cisco NX-OS, SONiC VS
   - **Tier 5 (Core Backbone Switches S3-S4)**: Arista EOS, Cisco NX-OS

---

## 2. System Architecture & Port Allocations

```
+---------------------------------------------------------------------------------------------------+
|                                 ROBOCONTROL NETWORK ECOSYSTEM                                     |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +-------------------------------------+         +-------------------------------------+          |
|  |     Django NSoT Web Platform        | <=====> |      Grafana NOC & Observability     |          |
|  |       `http://localhost:8000`       |  Links  |        `http://localhost:3000`      |          |
|  |  - Device Inventory & IPAM          |         |  - SNMP Health & Uptime Dashboard   |          |
|  |  - Live eAPI Running Config Pull    |         |  - Interface Bandwidth & Drops      |          |
|  |  - Multi-Vendor Jinja2 Studio       |         |  - InfluxDB 7-Day Data Lake         |          |
|  |  - Golden Configuration Snapshots   |         |  - Telegraf Collector Telemetry     |          |
|  +-------------------------------------+         +-------------------------------------+          |
|                     |                                               ^                             |
|                     | eAPI / REST / File Sync                       | SNMP Polling                |
|                     v                                               |                             |
|  +---------------------------------------------------------------------------------------------+  |
|  |                               Containerlab Network Fabric (16 Nodes)                       |  |
|  |  - Routers: R1, R2, R3, R4, R5 (cEOS 4.33.10M / Cisco XRv / SONiC)                          |  |
|  |  - Switches: S1, S2, S3, S4 (cEOS 4.33.10M / Cisco NX-OS / SONiC)                           |  |
|  |  - End Hosts: H1, H2, H3, H4                                                                |  |
|  |  - Servers: NMAS (172.20.20.100), Web (172.20.20.200), Backup (172.20.20.150)             |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Django Web GUI (NSoT Portal) Endpoints & Features

| Route / URL | View Function | Description |
| :--- | :--- | :--- |
| `http://localhost:8000/` | `dashboard_view` | Inventory dashboard with KPI counters, filter tabs (Router/Switch/Host/NMAS/Server), search, and Pull All button. |
| `http://localhost:8000/device/add/` | `add_device_view` | Dynamic device provisioning form with live routing/switching fields, template selector, and file uploads. |
| `http://localhost:8000/device/<id>/` | `device_detail_view` | Detailed node view with live configuration inspector, snapshot history, and manual eAPI pull button. |
| `http://localhost:8000/device/<id>/pull-config/` | `pull_device_config_view` | Executes Arista eAPI `["enable", "show running-config"]` or container startup script pull. |
| `http://localhost:8000/device/<id>/save-golden/` | `save_golden_config_view` | Creates timestamped snapshot in database and writes file to `golden_configs/<hostname>_<tag>.cfg`. |
| `http://localhost:8000/devices/pull-all/` | `pull_all_configs_view` | Batch eAPI extraction across all 16 registered devices. |
| `http://localhost:8000/golden-configs/` | `golden_configs_list_view` | Golden configuration repository and interactive Unified Diff comparison engine. |
| `http://localhost:8000/templates/` | `templates_list_view` | Multi-vendor Jinja2 template gallery categorized by vendor (Arista, Cisco NX-OS, Cisco XRv9k, SONiC). |
| `http://localhost:8000/templates/render/` | `render_template_view` | Live in-browser template rendering workspace with YAML input and instant code generation. |
| `http://localhost:8000/api/devices/` | `api_devices_view` | REST API endpoint returning JSON formatted device inventory. |

---

## 4. Multi-Vendor Hierarchical Jinja2 Templates (Extra Credit)

The framework organizes templates and data models according to network tier and vendor platform:

### 4.1 Arista EOS Templates (`Jinja2_templates_Arista/`)
* **`r1_r2.j2`** (Tier 1 - Distribution): R1 (RIPv2/OSPF redistribution, 802.1Q subinterfaces for VLAN 10/20) and R2 (DHCPv4/DHCPv6 server pools).
* **`r3_r4.j2`** (Tier 2 - ASBR Core): OSPF Area 0, iBGP AS 65001 mesh, eBGP AS 65001 -> AS 65002 peering, route redistribution.
* **`r3_r4.j2` / `r5.j2`** (Tier 3 - PE WAN Gateway): eBGP AS 65002 to Public Internet ISP (AS 65100), NAT, Static route failover.
* **`s1_s2.j2`** (Tier 4 - Access Switches): Access ports (VLANs 10, 20, 30, 40), 802.1Q uplink trunks, LLDP, MSTP.
* **`s3_s4.j2`** (Tier 5 - Core Backbone Switches): Multi-chassis 802.1Q trunks, MTU 9214 Jumbo frames, MSTP root priority.

### 4.2 Cisco NX-OS 9000v Templates (`Jinja2_templates_Cisco_NXOS/`)
* **`cisco_nxos_s1_s2.j2`**: NX-OS access switch config featuring `feature interface-vlan`, `feature lldp`, `spanning-tree mode rstp`, and access port assignments.
* **`cisco_nxos_s3_s4.j2`**: NX-OS core switch config featuring trunk interfaces `switchport trunk allowed vlan 10,20,30`, port-channel trunks, and jumbo MTU.

### 4.3 Cisco IOS-XRv 9000 Templates (`Jinja2_templates_Cisco_XRv9k/`)
* **`cisco_xrv9k_r1_r2.j2`**: Sub-interfaces `GigabitEthernet0/0/0/1.10`, `encapsulation dot1q 10`, OSPFv2, and route redistribution.
* **`cisco_xrv9k_r3_r4.j2`**: `router bgp 65001 address-family ipv4 unicast`, `route-policy PASS-ALL`, and BGP neighbors.
* **`cisco_xrv9k_r5.j2`**: PE WAN edge configuration with ISP eBGP peering (AS 65002 -> AS 65100).

### 4.4 SONiC VS Templates (`Jinja2_templates_SONiC/`)
* **`sonic_s1_s2.j2`**: SONiC `config_db.json` declarative schema for VLANs (`VLAN`, `VLAN_MEMBER`, `PORT`, `MGMT_INTERFACE`).
* **`sonic_r1_r2.j2`**: SONiC FRR routing engine configuration (`router ospf`, `router rip`, `interface Ethernet0`).
* **`sonic_r3_r4.j2`**: SONiC FRR BGP/OSPF ASBR configuration (`router bgp 65001`, `neighbor 172.16.50.2 remote-as 65001`).

---

## 5. Verification & Testing

To execute automated verification across all components:

```bash
python3 /home/student/Desktop/lab1/scripts/verify_lab4_5_part1.py
```

### Verification Output:
```
===========================================================================
  LAB 4 & 5 - OBJECTIVE 1 (PART 1) AUTOMATION FRAMEWORK VERIFICATION
===========================================================================
[✅ PASS] Git repository initialized and tracked
[✅ PASS] Multi-Vendor Jinja2 Templates (13 templates across 4 vendors)
[✅ PASS] Django Web GUI Endpoints (7/7 HTTP 200 OK)
[✅ PASS] Live Running Configuration Pull via eAPI
[✅ PASS] Bidirectional Navigation: Django GUI <---> Grafana NOC
[✅ PASS] Dynamic Device Provisioning & Golden Configuration Flow
===========================================================================
```

---

## 6. Operation & Access Instructions

1. **Django NSoT Web Platform**:
   - URL: `http://localhost:8000/`
   - Start Server: `python3 /home/student/Desktop/lab1/nsot_project/manage.py runserver 0.0.0.0:8000`
2. **Grafana Observability Dashboard**:
   - URL: `http://localhost:3000/d/nmas-noc-master`
   - Access Credentials: `admin` / `admin`
3. **InfluxDB Telemetry Data Lake**:
   - Host: `172.20.20.201` (Port 8086)
   - Retention Policy: 7 Days (`autogen`)
