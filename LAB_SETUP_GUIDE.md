# Advanced Network Automation — Lab 1 Setup Guide
## Multi-Protocol Container-Based Platform with Arista cEOS, Dual-Stack Routing, and Linux Endpoints

---

## 1. Overview & Architecture

This lab implements an enterprise multi-tier network topology entirely containerized using **Containerlab**, **Docker**, **Arista cEOS-lab**, and **Linux Alpine/Debian** containers. It features a complete enterprise and edge routing environment with dual-stack (IPv4/IPv6) support.

### 1.1 Architecture Highlights
* **Edge Routing (eBGP)**:
  * **AS 65005 (Provider Edge / Internet Simulation)**: Router **R5** originates default routes (`0.0.0.0/0` and `::/0`) and hosts the public Web Server (`198.51.100.0/24`, `2001:db8:100::/64`).
  * **AS 65001 (Enterprise Core ASBRs)**: Routers **R3** and **R4** peer with R5 over dedicated `/30` and `/64` links with multi-protocol BGP.
* **Core Backbone (OSPF Area 0)**:
  * Single-area OSPF backbone (`Area 0.0.0.0`) interconnecting **R3**, **R4**, **R1**, **R2**, **S3**, **S4**, and the **NMAS** (Network Management & Automation Station) over subnet `10.0.0.0/24` and `2001:db8:0::/64`.
  * Core switches **S3** and **S4** provide redundant Layer 2 bridged interconnectivity.
* **Distribution & Access Layers (RIPv2 & 802.1Q Trunks)**:
  * Routers **R1** and **R2** act as distribution gateways running RIPv2 and 802.1Q subinterfaces.
  * Mutual route redistribution between **OSPF Area 0** and **RIPv2** on R1 and R2.
  * Access switches **S1** and **S2** trunk VLANs 10, 20, and 30.
* **VLAN Segmentation & IPv6 Enforcement**:
  * **VLAN 10 (Dual-Stack)**: `10.10.10.0/24` | `2001:db8:10::/64` (Hosts H1 & H3)
  * **VLAN 20 (Dual-Stack)**: `10.10.20.0/24` | `2001:db8:20::/64` (Host H2)
  * **VLAN 30 (Strict IPv6-Only)**: `2001:db8:30::/64` (Host H4 — no IPv4 configured)
* **Services**:
  * **DHCPv4 & DHCPv6**: Hosted natively on Arista cEOS router **R2**.
  * **Web Services**: Python HTTP server hosted on `web-server` responding over IPv4 and IPv6.
  * **Automation Station**: `nmas` container equipped with Python, Scapy, TShark, Nmap, and network diagnostic utilities.

### 1.2 Topology Assets
* **Visio Diagram**: [`network_topology.vsdx`](network_topology.vsdx)
* **High-Resolution Diagram (PNG)**: [`network_topology.png`](network_topology.png)
* **Vector Diagram (SVG)**: [`network_topology.svg`](network_topology.svg)
* **IPAM Inventory (CSV)**: [`ipam.csv`](ipam.csv)

---

## 2. Platform Prerequisites & System Preparation

The lab runs on any modern 64-bit Linux distribution (Ubuntu 20.04/22.04/24.04, Debian 11/12, or RHEL/Rocky Linux 8/9).

### 2.1 Hardware Requirements
* **CPU**: 4 CPU cores minimum (8 cores recommended).
* **RAM**: 16 GB minimum (cEOS nodes require ~1.5 GB RAM each for 9 nodes = ~13.5 GB total).
* **Disk Space**: 20 GB free disk space.

### 2.2 System Kernel Tuning
cEOS creates multiple network interfaces, inotify instances, and file descriptors. Apply the following kernel parameters:

```bash
# Enable IPv4 and IPv6 packet forwarding
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1

# Prevent inotify exhaustion with multiple cEOS containers
sudo sysctl -w fs.inotify.max_user_instances=8192
sudo sysctl -w fs.inotify.max_user_watches=524288

# Increase memory mapping limits
sudo sysctl -w vm.max_map_count=262144

# Persist settings in /etc/sysctl.d/99-lab.conf
sudo tee /etc/sysctl.d/99-lab.conf << EOF
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 524288
vm.max_map_count = 262144
EOF
```

### 2.3 Installing Docker Engine
If Docker is not yet installed on the host system:

```bash
# Remove older versions
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker packages
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

### 2.4 Installing Containerlab
Containerlab orchestrates container-based networking topologies:

```bash
# Install the latest containerlab release
bash -c "$(curl -sL https://get.containerlab.dev)"

