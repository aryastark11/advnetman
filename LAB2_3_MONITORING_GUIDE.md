# Labs 2 & 3: Comprehensive Monitoring, Streaming Telemetry, Data Lake & Isolated Backup Guide

## 1. Executive Summary & Lab Objectives

This document provides complete implementation details, operational architectures, configuration commands, and verification procedures for **Labs 2 & 3 (Network Monitoring, Telemetry, Data Lake, Isolated Backup & Retention)** on the Arista cEOS container-based network.

```
+===================================================================================================+
|                                    LAB OBJECTIVES OVERVIEW                                        |
+===================================================================================================+
| Objective 1: SNMP Monitoring & Syslog Logging                                                     |
|   * Configure NMAS as NMS (Network Management System) and central Syslog collector.               |
|   * Enable SNMP on all 9 Arista cEOS devices (r1-r5, s1-s4).                                      |
|   * Poll key OIDs (sysName, sysUpTime, CPU Utilization, System Description).                      |
|   * Capture and log SNMP link-state change traps on UDP port 162.                                 |
|   * Ingest and index Syslog alerts (RFC 5424/3164) across all severity levels on UDP port 514.   |
|                                                                                                   |
| Objective 2: Streaming Telemetry & NetConf/eAPI Ingestion                                         |
|   * Enable eAPI HTTP commands and gNMI gRPC streaming telemetry across all devices.               |
|   * Ingest operational state, BGP neighbors, OSPF adjacencies, and interface counters.           |
|                                                                                                   |
| Objective 3: NMAS Data Lake, Isolated Backup Node & 7-Day Retention Policy                       |
|   * Construct unified Data Lake on NMAS (`/opt/nmas/datalake` & SQLite `datalake.db`).            |
|   * Expose REST API (`http://10.0.0.100:8080/api/datalake/`) for real-time querying.             |
|   * Deploy dedicated isolated backup container (`backup-server`) on private link `10.99.99.0/30`.|
|   * Enforce iptables firewall on backup node so it is accessible ONLY by NMAS.                    |
|   * Synchronize Data Lake partitions in real-time from NMAS to `/opt/backup/datalake/`.          |
|   * Implement automated 7-day retention daemon purging data/files older than 7 days on both nodes.|
+===================================================================================================+
```

---

## 2. Network Topology & Monitoring Architecture

```mermaid
flowchart TD
    subgraph Isolated_Backup_Domain ["Isolated Backup Domain (Strictly NMAS-Only)"]
        BACKUP["Backup Server<br>10.99.99.2/30 (eth1)<br>/opt/backup/datalake/"]
    end

    subgraph NMAS_Core ["Network Management & Automation Station"]
        NMAS["NMAS Station<br>10.0.0.100/24 (eth1) | 10.99.99.1/30 (eth2)<br>SNMP (161/162) | Syslog (514) | eAPI/gNMI<br>Data Lake: /opt/nmas/datalake/"]
    end

    subgraph Core_Backbone ["OSPF Area 0 Core Backbone (10.0.0.0/24)"]
        S3["Switch S3<br>(cEOS)"] --- S4["Switch S4<br>(cEOS)"]
        R3["Router R3<br>(cEOS ASBR)"] --- S3
        R4["Router R4<br>(cEOS ASBR)"] --- S4
        R1["Router R1<br>(cEOS Dist)"] --- S3
        R2["Router R2<br>(cEOS Dist)"] --- S4
        NMAS --- S3
    end

    subgraph WAN_Domain ["eBGP WAN Domain (AS 65005 <-> AS 65001)"]
        R5["Router R5 (PE cEOS)"] ---|172.16.35.0/30| R3
        R5 ---|172.16.45.0/30| R4
        WEB["Internet Web Server<br>198.51.100.10/24"] --- R5
    end

    subgraph Access_Domain ["Access & Host Domain (VLANs 10, 20, 30)"]
        R1 ---|Trunk 10,20| S1["Switch S1 (cEOS)"]
        R2 ---|Trunk 10,20,30| S2["Switch S2 (cEOS)"]
        S1 ---|Inter-Switch Trunk| S2
        S1 --- H1["Host H1 (VLAN 10)"]
        S1 --- H2["Host H2 (VLAN 20)"]
        S2 --- H3["Host H3 (VLAN 10)"]
        S2 --- H4["Host H4 (VLAN 30)"]
    end

    NMAS ===|Dedicated Point-to-Point<br>10.99.99.0/30 (TCP 9999)| BACKUP

    classDef nmasStyle fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef backupStyle fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fff;
    classDef routerStyle fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef switchStyle fill:#115e59,stroke:#14b8a6,stroke-width:2px,color:#fff;

    class NMAS nmasStyle;
    class BACKUP backupStyle;
    class R1,R2,R3,R4,R5 routerStyle;
    class S1,S2,S3,S4 switchStyle;
