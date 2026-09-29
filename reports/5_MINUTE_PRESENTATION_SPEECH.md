# 5-Minute Presentation Speech Script: End-to-End Network Automation, Observability & NSoT Platform
## Course: CSCI-5840 Advanced Network Management & Automation (Labs 1–4)
**Presenter**: Kavyashree Mahadevaiah (`aryastark11`)  
**Target Duration**: 5 Minutes (~700 words at 140 WPM)  
**Slide Deck**: `reports/Lab1_to_Lab4_Network_Automation_Presentation.pptx` (6 Slides)

---

### [0:00 – 0:45] Slide 1: Introduction & Platform Overview
> *"Good morning, everyone. Today, I am excited to present our enterprise-grade Network Automation, Observability, and Source of Truth platform built across Labs 1 through 4.*
>
> *Modern network engineering demands a transition away from manual, error-prone device configurations toward programmatic Infrastructure-as-Code, unified telemetry, and centralized Source of Truth architectures. Over the course of this project, we have designed and built a complete, self-healing network ecosystem spanning containerized multi-vendor fabrics, high-throughput time-series data lakes, real-time NOC dashboards, and a custom Django-based Network Source of Truth web portal with bidirectional telemetry integration.*
>
> *Let’s walk through what we built across each phase."*

---

### [0:45 – 1:45] Slide 2: Lab 1 — Multi-Vendor Fabric & IPAM Architecture
> *"In Lab 1, we established the foundational infrastructure of our network fabric. We migrated our routing and switching nodes from baseline FRR Linux containers to production-grade Arista cEOS running EOS version 4.33.*
>
> *As shown on the topology diagram on the right, our 16-node topology is structured hierarchically:*
> - *At the Distribution layer, routers **R1 and R2** provide inter-VLAN routing and redundant gateway services.*
> - *At the Core ASBR layer, routers **R3 and R4** run an internal BGP mesh within Autonomous System 65001 and interface with our OSPF Area 0 backbone.*
> - *At the Provider Edge, router **R5** terminates our WAN connection, peering via external BGP to the public Internet ISP in AS 65100.*
> - *Underneath, access switches **S1 and S2** and core switches **S3 and S4** segment traffic across VLANs 10 through 40.*
>
> *We implemented a comprehensive dual-stack IPv4 and IPv6 IPAM schema, complete with DHCPv4 and DHCPv6 server pools on R2 and SLAAC autoconfiguration for our end hosts."*

---

### [1:45 – 2:35] Slide 3: Lab 2 — Centralized NMAS & InfluxDB Data Lake
> *"Moving to Lab 2, we engineered the observability foundation with a dedicated Network Management and Automation Station—or **NMAS**.*
>
> *NMAS serves as our centralized data aggregation engine, orchestrating automated SNMP polling and gRPC streaming telemetry across all 9 cEOS switches and routers via Telegraf. Metric streams—including per-core CPU utilization, memory consumption, interface octets, and packet drops—are ingested directly into an **InfluxDB time-series data lake**.*
>
> *To adhere strictly to corporate retention requirements, we instituted an automated 7-day data lifecycle retention policy (`autogen`) that purges stale historical records while maintaining fine-grained operational metrics. Furthermore, we provisioned an **isolated secondary backup node** (`172.20.20.150`) that receives scheduled data lake snapshots, accessible strictly and exclusively by NMAS."*

---

### [2:35 – 3:25] Slide 4: Lab 3 — Real-Time Grafana NOC & Dynamic Traffic Visualization
> *"In Lab 3, we transformed raw telemetry into actionable visual intelligence through a Grafana Network Operations Center dashboard and a Python NetworkX dynamic traffic simulator.*
>
> *Our Grafana dashboard—live at port 3000—provides real-time gauge dials and time-series graphs of device CPU health, interface throughput in bits per second, drop rates, and ICMP latency. With sub-second gRPC streaming telemetry, operational anomalies and link bottlenecks are immediately visible.*
>
> *On the right, you can see our dynamic traffic flow visualization developed with NetworkX. It computes topology link loads dynamically and renders animated flows where green indicates healthy utilization under 50%, yellow highlights moderate load, and red flags link saturation exceeding 80%."*

---

### [3:25 – 4:20] Slide 5: Lab 4 & 5 (Part 1) — Django Network Source of Truth (NSoT) Portal
> *"In Lab 4, we built our crown jewel: a full-stack **Network Source of Truth (NSoT)** web platform powered by Python Django, operating at `http://localhost:8000`.*
>
> *The Django portal delivers five critical enterprise capabilities:*
> 1. *A real-time **Device Inventory** managing all 16 nodes with live status indicators.*
> 2. *A **Live eAPI Configuration Pull** engine executing privileged JSON-RPC commands against Arista cEOS nodes, with single-click batch synchronization.*
> 3. *A **Dynamic Device Provisioning Form** that tailors its fields depending on whether you are provisioning a Router or a Switch, with full file upload capabilities for running configs and Jinja2 templates.*
> 4. *A **Golden Configuration Snapshot Archive** that versions configuration snapshots in the database and filesystem, coupled with an in-browser **Unified Diff engine** to audit network drifts.*
> 5. *Seamless **Bidirectional Navigation**, allowing engineers to jump between the Django NSoT portal and the Grafana NOC dashboard with a single click."*

---

### [4:20 – 5:00] Slide 6: Multi-Vendor IaC Hierarchy, Git CI/CD & Roadmap
> *"Finally, we implemented complete multi-vendor Infrastructure-as-Code support for extra credit. We authored 13 hierarchical Jinja2 templates across four leading network operating systems: **Arista cEOS**, **Cisco NX-OS 9000v**, **Cisco IOS-XRv 9000**, and **SONiC VS**.*
>
> *By decoupling network intent into 16 standalone YAML data models, the exact same configuration intent can generate valid syntax for Arista, Cisco, or open-source SONiC devices.*
>
> *Our entire codebase, data models, and templates are version-controlled and live on GitHub at `github.com/aryastark11/advnetman`, verified with a 100% passing automated test suite.*
>
> *Looking ahead, this framework lays the perfect foundation for closed-loop self-healing networks and automated pre-deployment validation.*
>
> *Thank you, and I am now happy to take any questions."*