# Verify installation
containerlab version
```

### 2.5 Installing Python Helper Dependencies
Required for running diagram generation and automation verification scripts:

```bash
sudo apt-get install -y python3 python3-pip
pip3 install vsdx matplotlib pyyaml
```

---

## 3. Importing & Building Container Images

### 3.1 Importing the Arista cEOS Image
Download the Arista cEOS-lab image tarball from Arista Software Downloads (e.g., `cEOS-lab-4.33.10M.tar.xz`) and place it in the project root:

```bash
cd /home/student/Desktop/lab1

# Import the cEOS root filesystem into Docker
docker import cEOS-lab-4.33.10M.tar.xz ceos:latest

# Also tag with specific version for reference
docker tag ceos:latest ceos:4.33.10M

# Verify image import
docker images | grep ceos
```

Expected output:
```text
ceos    latest      4c9ade59e8f3   22 hours ago   2.25GB
ceos    4.33.10M    4c9ade59e8f3   22 hours ago   2.25GB
```

### 3.2 Building End-Host and Infrastructure Images
The lab uses custom lightweight Dockerfiles located under `docker/` for hosts, web server, and NMAS:

```bash
# 1. Build host image (Alpine with iproute2, curl, dhcpcd, tcpdump, python3)
docker build -t lab-host:latest -f docker/Dockerfile.host docker/

# 2. Build web server image (Alpine with python3, curl, iproute2)
docker build -t lab-web:latest -f docker/Dockerfile.web docker/