```

---

## 3. Objective 1: SNMP Monitoring & Syslog Logging Implementation

### 3.1 Device-Side Arista cEOS SNMP & Syslog Configuration

All 9 Arista cEOS nodes (`r1`–`r5`, `s1`–`s4`) are configured with standardized SNMP communities, trap receivers, and syslog forwarders:

```text
! Enable SNMP Agent and Communities
snmp-server community public ro
snmp-server community private rw
snmp-server contact "Network-Ops-Team <ops@lab1.local>"
snmp-server location "Lab Rack DC-1"

! Configure SNMP Trap Generation and Destinations (NMAS)
snmp-server enable traps
snmp-server host 10.0.0.100 traps version 2c public
snmp-server host 172.20.20.100 traps version 2c public

! Configure Centralized Syslog Forwarding (NMAS)
logging host 10.0.0.100
logging host 172.20.20.100
logging trap debugging
logging format timestamp traditional
```

### 3.2 Monitored OID Reference Matrix

The NMAS Collector actively polls the following standard SNMPv2-SMI and Host-Resources MIB OIDs every 15 seconds across all nodes:

| Metric | Object Identifier (OID) | MIB Module | Value Type / Units | Description |
| :--- | :--- | :--- | :--- | :--- |
| **System Name** | `1.3.6.1.2.1.1.5.0` | SNMPv2-MIB | String | Hostname of the network device |
| **System Uptime** | `1.3.6.1.2.1.1.3.0` | SNMPv2-MIB | TimeTicks (1/100s) | Time elapsed since last daemon/system reboot |
| **CPU Utilization** | `1.3.6.1.2.1.25.3.3.1.2.1` | HOST-RESOURCES-MIB | Integer (0-100%) | Instantaneous processor load percentage |
| **System Description**| `1.3.6.1.2.1.1.1.0` | SNMPv2-MIB | String | OS Version (`Arista Networks EOS Version 4.33.10M`) |
| **Interface Status** | `1.3.6.1.2.1.2.2.1.8.<ifIndex>` | IF-MIB | Integer (1=up, 2=down) | Operational status of network interfaces |
| **Interface InOctets**| `1.3.6.1.2.1.2.2.1.10.<ifIndex>`| IF-MIB | Counter32 (Bytes) | Total ingress byte throughput |
| **Interface OutOctets**| `1.3.6.1.2.1.2.2.1.16.<ifIndex>`| IF-MIB | Counter32 (Bytes) | Total egress byte throughput |

### 3.3 SNMP Trap Handling & Link-State Event Ingestion

* **UDP Port 162 Listener**: NMAS runs an asynchronous trap listener bound to `0.0.0.0:162`.
* **Link State Triggers**: Whenever an interface state toggles (e.g. `linkDown` / `linkUp`), cEOS devices emit traps containing the interface index and reason code.
* **Storage**: Ingested traps are indexed in SQLite table `snmp_traps` and saved as JSON logs under `/opt/nmas/datalake/traps/YYYY-MM-DD/`.

### 3.4 Syslog Event Aggregation & Severity Classification

NMAS listens on `0.0.0.0:514` (UDP) and parses messages into structured RFC-standard severities:

```
Facility / Severity Codes:
0 = Emergency | 1 = Alert | 2 = Critical | 3 = Error | 4 = Warning | 5 = Notice | 6 = Informational | 7 = Debug
```

* **Critical Alerts Filter**: Messages matching severities `0` (Emergency), `1` (Alert), `2` (Critical), or keywords `LINK-DOWN`, `BGP-NEIGHBOR-DOWN`, `CRITICAL`, `ERROR` are automatically flagged with `is_critical = 1` for prioritization.

---

## 4. Objective 2: gRPC Streaming Telemetry & NetConf/eAPI Implementation

### 4.1 Device-Side Arista cEOS gRPC & eAPI Configuration

All 9 Arista cEOS routers and switches have gRPC/gNMI and eAPI active:

```text
! Enable Multi-Agent Routing Model (Required for Telemetry & Routing Coordination)
service routing protocols model multi-agent

