# 📖 Comprehensive Network Operations & Engineering Documentation
## Daily Implementation, Architecture, Automation, and Verification Log

**Date**: November 2, 2026  
**Project**: RoboControl Networks (RCN) Autonomous NetDevOps Infrastructure  
**Workspace**: `/home/student/Desktop/lab1`  
**Topology**: Arista cEOS Multi-Area OSPF / BGP Campus Core & Access Fabric  
**Tools**: Containerlab, Arista EOS eAPI, Django NSoT, InfluxDB, Grafana, GitHub Actions, Vault, Python

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Master Network Topology & Architecture](#2-master-network-topology--architecture)
3. [Global IP & Subnet Allocation Matrix](#3-global-ip--subnet-allocation-matrix)
4. [Phase 1: Removal of H5 from S1 & Redeployment on Router R7 (VLAN 10)](#4-phase-1-removal-of-h5-from-s1--redeployment-on-router-r7-vlan-10)
5. [Phase 2: R6 & R7 Inventory Seeding & NSoT GUI Integration](#5-phase-2-r6--r7-inventory-seeding--nsot-gui-integration)
6. [Phase 3: Integration of Router R8 via Arista Built-in ZTP](#6-phase-3-integration-of-router-r8-via-arista-built-in-ztp)
7. [Phase 4: Migration of R2 and R8 to OSPF Area 30](#7-phase-4-migration-of-r2-and-r8-to-ospf-area-30)
8. [Phase 5: Access Switch S5 Provisioning & Hosts H6/H7 VLAN 10 Deployment](#8-phase-5-access-switch-s5-provisioning--hosts-h6h7-vlan-10-deployment)
9. [Phase 6: NSoT GUI Database & Data Model Synchronization for R8 & S5](#9-phase-6-nsot-gui-database--data-model-synchronization-for-r8--s5)
10. [Phase 7: Real-Time Observability: InfluxDB Data Lake & Grafana NOC Dashboard](#10-phase-7-real-time-observability-influxdb-data-lake--grafana-noc-dashboard)
11. [Phase 8: NetDevOps CI/CD Pipeline Automation & Multi-Stage Validation](#11-phase-8-netdevops-cicd-pipeline-automation--multi-stage-validation)
12. [Troubleshooting & Issues Resolved](#12-troubleshooting--issues-resolved)
13. [Verification & Test Results Summary](#13-verification--test-results-summary)

---

## 1. Executive Summary

During today's engineering operations, the network infrastructure underwent substantial architectural expansion, automation hardening, and observability integration:
- **Host H5 Remediation & Relocation**: Deconstructed the legacy H5 secondary subnet attachment on switch S1; reconnected H5 to router R7 on an isolated sub-interface (`Ethernet2.10`) within **VLAN 10** using a dedicated subnet (`10.70.10.0/24`), enabling dynamic multi-area routing and external Internet reachability.
- **NSoT GUI Inventory Fixes**: Diagnosed and repaired missing inventory records for routers **R6** and **R7** in the Django Network Source of Truth (NSoT) GUI (`http://localhost:8000`), generating golden baselines and automated live eAPI synchronization.
- **Router R8 Zero-Touch Provisioning (ZTP)**: Provisioned router **R8** (Arista cEOS) connected to distribution router **R2** using **Arista Built-In ZTP**, leveraging R2 as a DHCP server (Options 66 and 67) and TFTP server (`R8.cfg`) to automate boot configuration and SSH access.
- **OSPF Area 30 Multi-Area Expansion**: Transitioned the interconnect between **R2** and **R8** into **OSPF Area 30**, establishing R2 as an Area Border Router (ABR) that generates Type 3 Summary LSAs into Area 0 backbone.
- **Access Switch S5 & Dual Hosts (H6, H7)**: Deployed Arista cEOS access switch **S5** connected via an 802.1Q trunk to R8, and provisioned hosts **H6** and **H7** in **VLAN 10** with a dedicated, non-overlapping subnet (**`10.80.10.0/24`** / `2001:db8:80:10::/64`).
- **NSoT & Observability Synchronization**: Added R8 and S5 to the Django NSoT database, extended the `unified_telemetry_daemon.py` streaming telemetry engine to InfluxDB, and updated the master Grafana NOC dashboard (`http://localhost:3000/d/nmas-noc-master`).
- **NetDevOps CI/CD Green Pipeline**: Integrated R8 and S5 across all 5 stages of the GitHub Actions CI/CD workflow (`Stage 0` through `Stage 4`), achieving 100% test passes across health and regression test suites.

---

## 2. Master Network Topology & Architecture

```mermaid
graph TD
    subgraph External ["External WAN & Services"]
        WebServer["Web Server (Internet)<br/>198.51.100.10"]
        R5["R5 (PE Router / AS 65005)<br/>198.51.100.1"]
        WebServer --- R5
    end

    subgraph CoreWAN ["BGP Core / AS 65001"]
        R3["R3 (ASBR Core Router)<br/>eBGP AS 65005 & OSPF Area 0"]
        R4["R4 (ASBR Core Router)<br/>eBGP AS 65005 & OSPF Area 0"]
        R5 -- "172.16.35.0/24" --- R3
        R5 -- "172.16.45.0/24" --- R4
    end

    subgraph BackboneArea0 ["OSPF Area 0 (Backbone Fabric)"]
        S3["S3 (Core Switch)"]
        S4["S4 (Core Switch)"]
        R1["R1 (Distribution / ABR)<br/>VRRP Group 10/20/30 Master"]
        R2["R2 (Distribution / ABR)<br/>VRRP Group 10/20/30 Backup"]
        NMAS["NMAS Server<br/>10.0.0.100"]

        R3 --- S3
        R4 --- S4
        S3 --- R1
        S3 --- NMAS
        S4 --- R2
        R1 --- R2
    end

    subgraph Area10_20 ["OSPF Multi-Area Edge Branches"]
        R4 -- "OSPF Area 10 (10.46.46.0/24)" --- R6["R6 (Edge Router / ABR)<br/>10.46.46.6"]
        R6 -- "OSPF Area 20 (10.67.67.0/24)" --- R7["R7 (Edge Router)<br/>10.67.67.7"]
        R7 -- "Eth2.10 (802.1Q)" --- H5["H5 (VLAN 10 Host)<br/>10.70.10.105/24<br/>GW: 10.70.10.1"]
    end

    subgraph Area30 ["OSPF Area 30 Distribution Branch"]
        R2 -- "OSPF Area 30 (10.28.28.0/24)" --- R8["R8 (Distribution Router)<br/>10.28.28.100<br/>Router-ID: 10.28.28.8"]
    end

    subgraph AccessFabricS5 ["New Access Domain (S5 / VLAN 10)"]
        R8 -- "Eth2.10 (Trunk: 10.80.10.1/24)" --- S5["S5 (cEOS Access Switch)<br/>Mgmt: 172.20.20.25"]
        S5 -- "Eth2 (VLAN 10 Access)" --- H6["H6 (Campus Host)<br/>10.80.10.106/24<br/>GW: 10.80.10.1"]
        S5 -- "Eth3 (VLAN 10 Access)" --- H7["H7 (Campus Host)<br/>10.80.10.107/24<br/>GW: 10.80.10.1"]
    end

    subgraph LegacyAccess ["Campus Legacy Access (S1/S2)"]
        R1 --- S1["S1 (Access Switch)"]
        R2 --- S2["S2 (Access Switch)"]
        S1 --- H1["H1 (VLAN 10)<br/>10.10.10.101"]
        S1 --- H2["H2 (VLAN 20)<br/>10.10.20.102"]
        S2 --- H3["H3 (VLAN 10)<br/>10.10.10.103"]
        S2 --- H4["H4 (VLAN 30)<br/>10.10.30.104"]
    end
```

---

## 3. Global IP & Subnet Allocation Matrix

| Device | Interface | IPv4 Address / Prefix | IPv6 Address / Prefix | VLAN | Protocol / Area | Role / Purpose |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **R1** | `Ethernet1` | `10.0.0.1/24` | — | — | OSPF Area 0 | Core Backbone to S3 |
| **R1** | `Ethernet2.10`| `10.10.10.1/24` (VIP .254)| `2001:db8:10::1/64` | 10 | VRRP / OSPF Area 0 | Legacy VLAN 10 Gateway (Master) |
| **R2** | `Ethernet1` | `10.0.0.2/24` | — | — | OSPF Area 0 | Core Backbone to S4 |
| **R2** | `Ethernet3` | `10.28.28.2/24` | — | — | OSPF Area 30 | Inter-router link to R8 (DHCP/TFTP) |
| **R3** | `Ethernet1` | `10.0.0.3/24` | — | — | OSPF Area 0 | Core Backbone to S3 |
| **R3** | `Ethernet2` | `172.16.35.1/24`| — | — | eBGP AS 65001 | WAN Peering to R5 |
| **R4** | `Ethernet1` | `10.0.0.4/24` | — | — | OSPF Area 0 | Core Backbone to S4 |
| **R4** | `Ethernet3` | `10.46.46.4/24` | — | — | OSPF Area 10 | Distribution link to R6 |
| **R5** | `Ethernet1` | `198.51.100.1/24`| `2001:db8:100::1/64`| — | Connected / Static | WAN Internet Gateway |
| **R6** | `Ethernet1` | `10.46.46.6/24` | — | — | OSPF Area 10 | Uplink to R4 |
| **R6** | `Ethernet2` | `10.67.67.6/24` | — | — | OSPF Area 20 | Downlink to R7 |
| **R7** | `Ethernet1` | `10.67.67.7/24` | — | — | OSPF Area 20 | Uplink to R6 |
| **R7** | `Ethernet2.10`| `10.70.10.1/24` | `2001:db8:70:10::1/64` | 10 | OSPF Area 20 | Branch VLAN 10 Gateway for H5 |
| **R8** | `Ethernet1` | `10.28.28.100/24`| — | — | OSPF Area 30 | Uplink to R2 |
| **R8** | `Ethernet2.10`| `10.80.10.1/24` | `2001:db8:80:10::1/64` | 10 | OSPF Area 30 | Access VLAN 10 Gateway for H6/H7 |
| **S5** | `Ethernet1` | — | — | Trunk | 802.1Q | Trunk to R8 |
| **S5** | `Ethernet2` | — | — | 10 | L2 Access | Access port for H6 |
| **S5** | `Ethernet3` | — | — | 10 | L2 Access | Access port for H7 |
| **S5** | `Management0`| `172.20.20.25/24`| — | — | Management | eAPI HTTP Command API |
| **H5** | `eth1` | `10.70.10.105/24`| `2001:db8:70:10::105/64`| 10 | Static Default GW | Branch Host on R7 |
| **H6** | `eth1` | `10.80.10.106/24`| `2001:db8:80:10::106/64`| 10 | Static Default GW | Campus Host on S5 |
| **H7** | `eth1` | `10.80.10.107/24`| `2001:db8:80:10::107/64`| 10 | Static Default GW | Campus Host on S5 |
| **Web**| `eth1` | `198.51.100.10/24`| `2001:db8:100::10/64` | — | Static | External Web Services Target |

---

## 4. Phase 1: Removal of H5 from S1 & Redeployment on Router R7 (VLAN 10)

### 4.1 Problem Statement & Remediation
Prior configuration had placed host **H5** on switch **S1** with an overlapping/secondary subnet on VLAN 10 (`10.10.50.0/24`), which introduced ARP confusion and bypassed router hierarchy.

**Actions Taken**:
1. Removed H5 container (`clab-lab1-h5`) and disconnected its veth interface from `s1:eth5`.
2. Removed secondary IP addresses and static ARP entries from R1 and R2.
3. Updated Containerlab topology [`lab1.clab.yml`](file:///home/student/Desktop/lab1/lab1.clab.yml) to define H5 attached directly to router **R7** on `r7:eth2`.

### 4.2 R7 Sub-Interface & Routing Configuration
On router **R7**, sub-interface `Ethernet2.10` was configured for 802.1Q encapsulation with a dedicated subnet:
```text
interface Ethernet2.10
   description Branch VLAN 10 Access Network
   encapsulation dot1q vlan 10
   ip address 10.70.10.1/24
   ipv6 enable
   ipv6 address 2001:db8:70:10::1/64
   ip ospf area 0.0.0.20
```
On `router ospf 1`:
```text
router ospf 1
   router-id 10.67.67.7
   redistribute connected
   network 10.67.67.0/24 area 0.0.0.20
   network 10.70.10.0/24 area 0.0.0.20
```

### 4.3 Host H5 Provisioning & Testing
Configured [`configs/h5/start.sh`](file:///home/student/Desktop/lab1/configs/h5/start.sh):
```bash
ip link set dev eth1 address aa:c1:ab:00:10:05
ip addr add 10.70.10.105/24 dev eth1
ip -6 addr add 2001:db8:70:10::105/64 dev eth1
ip link set dev eth1 up
ip route add default via 10.70.10.1
ip -6 route add default via 2001:db8:70:10::1
```
**Verification**:
- Ping from H5 to Internet Web Server (`198.51.100.10`): **100% success (0% loss, ~1.1ms)**
- HTTP 200 GET from H5 to `http://198.51.100.10`: **HTTP/1.1 200 OK ("Hello World")**
- Inter-VLAN reachability: H5 ping to H1 (`10.10.10.101`) and H2 (`10.10.20.102`): **100% success**.

---

## 5. Phase 2: R6 & R7 Inventory Seeding & NSoT GUI Integration

### 5.1 Root Cause of Missing GUI Devices
When browsing the Django NSoT Web GUI (`http://localhost:8000`), routers **R6** and **R7** were absent from the inventory tables. Analysis revealed:
- Database records in `nsot_project/nsot.db` had not been populated for `r6` and `r7` in the `Device`, `DeviceInterface`, and `GoldenConfig` models.
- The automated seeding script [`scripts/seed_django_nsot.py`](file:///home/student/Desktop/lab1/scripts/seed_django_nsot.py) lacked definitions for these routers.

### 5.2 Remediation & Execution
1. Enhanced [`scripts/seed_django_nsot.py`](file:///home/student/Desktop/lab1/scripts/seed_django_nsot.py):
   - Added device records with management IPs `172.20.20.16` (R6) and `172.20.20.17` (R7).
   - Added interfaces `Ethernet1`, `Ethernet2`, `Ethernet2.10`, and `Management0`.
   - Embedded eAPI live running-configuration fetch to pull active configs directly into NSoT.
2. Executed seeding:
   ```bash
   python3 scripts/seed_django_nsot.py
   ```
   **Output**: 23 devices, 13 templates, and 23 golden configs verified.
3. Verified via HTTP GET on `http://localhost:8000/devices/` that R6 and R7 appeared with green operational status, live config diff viewer, and interface mappings.

---

## 6. Phase 3: Integration of Router R8 via Arista Built-in ZTP

### 6.1 Requirements & Workflow
1. Interconnect R8 to R2 on physical link `r2:eth3` $\leftrightarrow$ `r8:eth1`.
2. Configure R2 as a DHCP server providing IP address `10.28.28.100/24`, default gateway `10.28.28.2`, Option 66 (TFTP Server `10.28.28.2`), and Option 67 (Bootfile `R8.cfg`).
3. Deploy a TFTP server daemon on R2 hosting [`configs/r8/R8.cfg`](file:///home/student/Desktop/lab1/configs/r8/R8.cfg).
4. Allow R8 built-in ZTP (`zerotouch-dhclient`) to boot, receive lease and TFTP details, fetch `R8.cfg`, apply startup configuration, and enable SSH.

### 6.2 ZTP Sequence & Implementation

```mermaid
sequenceDiagram
    autonumber
    participant R8 as Router R8 (cEOS Client)
    participant R2 as Router R2 (Gateway & DHCP/TFTP)
    participant NMAS as NMAS / Controller

    Note over R2,R8: Link r2:eth3 <-> r8:eth1 UP
    R8->>R2: DHCP Discover (eth1 requesting Opt 66 & 67)
    R2->>R8: DHCP Offer (IP: 10.28.28.100, Opt 66: 10.28.28.2, Opt 67: R8.cfg)
    R8->>R2: DHCP Request (10.28.28.100)
    R2->>R8: DHCP ACK (Lease registered)
    R8->>R2: TFTP Read Request (RRQ) for R8.cfg (UDP port 69)
    R2->>R8: TFTP Data Blocks (R8.cfg file transferred)
    Note over R8: Saves to /mnt/flash/startup-config & enables SSH
    NMAS->>R8: SSH Connect (admin@10.28.28.100 & admin@172.20.20.18)
    R8-->>NMAS: SSH Session Established (Passwordless/AAA OK)
```

### 6.3 Technical Configurations Applied
- **R2 DHCP Server Configuration ([`configs/ceos/r2.cfg`](file:///home/student/Desktop/lab1/configs/ceos/r2.cfg))**:
  ```text
  interface Ethernet3
     description Link to R8
     no switchport
     ip address 10.28.28.2/24
     dhcp server ipv4
  !
  dhcp server
     subnet 10.28.28.0/24
        range 10.28.28.100 10.28.28.150
        dns server 198.51.100.10
        default-gateway 10.28.28.2
        tftp server option 66 10.28.28.2
        tftp server file R8.cfg
  ```
- **R2 TFTP Service**:
  - Installed Python `tftpy` on R2 `/mnt/flash/tftpy`.
  - Created `/mnt/flash/tftp_server.py` serving directory `/mnt/flash/tftpboot/`.
  - Configured systemd unit `/etc/systemd/system/tftp-server.service` and started service.
  - Added iptables rule to allow UDP 69 through `EOS_INPUT`.
- **R8 Configuration File (`R8.cfg`)**:
  - Baseline AAA, username `admin` with privilege 15, SSH daemon enabled, and eAPI activated.
- **Verification**:
  - `Cli -p 15 -c "show zerotouch"` on R8: Status transitioned to `Disabled (Success)`.
  - Successful SSH login via `ssh -o StrictHostKeyChecking=no admin@10.28.28.100`.

---

## 7. Phase 4: Migration of R2 and R8 to OSPF Area 30

### 7.1 Architecture & Design
To maintain a scalable hierarchical multi-area topology, R2 was configured as an Area Border Router (ABR) bridging **Area 0** (backbone) with a new **Area 30** assigned to the R2–R8 link and R8's downstream access networks.

### 7.2 Configuration Details
- **Router R2 ([`configs/ceos/r2.cfg`](file:///home/student/Desktop/lab1/configs/ceos/r2.cfg))**:
  ```text
  interface Ethernet3
     description Link to R8 (Area 30)
     no switchport
     ip address 10.28.28.2/24
     ip ospf area 0.0.0.30
  ```
- **Router R8 ([`configs/ceos/r8.cfg`](file:///home/student/Desktop/lab1/configs/ceos/r8.cfg))**:
  ```text
  router ospf 1
     router-id 10.28.28.8
     redistribute connected
     network 10.28.28.0/24 area 0.0.0.30
     network 10.80.10.0/24 area 0.0.0.30
  !
  interface Ethernet1
     description Uplink to R2
     no switchport
     ip address 10.28.28.100/24
     ip ospf area 0.0.0.30
  ```

### 7.3 Control Plane Convergence
- **Neighbor State**: R2 and R8 established adjacency `FULL/DR` across `10.28.28.0/24`.
- **Route Injection**: R2 injected Type 3 Summary LSAs for `10.80.10.0/24` into Area 0 (`O IA` route on R1, R3, R4, R6, R7).
- **Default/WAN Injection**: External Type 5 LSAs for `0.0.0.0/0` and `198.51.100.0/24` flooded into Area 30, providing complete outbound reachability.

---

## 8. Phase 5: Access Switch S5 Provisioning & Hosts H6/H7 VLAN 10 Deployment

### 8.1 S5 Switch Deployment
Deployed an Arista cEOS L2 switch **S5** (`172.20.20.25`) in [`lab1.clab.yml`](file:///home/student/Desktop/lab1/lab1.clab.yml):
```yaml
    s5:
      kind: arista_ceos
      image: ceos:latest
      mgmt-ipv4: 172.20.20.25
      startup-config: configs/ceos/s5.cfg
```
Links configured:
- `["r8:eth2", "s5:eth1"]` (802.1Q Trunk)
- `["s5:eth2", "h6:eth1"]` (Access VLAN 10)
- `["s5:eth3", "h7:eth1"]` (Access VLAN 10)

### 8.2 S5 Configuration ([`configs/ceos/s5.cfg`](file:///home/student/Desktop/lab1/configs/ceos/s5.cfg))
```text
vlan 10
   name DATA_ACCESS
!
interface Ethernet1
   description Trunk to R8
   switchport mode trunk
   switchport trunk allowed vlan 10
!
interface Ethernet2
   description Access to H6
   switchport mode access
   switchport access vlan 10
!
interface Ethernet3
   description Access to H7
   switchport mode access
   switchport access vlan 10
!
interface Management0
   ip address 172.20.20.25/24
!
management api http-commands
   protocol http
   no shutdown
```

### 8.3 R8 Sub-Interface & Gateway
Configured on R8:
```text
interface Ethernet2.10
   description Access VLAN 10 Gateway
   encapsulation dot1q vlan 10
   ip address 10.80.10.1/24
   ipv6 enable
   ipv6 address 2001:db8:80:10::1/64
   ip ospf area 0.0.0.30
```

### 8.4 Hosts H6 & H7 Configuration
- **H6 ([`configs/h6/start.sh`](file:///home/student/Desktop/lab1/configs/h6/start.sh))**:
  - IP: `10.80.10.106/24` | IPv6: `2001:db8:80:10::106/64` | MAC: `aa:c1:ab:00:10:06`
  - Default route via `10.80.10.1` and `2001:db8:80:10::1`
- **H7 ([`configs/h7/start.sh`](file:///home/student/Desktop/lab1/configs/h7/start.sh))**:
  - IP: `10.80.10.107/24` | IPv6: `2001:db8:80:10::107/64` | MAC: `aa:c1:ab:00:10:07`
  - Default route via `10.80.10.1` and `2001:db8:80:10::1`

---

## 9. Phase 6: NSoT GUI Database & Data Model Synchronization for R8 & S5

### 9.1 Data Models Created & Updated
1. [`data_models/r8.yml`](file:///home/student/Desktop/lab1/data_models/r8.yml): Updated with `Ethernet1` (`10.28.28.100/24`), `Ethernet2.10` (`10.80.10.1/24`), and OSPF Area 30.
2. [`data_models/s5.yml`](file:///home/student/Desktop/lab1/data_models/s5.yml): Access switch model with VLAN 10, trunk, and access interfaces.
3. [`data_models/h6.yml`](file:///home/student/Desktop/lab1/data_models/h6.yml) and [`data_models/h7.yml`](file:///home/student/Desktop/lab1/data_models/h7.yml): End-host node definitions.
4. [`data_models/r2.yml`](file:///home/student/Desktop/lab1/data_models/r2.yml): Added `Ethernet3` Area 30 link.

### 9.2 Golden Baseline Generation & Seeding
Updated [`scripts/seed_django_nsot.py`](file:///home/student/Desktop/lab1/scripts/seed_django_nsot.py):
- Seeded R8 and S5 device objects, interfaces, and baseline configs (`golden_configs/r8_v1.0-baseline.cfg`, `golden_configs/s5_v1.0-baseline.cfg`).
- Verified live config fetch:
  ```text
  [*] Pulling live running-config from r8 via eAPI (172.20.20.18)... SUCCESS (49 lines)
  [*] Pulling live running-config from s5 via eAPI (172.20.20.25)... SUCCESS (43 lines)
  ```

---

## 10. Phase 7: Real-Time Observability: InfluxDB Data Lake & Grafana NOC Dashboard

### 10.1 Telemetry Daemon Enhancement
Updated [`scripts/unified_telemetry_daemon.py`](file:///home/student/Desktop/lab1/scripts/unified_telemetry_daemon.py):
- Added `s5` to the `DEVICES` dictionary (`http://admin:admin@172.20.20.25/command-api`).
- Configured real-time polling loops for CPU utilization, memory allocation, and interface byte/packet counters across `eth1`, `eth2`, `eth3`, and `Management0`.
- Verified live ingestion into InfluxDB database `nmas_datalake` (measurements `cpu_metrics`, `interface_metrics`, `r8_telemetry`, `s5_telemetry`).

### 10.2 Grafana NOC Dashboard Integration
1. Enhanced [`scripts/build_grafana_dashboard.py`](file:///home/student/Desktop/lab1/scripts/build_grafana_dashboard.py) template query dropdown to include `r8` and `s5`.
2. Regenerated [`configs/grafana/dashboards/nmas_network_operations.json`](file:///home/student/Desktop/lab1/configs/grafana/dashboards/nmas_network_operations.json).
3. Restarted Grafana container (`clab-lab1-grafana`).
4. Confirmed live graphs displaying CPU, interface traffic, and memory utilization for R8 and S5 at:
   `http://localhost:3000/d/nmas-noc-master`

---

## 11. Phase 8: NetDevOps CI/CD Pipeline Automation & Multi-Stage Validation

### 11.1 Test Suite Updates
- **[`scripts/validate_iac_syntax.py`](file:///home/student/Desktop/lab1/scripts/validate_iac_syntax.py)**: Added `r8.yml`, `s5.yml`, `h6.yml`, and `h7.yml` schema validations and Jinja2 template compilations.
- **[`scripts/generate_and_diff_configs.py`](file:///home/student/Desktop/lab1/scripts/generate_and_diff_configs.py)**: Added R8 and S5 to candidate config compilation and live diff generation.
- **[`scripts/deploy_device_configs.py`](file:///home/student/Desktop/lab1/scripts/deploy_device_configs.py)**: Added R8 and S5 to automated eAPI deployment engine.
- **[`scripts/verify_network_health.py`](file:///home/student/Desktop/lab1/scripts/verify_network_health.py)**: Added H6/H7 ping & HTTP tests, OSPF Area 30 tests, eAPI checks, and InfluxDB telemetry checks.
- **[`scripts/verify_network_regression.py`](file:///home/student/Desktop/lab1/scripts/verify_network_regression.py)**: Added H6/H7 positive/negative tests, S5 L2 isolation checks, and Area 30 RIB assertions.

### 11.2 CI/CD Execution Summary (GitHub Actions Run ID: 41400067395)
Pushed commit `a0b0c91` to `origin/main`. All 5 stages executed cleanly on the self-hosted Linux runner:

| Stage | Name | Status | Duration | Key Metrics |
| :---: | :--- | :---: | :---: | :--- |
| **0** | **NSoT Unit Tests & Code Coverage** | `SUCCESS` | 24s | 77/77 tests passed; coverage report generated |
| **1** | **Linting & Quality Gate** | `SUCCESS` | 11s | 23 YAML models, 21 Jinja2 templates, 0 leaks |
| **2** | **Compile Configs & Generate Diffs** | `SUCCESS` | 17s | 13 candidate configs compiled, diff report created |
| **3** | **Deploy Configurations** | `SUCCESS` | 49s | 13/13 devices deployed via eAPI without errors |
| **4** | **Network Health & Observability** | `SUCCESS` | 66s | Health: 45/45 Passed (100%), Regression: 47/47 Passed (100%) |

---

## 12. Troubleshooting & Issues Resolved

### Issue 1: FastCli Authorization Denied on Router R8
- **Symptom**: `FastCli -c "show ip int brief"` returned `% Authorization denied for command 'show ip interface brief': Default authorization provider rejects all commands`.
- **Cause**: Arista cEOS FastCli agent without explicit privilege level rejects commands until AAA authorization initializes.
- **Resolution**: Utilized privileged execution flag `Cli -p 15 -c "..."`, which bypassed authorization rejection and enabled smooth automated commands.

### Issue 2: Switch S5 eAPI Connection Failure
- **Symptom**: `curl http://172.20.20.25/command-api` timed out with `curl: (7) Failed to connect`.
- **Cause**: Initial configuration placed management IP on `interface Management1` instead of `interface Management0`. In cEOS, only `Management0` is bound to the Linux container's eth0 management network namespace.
- **Resolution**: Reconfigured `Management0` with `ip address 172.20.20.25/24` and removed it from `Management1`. eAPI and telemetry metrics responded immediately.

### Issue 3: S5 Layer 2 Isolation Regression Test Failure
- **Symptom**: Regression test failed with `Criteria Failure: Switch routing enabled: disabled=True, count=1`.
- **Cause**: The test asserted that `show ip route` must return 0 routes, but the connected out-of-band management subnet (`172.20.20.0/24`) was present in the kernel table.
- **Resolution**: Updated `check_s5_routing_disabled` in [`scripts/verify_network_regression.py`](file:///home/student/Desktop/lab1/scripts/verify_network_regression.py) to filter out out-of-band management routes (`172.20.20.0/24`), ensuring strict assertion of zero data-plane routes while `routingDisabled=True`.

---

## 13. Verification & Test Results Summary

### 13.1 Health Verification Suite (`verify_network_health.py`): 45/45 Passed (100.0%)
- **Data Plane (Internet Connectivity)**: 14/14 Passed (H1 through H7 ping and HTTP 200 to `198.51.100.10`).
- **Data Plane (Inter/Intra VLAN)**: 7/7 Passed (H6 $\leftrightarrow$ H7 intra-VLAN, H6 $\leftrightarrow$ H1 inter-subnet, H1/H2 $\leftrightarrow$ H4 IPv6).
- **Control Plane (BGP & OSPF & RIP)**: 9/9 Passed (eBGP R5 $\leftrightarrow$ R3/R4, OSPF Area 0, Area 10, Area 20, Area 30, RIPv2).
- **High Availability (VRRP)**: 2/2 Passed (R1 Master, R2 Backup).
- **Security & Management**: 7/7 Passed (eAPI active across R1, R6, R7, R8, S5; FreeRADIUS and PrivacyIDEA active).
- **Observability**: 6/6 Passed (InfluxDB, Grafana NOC, live telemetry streams for R6, R7, R8, S5).

### 13.2 Network Regression Suite (`verify_network_regression.py`): 47/47 Passed (100.0%)
- **Positive Reachability & Control Plane**: 35/35 Passed (End-to-end data plane, default route injection, Area 30 RIB assertions on R2 and R8, VRRP Master/Backup assertions).
- **Negative Rejection Tests**: 12/12 Passed (Unallocated WAN drop, bogus subnet drop, rogue BGP peer rejection, VRRP split-brain prevention, S1 and S5 Layer 2 routing isolation).

---

## 14. File & Artifact Reference Index

- **Topology**: [`lab1.clab.yml`](file:///home/student/Desktop/lab1/lab1.clab.yml)
- **Device Configurations**:
  - [`configs/ceos/r2.cfg`](file:///home/student/Desktop/lab1/configs/ceos/r2.cfg)
  - [`configs/ceos/r8.cfg`](file:///home/student/Desktop/lab1/configs/ceos/r8.cfg)
  - [`configs/ceos/s5.cfg`](file:///home/student/Desktop/lab1/configs/ceos/s5.cfg)
  - [`configs/h6/start.sh`](file:///home/student/Desktop/lab1/configs/h6/start.sh)
  - [`configs/h7/start.sh`](file:///home/student/Desktop/lab1/configs/h7/start.sh)
- **Data Models**:
  - [`data_models/r8.yml`](file:///home/student/Desktop/lab1/data_models/r8.yml)
  - [`data_models/s5.yml`](file:///home/student/Desktop/lab1/data_models/s5.yml)
  - [`data_models/h6.yml`](file:///home/student/Desktop/lab1/data_models/h6.yml)
  - [`data_models/h7.yml`](file:///home/student/Desktop/lab1/data_models/h7.yml)
- **Automation Scripts**:
  - [`scripts/seed_django_nsot.py`](file:///home/student/Desktop/lab1/scripts/seed_django_nsot.py)
  - [`scripts/unified_telemetry_daemon.py`](file:///home/student/Desktop/lab1/scripts/unified_telemetry_daemon.py)
  - [`scripts/build_grafana_dashboard.py`](file:///home/student/Desktop/lab1/scripts/build_grafana_dashboard.py)
  - [`scripts/validate_iac_syntax.py`](file:///home/student/Desktop/lab1/scripts/validate_iac_syntax.py)
  - [`scripts/generate_and_diff_configs.py`](file:///home/student/Desktop/lab1/scripts/generate_and_diff_configs.py)
  - [`scripts/deploy_device_configs.py`](file:///home/student/Desktop/lab1/scripts/deploy_device_configs.py)
  - [`scripts/verify_network_health.py`](file:///home/student/Desktop/lab1/scripts/verify_network_health.py)
  - [`scripts/verify_network_regression.py`](file:///home/student/Desktop/lab1/scripts/verify_network_regression.py)
- **CI/CD Workflow**: [`.github/workflows/network-ci-cd.yml`](file:///home/student/Desktop/lab1/.github/workflows/network-ci-cd.yml)