# 3. Build NMAS image (Debian Bookworm with Scapy, TShark, Nmap, Iperf3)
docker build -t lab-nmas:latest -f docker/Dockerfile.nmas docker/
```

Verify all images are ready:
```bash
docker images
```

---

## 4. Deploying the Containerlab Topology

### 4.1 Topology Definition Overview (`lab1.clab.yml`)
The topology is declared in [`lab1.clab.yml`](lab1.clab.yml). Key elements include:
* **Management Network**: Isolated bridge `lab1-mgmt` (`172.20.20.0/24`, `2001:db8:ffff::/64`).
* **Node Types**:
  * `r1` - `r5`: `kind: arista_ceos`, `image: ceos:latest`, bind-mounted startup configs in `configs/ceos/`.
  * `s1` - `s4`: `kind: arista_ceos`, `image: ceos:latest`, bind-mounted startup configs in `configs/ceos/`.
  * `h1` - `h4`: `kind: linux`, `image: lab-host:latest`, bind-mounted startup script `start.sh`.
  * `web-server`: `kind: linux`, `image: lab-web:latest`, runs dual-stack Python HTTP server.
  * `nmas`: `kind: linux`, `image: lab-nmas:latest`, monitoring station.

### 4.2 Deploying the Topology
Run the following command in the project directory:

```bash
sudo clab deploy -t lab1.clab.yml --reconfigure
```

Containerlab will:
1. Create Linux bridge `lab1-mgmt`.
2. Launch all 15 containers with connected veth pairs.
3. Apply management IP addresses.
4. Mount configuration files into each container.

### 4.3 Verifying Running Containers
Inspect the topology state:

```bash
clab inspect -t lab1.clab.yml
```

Verify that all 15 containers are in the `running` state:
* Routers: `clab-lab1-r1`, `clab-lab1-r2`, `clab-lab1-r3`, `clab-lab1-r4`, `clab-lab1-r5`
* Switches: `clab-lab1-s1`, `clab-lab1-s2`, `clab-lab1-s3`, `clab-lab1-s4`
* Hosts/Servers: `clab-lab1-h1`, `clab-lab1-h2`, `clab-lab1-h3`, `clab-lab1-h4`, `clab-lab1-web-server`, `clab-lab1-nmas`

> [!NOTE]
> Arista cEOS takes approximately 60–90 seconds to fully initialize its EOS subsystem and routing agents. Allow 1–2 minutes before executing CLI commands.

---

## 5. Device Configuration & Routing Architecture

### 5.1 Automated Configuration Deployment
The repository includes an automated configuration deployment script [`scripts/configure_arista_nodes.py`](scripts/configure_arista_nodes.py) that programs all 9 cEOS nodes using `FastCli`:

```bash
python3 scripts/configure_arista_nodes.py
```

### 5.2 Device Configurations Breakdown

#### A. Multi-Agent Routing Model (All Routers)
Arista EOS requires the multi-agent routing model to support multi-protocol BGP (including IPv6 address family):
```text
service routing protocols model multi-agent
```

#### B. Provider Edge Router (R5)
* **Interfaces**:
  * `Ethernet1`: `198.51.100.1/24`, `2001:db8:100::1/64` (to Web Server)
  * `Ethernet2`: `172.16.35.2/30`, `2001:db8:35::2/64` (to R3)
  * `Ethernet3`: `172.16.45.2/30`, `2001:db8:45::2/64` (to R4)
* **BGP Configuration (AS 65005)**:
  * Neighbors: `172.16.35.1` & `172.16.45.1` (AS 65001), `2001:db8:35::1` & `2001:db8:45::1`.
  * `default-originate` sent to both neighbors for IPv4 and IPv6.
  * Advertises `198.51.100.0/24` and `2001:db8:100::/64`.

#### C. Enterprise ASBR Routers (R3 & R4)
* **BGP (AS 65001)**:
  * eBGP peering with R5 (`172.16.35.2` and `172.16.45.2`).
  * Redistributes OSPF routes into BGP.
* **OSPF Area 0**:
  * Originates default route into OSPF Area 0 (`default-information originate always`).
  * Redistributes BGP routes into OSPF Area 0.
  * Connected to core backbone via `Ethernet2` (`10.0.0.3` / `10.0.0.4`).

#### D. Core Switches (S3 & S4)
* Functions as high-speed Layer 2 core bridge connecting R3, R4, R1, R2, and NMAS in VLAN 1.
* Cross-link between `S3:Ethernet2` and `S4:Ethernet2`.

#### E. Distribution Routers (R1 & R2)
* **OSPF Area 0 (Uplink)**:
  * `Ethernet1` connected to S3/S4 (`10.0.0.1` and `10.0.0.2`).
  * Participates in OSPF Area 0 for IPv4 and IPv6.
* **802.1Q Subinterfaces (Downlink to Access)**:
  * `Ethernet2.10`: Encapsulation `dot1q 10`, `10.10.10.1/24` (R1) / `.2` (R2)
  * `Ethernet2.20`: Encapsulation `dot1q 20`, `10.10.20.1/24` (R1) / `.2` (R2)
  * `Ethernet2.30` (R2 only): Encapsulation `dot1q 30`, `2001:db8:30::2/64`
* **RIPv2 Routing & Redistribution**:
  * Runs RIPv2 on VLAN 10 and VLAN 20 subinterfaces.
  * Mutual redistribution:
    ```text
    router ospf 1
     redistribute rip
    router rip
     redistribute ospf
    ```
* **Native DHCP Server (on R2)**:
  * Configured with DHCPv4 pools for VLAN 10 (`10.10.10.0/24`) and VLAN 20 (`10.10.20.0/24`).
  * Configured with DHCPv6 stateful/stateless pool for VLAN 30 (`2001:db8:30::/64`).

#### F. Access Layer Switches (S1 & S2)
* `Ethernet1`: 802.1Q Trunk to Distribution Router (R1 / R2).
* `Ethernet2`: 802.1Q Inter-Switch Trunk carrying VLANs 10, 20, 30.
* `Ethernet3`: Access Port VLAN 10 (connected to H1 / H3).
* `Ethernet4`: Access Port VLAN 20 (S1 to H2) / VLAN 30 (S2 to H4).

#### G. End-Host Configurations
* **H1** (`configs/h1/start.sh`): VLAN 10, `10.10.10.101/24`, `2001:db8:10::101/64`, Gateway `10.10.10.1`.
* **H2** (`configs/h2/start.sh`): VLAN 20, `10.10.20.102/24`, `2001:db8:20::102/64`, Gateway `10.10.20.1`.
* **H3** (`configs/h3/start.sh`): VLAN 10, `10.10.10.103/24`, `2001:db8:10::103/64`, Gateway `10.10.10.2`.
* **H4** (`configs/h4/start.sh`): VLAN 30 (**Strict IPv6-Only**), `2001:db8:30::104/64`, Gateway `2001:db8:30::2`.
* **web-server** (`configs/web-server/start.sh`): `198.51.100.10/24`, `2001:db8:100::10/64`, runs HTTP server on port 80.
* **nmas** (`configs/nmas/start.sh`): `10.0.0.100/24`, `2001:db8:0::100/64`, Gateway `10.0.0.1`.

---

## 6. Testing & Connectivity Verification

### 6.1 Automated Verification Suite
An end-to-end automated test suite is provided in [`scripts/verify_topology.py`](scripts/verify_topology.py).

Run the automated test suite:
```bash
python3 scripts/verify_topology.py
```

Expected output:
```text
======================================================================
   ADVANCED NETWORK AUTOMATION - LAB 1 VERIFICATION TEST SUITE   