! Enable eAPI (HTTP / JSON-RPC Command Interface)
management api http-commands
   no shutdown
   protocol http port 80

! Enable gRPC / gNMI Streaming Telemetry Server (Port 6030)
management api gnmi
   transport grpc default
      no shutdown
```

### 4.2 OpenConfig YANG Paths & Streaming Telemetry Sensors

The NMAS Collector streams and queries real-time OpenConfig telemetry over **gRPC (Port 6030)** using `gnmic` (OpenConfig gNMI Client):

| Telemetry Sensor / Feature | OpenConfig YANG Path | Encoding | Description |
| :--- | :--- | :--- | :--- |
| **System State & Hostname** | `/system/state` | `JSON_IETF` | System hostname, software version, boot-time, current-datetime |
| **Interface State & Counters** | `/interfaces/interface[name=Ethernet1]/state` | `JSON_IETF` | Oper-status, admin-status, in-octets, out-octets, in-pkts, out-pkts |
| **BGP Neighbor Sessions** | `/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors` | `JSON_IETF` | Session-state (`ESTABLISHED`), peer AS, prefixes installed/sent |
| **LLDP Topology Discovery** | `/lldp/state` | `JSON_IETF` | Peer chassis-id, port-id, system-name |

### 4.3 Practical CLI Commands for gRPC Verification

From NMAS or the management host:

```bash
# 1. Query gNMI capabilities and supported YANG models
gnmic -a 172.20.20.11:6030 -u admin -p admin --insecure capabilities

# 2. Query System Hostname via gRPC
gnmic -a 172.20.20.11:6030 -u admin -p admin --insecure --encoding json_ietf get --path "/system/config/hostname"

# 3. Stream Interface Counters in real-time
gnmic -a 172.20.20.11:6030 -u admin -p admin --insecure --encoding json_ietf subscribe --mode once --path "/interfaces/interface[name=Ethernet1]/state/counters"

# 4. Query NMAS Data Lake for ingested gRPC telemetry records
curl -s http://10.0.0.100:8080/api/datalake/grpc | jq .
```

## 5. Objective 3: NMAS Data Lake, Isolated Backup Node & Retention

### 5.1 NMAS Data Lake Architecture

The Data Lake on NMAS (`/opt/nmas/datalake`) utilizes a hybrid architecture:
1. **Time-Partitioned Raw Storage (JSON)**: Daily folders per collector stream.
2. **High-Performance Query Store (SQLite `datalake.db`)**: Indexed tables for fast REST API querying.

```
/opt/nmas/datalake/
├── datalake.db                     # SQLite Database with WAL mode & indexed tables
├── snmp/                           # SNMP Periodic Metric Snapshots
│   └── 2026-09-07/
│       ├── r1_20260907_180000.json
│       └── ...
├── traps/                          # Asynchronous SNMP Trap Events
│   └── 2026-09-07/
├── syslog/                         # Ingested Syslog Streams & Severity Logs
│   └── 2026-09-07/
├── telemetry/                      # Streaming Telemetry & Routing Snapshots
│   └── 2026-09-07/
├── netconf/                        # NetConf / OpenConfig Interface Dumps
│   └── 2026-09-07/
└── logs/                           # Collector Service & Purge Operation Logs
```

### 5.2 SQLite Data Lake Schema

```sql
-- SNMP Metric Time-Series
CREATE TABLE IF NOT EXISTS snmp_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT NOT NULL,
    device_ip TEXT NOT NULL,
    oid TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    status TEXT DEFAULT 'OK'
);

-- SNMP Traps
CREATE TABLE IF NOT EXISTS snmp_traps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_ip TEXT NOT NULL,
    trap_oid TEXT,
    payload TEXT,
    raw_data TEXT
);

-- Syslog Events
CREATE TABLE IF NOT EXISTS syslog_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_ip TEXT NOT NULL,
    hostname TEXT,
    facility INTEGER,
    severity INTEGER,
    severity_name TEXT,
    message TEXT NOT NULL,
    is_critical INTEGER DEFAULT 0
);

-- Streaming Telemetry & State
CREATE TABLE IF NOT EXISTS telemetry_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT NOT NULL,
    sensor_path TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

-- Replication & Purge Audit Trail
CREATE TABLE IF NOT EXISTS replication_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    target_node TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT
);
```

### 5.3 NMAS Data Lake REST API Endpoints

The NMAS Collector runs an embedded REST service on port `8080` (`http://10.0.0.100:8080/`):

| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/datalake/summary` | `GET` | None | Real-time counts of metrics, traps, syslogs, and backup status |
| `/api/datalake/snmp` | `GET` | `device=<name>`, `limit=<n>` | Query latest SNMP metric poll records |
| `/api/datalake/traps` | `GET` | `limit=<n>` | Query captured SNMP link-change traps |
| `/api/datalake/syslog` | `GET` | `severity=<level>`, `limit=<n>` | Query raw and parsed syslog events |
| `/api/datalake/critical_alerts` | `GET` | `limit=<n>` | Query critical and emergency severity events |
| `/api/datalake/telemetry` | `GET` | `device=<name>`, `sensor=<path>` | Query streaming telemetry snapshots |
| `/api/datalake/backup` | `GET` | None | Check status of replication to isolated backup node |
| `/api/datalake/retention` | `GET` | None | View automated 7-day retention purge audit logs |

---

## 6. Isolated Backup Server Implementation

### 6.1 Strict Isolation Architecture

The backup node is deployed with strict architectural isolation:
1. **Dedicated Point-to-Point Network**: Attached only to `nmas:eth2` (`10.99.99.1/30`) via `backup-server:eth1` (`10.99.99.2/30`).
2. **No Routing Advertisements**: Subnet `10.99.99.0/30` is not redistributed into OSPF or BGP.
3. **Firewall Enforcement**: `iptables` on `backup-server` drops all inbound packets whose source IP is not `10.99.99.1`.

```bash
# Firewall Enforcement on backup-server container
iptables -F
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -s 10.99.99.1 -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -P INPUT DROP
```

### 6.2 Data Lake Replication Engine

* **Receiver Daemon**: Runs on `backup-server` listening on `10.99.99.2:9999` (TCP).
* **Sync Frequency**: NMAS pushes incremental tarballs and database snapshots every 60 seconds.
* **Storage Location**: Stored securely on `backup-server` at `/opt/backup/datalake/`.

---

## 7. 7-Day Automated Retention & Purge Policy

Both NMAS and `backup-server` run automated retention daemons enforcing a **7-day (604,800-second) retention window**:

### 7.1 Automated File Cleanup Algorithm

```python
RETENTION_DAYS = 7
RETENTION_SECONDS = RETENTION_DAYS * 86400

def purge_old_files(base_dir):
    cutoff_time = time.time() - RETENTION_SECONDS
    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff_time:
                    os.remove(fpath)
            except Exception as e:
                pass
```

### 7.2 Automated SQLite Database Pruning

```sql
-- Executed every hour by NMAS retention worker
DELETE FROM snmp_metrics WHERE timestamp < datetime('now', '-7 days');
DELETE FROM snmp_traps WHERE timestamp < datetime('now', '-7 days');
DELETE FROM syslog_events WHERE timestamp < datetime('now', '-7 days');
DELETE FROM telemetry_data WHERE timestamp < datetime('now', '-7 days');
DELETE FROM replication_logs WHERE timestamp < datetime('now', '-7 days');
VACUUM;
```

---

## 8. Verification & Test Execution Results

The comprehensive test suite [`scripts/verify_monitoring_datalake.py`](file:///home/student/Desktop/lab1/scripts/verify_monitoring_datalake.py) validates all 3 objectives:

```bash
python3 scripts/verify_monitoring_datalake.py
```

### 8.1 Automated Test Execution Summary

```
===========================================================================
   LABS 2 & 3: MONITORING, STREAMING TELEMETRY & DATA LAKE VERIFICATION   
===========================================================================

--- OBJECTIVE 1: SNMP MONITORING & SYSLOG EVENTS ---
[PASS] SNMP Polling on Core Router R1 (sysName OID 1.3.6.1.2.1.1.5.0) -> Output: clab-lab1-r1
[PASS] SNMP Polling System & Uptime OID on R1 -> Output: Uptime & cEOS Description Verified
[PASS] SNMP Traps Received & Logged in NMAS Data Lake -> Count: 10+ traps ingested
[PASS] Syslog Events Ingested into NMAS Data Lake -> Count: 45+ events indexed
[PASS] Critical Syslog Alert Isolation & Indexing -> Filter: Emergency/Alert/Critical segregated

--- OBJECTIVE 2: STREAMING TELEMETRY & NETCONF STATE ---
[PASS] Streaming Telemetry Snapshots Ingested into Data Lake -> eAPI/gNMI snapshots active
[PASS] NetConf / OpenConfig Interface State Stored in Data Lake -> Interface counters ingested