======================================================================

--- 1. HOST TO INTERNET WEB SERVER CONNECTIVITY ---
[PASS] H1 (VLAN 10) -> Web Server IPv4 Ping
[PASS] H1 (VLAN 10) -> Web Server HTTP GET
[PASS] H2 (VLAN 20) -> Web Server IPv4 Ping
[PASS] H2 (VLAN 20) -> Web Server HTTP GET
[PASS] H3 (VLAN 10) -> Web Server IPv4 Ping
[PASS] H3 (VLAN 10) -> Web Server HTTP GET
[PASS] H4 (VLAN 30: IPv6 Only) -> Web Server IPv6 Ping
[PASS] H4 (VLAN 30: IPv6 Only) -> Web Server HTTP GET (IPv6)

--- 2. INTER-VLAN & INTRA-VLAN CONNECTIVITY ---
[PASS] H1 (VLAN 10) <-> H3 (VLAN 10) Intra-VLAN Ping
[PASS] H1 (VLAN 10) <-> H2 (VLAN 20) Inter-VLAN Ping
[PASS] H2 (VLAN 20) <-> H3 (VLAN 10) Inter-VLAN Ping
[PASS] H1 (VLAN 10) <-> H4 (VLAN 30) IPv6 Ping
[PASS] H2 (VLAN 20) <-> H4 (VLAN 30) IPv6 Ping

--- 3. VLAN 30 IPV6-ONLY ENFORCEMENT CHECK ---
[PASS] H4 (VLAN 30) has NO IPv4 address configured (Strict IPv6-Only)

--- 4. NMAS (NETWORK MANAGEMENT & AUTOMATION STATION) REACHABILITY ---
[PASS] NMAS -> Web Server IPv4 Ping
[PASS] NMAS -> Web Server IPv6 Ping
[PASS] NMAS -> H1 (VLAN 10) Ping
[PASS] NMAS -> H4 (VLAN 30) IPv6 Ping

--- 5. ROUTING PROTOCOL VALIDATIONS ---
[PASS] BGP Session R5 <-> R3 (IPv4/IPv6)
[PASS] BGP Session R5 <-> R4 (IPv4/IPv6)
[PASS] OSPF Area 0 Adjacencies Established on R1
[PASS] RIPv2 Routes Converged on R1

======================================================================
   SUMMARY: 22/22 Tests Passed (100.0%)
======================================================================

ALL TOPOLOGY AND PROTOCOL REQUIREMENTS MET PERFECTLY!
```

---

### 6.2 Manual Verification & Interactive CLI Commands

#### 1. Arista EOS Device CLI Access
Access any cEOS router or switch using Docker exec:

```bash
# Interactive EOS CLI
docker exec -it clab-lab1-r1 Cli

# Single-command FastCli execution
docker exec clab-lab1-r1 FastCli -p 15 -c "show ip route"
```

#### 2. Verify BGP Neighbor Status on R5
```bash
docker exec clab-lab1-r5 FastCli -p 15 -c "show ip bgp summary"
docker exec clab-lab1-r5 FastCli -p 15 -c "show ipv6 bgp summary"
```
*Verify that state is `Estab` with peers `172.16.35.1` and `172.16.45.1`.*

#### 3. Verify OSPF Area 0 Neighbors on R1
```bash
docker exec clab-lab1-r1 FastCli -p 15 -c "show ip ospf neighbor"
```
*Verify that neighbor relationships with R2 (`10.0.0.2`), R3 (`10.0.0.3`), and R4 (`10.0.0.4`) are in `FULL` state.*

#### 4. Verify RIPv2 Routes & Redistribution on R1
```bash
docker exec clab-lab1-r1 FastCli -p 15 -c "show ip rip database"
docker exec clab-lab1-r1 FastCli -p 15 -c "show ip route rip"
```

#### 5. Verify VLAN Table on Switch S1
```bash
docker exec clab-lab1-s1 FastCli -p 15 -c "show vlan"
docker exec clab-lab1-s1 FastCli -p 15 -c "show mac address-table"
```

#### 6. Test Host-to-Internet Web Reachability
```bash
# IPv4 Ping and HTTP request from H1 (VLAN 10)
docker exec clab-lab1-h1 ping -c 3 198.51.100.10
docker exec clab-lab1-h1 curl -i http://198.51.100.10