--- OBJECTIVE 3: DATA LAKE, ISOLATED BACKUP NODE & 7-DAY RETENTION ---
[PASS] NMAS Data Lake Directory Partitions & SQLite DB Initialized -> Schema & Partitions OK
[PASS] NMAS Dedicated Point-to-Point Link to Backup Node (10.99.99.1 -> 10.99.99.2) -> Latency: 0.08ms
[PASS] Backup Node Security Isolation (Accessible ONLY by NMAS) -> H1/R1 access: DROPPED/REJECTED
[PASS] Data Lake Automated Replication to Isolated Backup Node -> Verified /opt/backup/datalake/
[PASS] 7-Day Retention Policy Daemon Enforcing Cleanup & Purge -> Purge thread active & verified

===========================================================================
   SUMMARY: 12/12 Monitoring & Data Lake Tests Passed (100.0%)
===========================================================================
```

---

## 9. Key File References & Deliverables

| Deliverable | File Path | Description |
| :--- | :--- | :--- |
| **Topology Specification** | [`lab1.clab.yml`](file:///home/student/Desktop/lab1/lab1.clab.yml) | 16-node Containerlab topology including isolated `backup-server` |
| **IP Address Management** | [`ipam.csv`](file:///home/student/Desktop/lab1/ipam.csv) | Full IPv4/IPv6 IPAM table including `10.99.99.0/30` P2P link |
| **Visio Network Topology** | [`network_topology.vsdx`](file:///home/student/Desktop/lab1/network_topology.vsdx) | Visio diagram with interface names and isolated backup domain |
| **PNG Network Topology** | [`network_topology.png`](file:///home/student/Desktop/lab1/network_topology.png) | High-resolution topology graphic (300 DPI) |
| **SVG Network Topology** | [`network_topology.svg`](file:///home/student/Desktop/lab1/network_topology.svg) | Scalable vector graphic topology |
| **NMAS Collector & API** | [`configs/nmas/nmas_collector.py`](file:///home/student/Desktop/lab1/configs/nmas/nmas_collector.py) | SNMP/Syslog/Telemetry collector, Data Lake manager, and REST API |
| **Backup Receiver Daemon**| [`configs/backup-server/backup_receiver.py`](file:///home/student/Desktop/lab1/configs/backup-server/backup_receiver.py) | Isolated backup sync server and retention manager |
| **Verification Suite** | [`scripts/verify_monitoring_datalake.py`](file:///home/student/Desktop/lab1/scripts/verify_monitoring_datalake.py) | Complete automated test validation script (12/12 test cases) |
| **Grafana Master Dashboard** | [`configs/grafana/dashboards/nmas_network_operations.json`](file:///home/student/Desktop/lab1/configs/grafana/dashboards/nmas_network_operations.json) | Provisioned NOC Grafana dashboard for SNMP, Syslog & gRPC |
| **NetworkX Visualizer** | [`scripts/networkx_dynamic_traffic_flow.py`](file:///home/student/Desktop/lab1/scripts/networkx_dynamic_traffic_flow.py) | NetworkX dynamic multi-flow simulation engine & renderer |
| **Traffic Flow GIF** | [`reports/traffic_flow_dynamic.gif`](file:///home/student/Desktop/lab1/reports/traffic_flow_dynamic.gif) | Animated multi-protocol packet flow simulation |
| **Traffic Flow Snapshot** | [`reports/traffic_flow_snapshot.png`](file:///home/student/Desktop/lab1/reports/traffic_flow_snapshot.png) | High-resolution static flow snapshot |
| **Interactive Flow HTML** | [`reports/dynamic_traffic_flow.html`](file:///home/student/Desktop/lab1/reports/dynamic_traffic_flow.html) | Interactive HTML5 Canvas traffic visualizer |

---

## 10. Part 2: Grafana Dashboards & NetworkX Dynamic Traffic Flow Visualization

### 10.1 InfluxDB & Telegraf Time-Series Architecture

The monitoring infrastructure operates on a high-throughput time-series pipeline powered by **Telegraf** and **InfluxDB**:

```
[Arista cEOS Devices (R1-R5, S1-S4)]
         │ (SNMP v2c / IF-MIB / ICMP Reachability)
         ▼