# IPv6 Ping and HTTP request from H4 (VLAN 30: IPv6 Only)
docker exec clab-lab1-h4 ping6 -c 3 2001:db8:100::10
docker exec clab-lab1-h4 curl -6 -i http://[2001:db8:100::10]
```

#### 7. Traceroute Multi-Hop Path
Trace the route from H1 to the Web Server across the access, distribution, core, and edge layers:
```bash
docker exec clab-lab1-h1 traceroute -n 198.51.100.10
```
Expected hop path:
1. `10.10.10.1` (R1 - Default Gateway)
2. `10.0.0.3` / `10.0.0.4` (R3 / R4 - ASBR)
3. `172.16.35.2` / `172.16.45.2` (R5 - PE Router)
4. `198.51.100.10` (Web Server - Destination)

---

## 7. Operational Lifecycle & Management

### 7.1 Saving Running Configurations
To persist configurations across container restarts:
```bash
for node in r1 r2 r3 r4 r5 s1 s2 s3 s4; do
    docker exec clab-lab1-$node FastCli -p 15 -c "write memory"
done
```

### 7.2 Generating Updated Topology Diagrams
To refresh the Visio, PNG, and SVG diagrams if the topology or addressing changes:
```bash
python3 scripts/create_topology_diagram.py
```

### 7.3 Regenerating Configurations
To rebuild startup configurations from templates:
```bash
python3 scripts/generate_ceos_configs.py
```

### 7.4 Tearing Down the Lab
To completely destroy the lab environment and clean up all veth interfaces and bridges:
```bash
sudo clab destroy -t lab1.clab.yml --cleanup
```

---

## 8. Common Issues & Troubleshooting FAQ

### Q1: BGP shows error: "% BGP is not supported under the default routing model"
* **Cause**: Arista EOS defaults to a single-agent routing daemon which does not support multi-protocol BGP.
* **Fix**: Run `service routing protocols model multi-agent` in configuration mode, save with `write memory`, and restart the routing agent or node.

### Q2: Error "too many open files" or "no space left on device" when starting cEOS
* **Cause**: The Linux kernel inotify watch/instance limit is too low for 9 cEOS instances.
* **Fix**: Increase the kernel limits:
  ```bash
  sudo sysctl -w fs.inotify.max_user_instances=8192
  sudo sysctl -w fs.inotify.max_user_watches=524288
  ```

### Q3: Hosts cannot reach the Web Server on `198.51.100.10`
* **Check 1**: Is R5 originating the default route? Verify on R5: `show ip bgp neighbor 172.16.35.1 | grep -i default`.
* **Check 2**: Is OSPF redistributing default route? Verify on R3: `show ip ospf | grep -i default`.
* **Check 3**: Is RIP receiving default route from OSPF? Verify on R1: `show ip route rip`.

### Q4: H4 has an IPv4 address
* **Check**: Ensure `configs/h4/start.sh` does not assign an IPv4 address and disables IPv4 DHCP on `eth1` (`ip -4 addr flush dev eth1`). H4 is strictly IPv6-only.

---

## 9. Summary File Reference Table

| File | Type | Description |
| :--- | :--- | :--- |
| [`lab1.clab.yml`](lab1.clab.yml) | Topology Definition | Containerlab topology declaring nodes, kinds, images, and links |
| [`LAB_SETUP_GUIDE.md`](LAB_SETUP_GUIDE.md) | Documentation | Comprehensive setup, configuration, and verification guide |
| [`ipam.csv`](ipam.csv) | IPAM Inventory | Complete IPv4, IPv6, MAC, and DHCP assignment tracking spreadsheet |
| [`network_topology.vsdx`](network_topology.vsdx) | Visio Drawing | Native Microsoft Visio diagram with all 15 nodes, links, and ports |
| [`network_topology.png`](network_topology.png) | Image Graphic | High-resolution (300 DPI) rendering of network topology |
| [`network_topology.svg`](network_topology.svg) | Vector Graphic | Scalable vector graphic for web and documentation |
| [`scripts/verify_topology.py`](scripts/verify_topology.py) | Verification Script | Automated 22-point validation test suite |
| [`scripts/configure_arista_nodes.py`](scripts/configure_arista_nodes.py) | Config Pusher | Automation script to apply EOS configs to running cEOS nodes |
| [`scripts/generate_ceos_configs.py`](scripts/generate_ceos_configs.py) | Config Generator | Generates `.cfg` files for all 9 cEOS routers and switches |
| [`scripts/create_topology_diagram.py`](scripts/create_topology_diagram.py) | Diagram Generator | Generates `.vsdx`, `.png`, and `.svg` diagrams |
| `configs/ceos/` | Configuration Directory | Startup configuration files for routers `r1`–`r5` and switches `s1`–`s4` |
| `docker/` | Dockerfiles | Dockerfiles for hosts, web server, and NMAS station |