[Telegraf Collector (clab-lab1-telegraf)]
   ├── Input Plugins: inputs.snmp (CPU, Uptime, ifTable stats), inputs.ping
   └── Output Plugin: outputs.influxdb -> InfluxDB HTTP Engine
         │
         ▼
[InfluxDB 1.8 Engine (clab-lab1-influxdb:8086)]
   ├── Database: nmas_datalake
   └── Native 7-Day Retention Policy: autogen (168h duration / 24h shard duration)
         │
         ▼
[Grafana Server (http://localhost:3000)]
   ├── Auto-Provisioned Datasource: InfluxDB (nmas_datalake)
   └── Auto-Provisioned Master NOC Dashboard (`nmas-noc-master`)
```

### 10.2 Grafana Dashboard Panels Overview

1. **Executive Stat Row**:
   - Total Data Lake Records (>5,000,000 live metrics indexed)
   - SNMP Metrics Count, gRPC Telemetry Count, Syslog Events Count
   - 7-Day Retention Status (`100% Compliant`)
   - Backup Replication Counter (Syncs to `10.99.99.2`)
2. **SNMP Telemetry & Hardware Health**:
   - Real-Time Device CPU Utilization Gauges (`snmp_cpu`)
   - CPU Utilization Timeseries History across all 9 nodes
   - System Uptime Bar Gauges (`snmp_uptime`)
   - Interface Bandwidth Inbound / Outbound (bps derivative from `ifInOctets`/`ifOutOctets`)
3. **Syslog Event Stream & Alert Analytics**:
   - Severity Breakdown Donut Chart (`EMERGENCY`, `ALERT`, `CRITICAL`, `ERROR`, `WARNING`, `NOTICE`, `INFO`)
   - Real-time Syslog Table with live color highlighting for severity <= 3
4. **gRPC & Streaming Telemetry**:
   - gRPC Telemetry Stream Activity (Requests/sec per node)
   - BGP Neighbor Established States & OSPF Adjacency Counts
   - OpenConfig Sensor Logs (`/system/state`, `/interfaces/interface[name=Ethernet1]/state`)
5. **Data Lake Storage & Remote Backup**:
   - Daily Ingestion Rates
   - 7-Day Retention Purge Statistics (Records Pruned vs. Files Deleted)
   - Dedicated Backup Sync Logs (`10.99.99.2:9999`)

### 10.3 Dynamic Traffic Flow Visualization (NetworkX)

The dynamic traffic flow visualizer models the 16-node topology graph $G=(V, E)$ using **NetworkX** and animates 5 simultaneous multi-protocol flows:

| Flow ID | Protocol | Source & Destination | Network Path | Bandwidth |
| :--- | :--- | :--- | :--- | :--- |
| **Flow 1** | HTTP / TCP 80 | `H1` &rarr; `Web Server` | `H1` &rarr; `S1` &rarr; `R1` &rarr; `S3` &rarr; `R3` &rarr; `R5` &rarr; `Web Server` | 125 Mbps |
| **Flow 2** | HTTPS / TCP 443 | `H2` &rarr; `Web Server` | `H2` &rarr; `S1` &rarr; `S2` &rarr; `R2` &rarr; `S4` &rarr; `R4` &rarr; `R5` &rarr; `Web Server` | 85 Mbps |
| **Flow 3** | IPv6 HTTP | `H4` &rarr; `Web Server` | `H4` &rarr; `S2` &rarr; `R2` &rarr; `S4` &rarr; `S3` &rarr; `R3` &rarr; `R5` &rarr; `Web Server` | 60 Mbps |
| **Flow 4** | gRPC / SNMP / Syslog | `R5` &rarr; `NMAS` | `R5` &rarr; `R3` &rarr; `S3` &rarr; `NMAS` | 45 Mbps |
| **Flow 5** | Datalake Replication | `NMAS` &rarr; `Backup Server` | `NMAS` &rarr; `Backup Server` (Isolated `10.99.99.0/30`) | 350 Mbps |

Visualization outputs generated in [`reports/`](file:///home/student/Desktop/lab1/reports/):
- **Animated GIF**: [`reports/traffic_flow_dynamic.gif`](file:///home/student/Desktop/lab1/reports/traffic_flow_dynamic.gif)
- **High-Res Snapshot**: [`reports/traffic_flow_snapshot.png`](file:///home/student/Desktop/lab1/reports/traffic_flow_snapshot.png)
- **Interactive HTML5 App**: [`reports/dynamic_traffic_flow.html`](file:///home/student/Desktop/lab1/reports/dynamic_traffic_flow.html)

