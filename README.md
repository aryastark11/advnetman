# RCN NetSleuth AI

> **Evidence-First, Closed-Loop Autonomous Network Troubleshooting & Remediation Copilot**  
> *CSCI 5840 Labs 9–10 — Hackathon Edition*

---

## Architecture Overview

NetSleuth AI operates on a **Deterministic Core + LLM Shell** philosophy. Fault detection, blast-radius calculation, and topology path validation are strictly deterministic and function even with the LLM offline. The LLM (Gemini API) is read-only, never performs write operations directly, and serves exclusively to explain, correlate, and rank root-cause hypotheses against structured evidence. Remediation requires explicit human-in-the-loop approval, executes via Arista eAPI, takes a pre-change snapshot, verifies convergence across data and control planes, and automatically rolls back if post-checks fail.

```
+----------------------------------------------------------------------------------------------------+
|                                    MODERN HACKATHON WEB UI (Port 8000)                             |
|  +---------------------------+  +-------------------------------+  +----------------------------+  |
|  |   Interactive SVG Map     |  |     Incident Deep-Dive        |  |    AI Copilot Chat Dock    |  |
|  | - 23 Nodes / 24 Links     |  | - Blast Radius Hosts/Svcs     |  | - Read-Only Tools          |  |
|  | - Glowing Health Rings    |  | - Evidence Chips (EVID-xxx)   |  | - Evidence Citations       |  |
|  | - Path Tracer Inspection  |  | - Human Approval Button       |  | - RAG Runbook Citations    |  |
|  +---------------------------+  +-------------------------------+  +----------------------------+  |
+--------------------------------------------------+-------------------------------------------------+
                                                   | REST API / JSON
+--------------------------------------------------v-------------------------------------------------+
|                                        FASTAPI BACKEND                                             |
|   /api/topology  |  /api/incidents  |  /api/path  |  /api/remediate  |  /api/copilot/chat           |
+--------------------------+-----------------------------------------------+-------------------------+
                           |                                               |
+--------------------------v--------------------+   +----------------------v-------------------------+
|              DETERMINISTIC ENGINE             |   |                    LLM SHELL                   |
| - Health Rules (BGP, OSPF, RIP, VARP, Intf)   |   | - Provider-Agnostic LLMClient (Gemini API)     |
| - Blast Radius Computation                    |   | - Secret Redaction (Hashes, Passwords, Keys)   |
| - Evidence Aggregator (Unique EVID-IDs)       |   | - JSON Schema Enforcement (Pydantic)           |
| - Incident State Machine & Auto-Recovery      |   | - RAG Retrieval over `runbooks/*.md`           |
| - Graph Path Tracer (NetworkX + Live Checks)  |   | - Read-Only Diagnostic Tool Dispatcher         |
+--------------------------+--------------------+   +------------------------------------------------+
                           |
+--------------------------v-------------------------------------------------------------------------+
|                                    CLOSED-LOOP REMEDIATION ENGINE                                  |
|   Human Approval  -->  Pre-Change Snapshot  -->  eAPI Config Commit  -->  Post-Verification        |
|                                                                                |                   |
|                        Success: Resolve & Audit Log   <------------------------+-- PASS            |
|                        Fail:    Auto-Rollback Snapshot & Audit Log <-----------+-- FAIL            |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
+--------------------------------------------------v-------------------------------------------------+
|                                 TELEMETRY & DEVICE INTEGRATION                                     |
| - Arista eAPI (pyeapi): R1–R8, S1–S4 (Strictly JSON-RPC, No CLI Scraping)                         |
| - HashiCorp Vault: AppRole credential fetching (`network/devices/*`)                               |
| - Synthetic Probes: Multi-threaded ICMP & HTTP probes (35 targets every 10s)                       |
| - InfluxDB + Telegraf: Unified telemetry streaming                                                |
| - SQLite Incident & Audit Store (`netsleuth.db`)                                                   |
+----------------------------------------------------------------------------------------------------+
```

---

## Lab 9–10 Requirement to Feature Mapping

| Requirement | NetSleuth Feature | Implementation Module | Verification Status |
|---|---|---|---|
| **F1: Live Topology Map** | Interactive SVG canvas rendering 23 nodes and 24 links with dynamic health glow, node evidence drawer, and config drift badge. | `netsleuth/graph/topology.py`, `netsleuth/web/static/` | **PASSED** (Matches Lab 10 spec) |
| **F2: Synthetic Probes** | 35 multi-threaded probes every 10s (Host → Gateway, Core, R5, Web Server ICMP + HTTP). | `netsleuth/collectors/synthetic_probes.py` | **PASSED** (0 failures nominal) |
| **F3: Hop-by-Hop Path Tracer** | Computes expected path H1–H7 to Web Server; performs live per-hop checks (link state, adjacency, routes); flags first failing hop. | `netsleuth/graph/path_tracer.py` | **PASSED** (Isolated down hops) |
| **F4: Incident Engine** | Deterministic rules (OSPF, BGP, RIP, VARP, interfaces, probes); precise blast-radius computation (affected hosts/services). | `netsleuth/engine/` (`rules.py`, `blast_radius.py`, `incident_engine.py`) | **PASSED** (100% deterministic) |
| **F5: LLM Diagnosis** | Structured prompt with redacted configs, diffs, and RAG runbooks; Pydantic JSON schema validation; evidence-first fallback. | `netsleuth/llm/` (`client.py`, `schema.py`, `redaction.py`, `rag.py`) | **PASSED** (Top hypothesis matches) |
| **F6: Evidence-Linked Copilot** | Chat dock anchored to incident; strictly read-only diagnostic tools (`get_path`, `get_ospf_neighbors`, `get_bgp_peers`, `get_logs`, etc.); cites `EVID-...`. | `netsleuth/llm/tools.py`, `netsleuth/api/main.py` | **PASSED** (Read-only verified) |
| **F7: Closed-Loop Remediation** | Human approval gate; pre-remediation config snapshot; eAPI commit; automated post-verification; automated rollback on failure; audit logging. | `netsleuth/remediation/engine.py` | **PASSED** (Rollback verified) |
| **F8: Unified Incident Timeline** | Single chronological timeline combining probe failures, syslog events, adjacency collapses, LLM analysis, approval, remediation, and recovery. | `netsleuth/storage/db.py`, `netsleuth/engine/incident_engine.py` | **PASSED** (Audit trail verified) |
| **F9: Golden-Config Drift** | Nightly and on-demand config diffing against baseline repository configs; drift severity tracking and context injection. | `netsleuth/collectors/eapi_poller.py`, `netsleuth/storage/db.py` | **PASSED** (Diff engine active) |
| **F10: Demo & Fault Injection** | Automated CLI and 1-click UI Quick Bar supporting all 7 test scenarios + deliberate bad-fix rollback verification. | `scripts/inject_fault.py`, `netsleuth/scripts/inject_fault.py` | **PASSED** (7/7 Scenarios + Rollback) |

---

## How to Run NetSleuth

### 1. Prerequisites
- Linux host running Docker and Containerlab (`lab1.clab.yml` active).
- HashiCorp Vault initialized and unsealed (`https://127.0.0.1:8200`).
- Python 3.10+ virtual environment.

### 2. Environment Configuration
Copy `.env.example` to `.env` and set your API keys:
```bash
cp .env.example .env
# Edit .env and supply GEMINI_API_KEY
```

### 3. Start NetSleuth Backend & UI
```bash
# Start FastAPI server on port 8000
python3 -m uvicorn netsleuth.api.main:app --host 0.0.0.0 --port 8000
```
Open your browser to: **`http://localhost:8000`**

### 4. Run the Full Automated Test Suite
```bash
# Run unit tests
python3 -m unittest tests/test_unit.py

# Run integration tests against live devices
python3 -m unittest tests/test_integration.py

# Run end-to-end fault injection and remediation tests
python3 -m unittest tests/test_fault_injection.py

# Or discover and run all 17 tests together
python3 -m unittest discover tests/
```

---

## Fault Scenarios & Test Suite

NetSleuth includes automated fault injection across all 7 lab failure domains:

| Scenario Name | Injected Failure | Target Device | Detection Category | Blast Radius |
|---|---|---|---|---|
| `interface-down` | `interface Ethernet2 shutdown` | R1 | Data Plane - Interface | Core transit, access path degradation |
| `ospf-area-mismatch` | `interface Ethernet3 ip ospf area 99` | R4 | Control Plane - OSPF | Area 10 routes (R6, R7, H5) |
| `rip-missing-network` | `router rip` -> remove `10.10.0.0/16` | R1 | Control Plane - RIP | VLAN 10/20 routes from S1/S2 |
| `bgp-peer-down` | `router bgp 65005` -> `neighbor 172.16.35.1 shutdown` | R5 | Control Plane - BGP | H1–H4 Internet egress to Web Server |
| `vlan-trunk-missing` | `interface Ethernet1 switchport trunk allowed vlan 20` | S1 | Data Plane - Interface | H1, H3 VLAN 10 probe failures |
| `varp-gateway-down` | `interface Ethernet2.10 shutdown` | R1 | High Availability - VARP | VLAN 10 first-hop redundancy failure |
| `webserver-down` | `pkill -f python3` inside web container | Web Server | Service - Web Server | All hosts (H1–H7) HTTP service loss |

### Fault Injection CLI Usage
```bash
# Inject a fault
python3 scripts/inject_fault.py --scenario bgp-peer-down

# Clear a specific fault
python3 scripts/inject_fault.py --scenario bgp-peer-down --clear

# Clear all faults across the network and restore baseline
python3 scripts/inject_fault.py --clear
```

---

## Hackathon Video Demo Script (Step-by-Step)

### Setup
- Ensure Containerlab topology is running and NetSleuth is open at `http://localhost:8000`.
- Have a terminal open side-by-side with the web browser.

### Scene 1: Baseline Network & Interactive Topology
1. **Show Web UI**: Point out the live topology map showing all 23 nodes and 24 links.
   - All nodes glow **green** (healthy).
   - Point out the tiers: Access Switches (S1, S2, S5), Core Routers (R1–R4, S3, S4), Distribution/Area Routers (R6, R7, R8), Edge Router (R5), and Web Server.
2. **Node Evidence Panel**: Click on router **R5**.
   - Note the live evidence panel on the right: BGP peers (Established with R3, R4), interface counters, OSPF state, and Golden Config drift status.
3. **Live Path Tracer**: On the left sidebar, click **Trace Path** from `H1` to `Web Server`.
   - Show the clean hop-by-hop path (`H1` → `S1` → `R1` → `R3` → `R5` → `Web Server`) with green checks on every hop.

### Scene 2: Fault Injection (eBGP Peering Session Collapse)
1. **Trigger Fault**:
   - In the top **Demo Quick Bar**, click **"BGP Peer Down"** (or run `python3 scripts/inject_fault.py --scenario bgp-peer-down` in terminal).
2. **Observe Real-Time Detection**:
   - Within seconds, **R5** turns **amber/red**.
   - Synthetic probe fails from H1/H2/H3/H4.
   - A critical incident card appears in the left feed: **`BGP Session Down on R5 to Peer 172.16.35.1`**.
   - Highlight the **Blast Radius**: `Affected Hosts: H1, H2, H3, H4`. Explain that this was computed deterministically by the graph engine without needing an LLM.

### Scene 3: Evidence-First LLM Diagnosis & Runbook Match
1. **Open Incident Deep-Dive**: Click on the new BGP incident card.
2. **Review Evidence Chips**:
   - Show the structured evidence items citing IDs (e.g. `EVID-10492` showing BGP state `Idle` on R5).
3. **Trigger AI Diagnosis**:
   - Click **Run AI Diagnosis**.
   - The LLM parses the redacted evidence and matches the runbook `runbooks/bgp-peer-down.md`.
   - The Root Cause Hypothesis appears with a confidence meter (e.g., `96% Confidence`):
     - *Cause*: eBGP session between R5 (AS 65005) and R3 (172.16.35.1) is administratively shut down.
     - *Proposed Fix*: `router bgp 65005` -> `no neighbor 172.16.35.1 shutdown`.

### Scene 4: AI Copilot Interactive Investigation
1. **Interact with Copilot**: In the bottom-right AI Copilot chat dock, ask:
   - *"What is the current operational state of neighbor 172.16.35.1?"*
2. **Show Tool Execution**:
   - Point out that the copilot autonomously calls read-only tool `get_bgp_peers(device="R5")` and responds with exact evidence citing peer state `Idle`.

### Scene 5: Closed-Loop Remediation with Post-Verification
1. **Human Approval Gate**:
   - Review the proposed eAPI commands in the remediation card.
   - Click **Approve & Remediate**.
2. **Watch the Orchestration**:
   - Step 1: Pre-remediation snapshot of R5 running-config is captured.
   - Step 2: Commands are applied to R5 via eAPI (`FastCli / pyeapi`).
   - Step 3: Engine waits 2s for convergence and re-runs synthetic probes and BGP health checks.
   - Step 4: Verification **PASSES**. All 35 synthetic probes recover to green.
   - The incident automatically transitions to **Resolved**.
   - Show the **Timeline**: from first probe failure -> incident created -> human approval -> fix applied -> verification passed -> resolved.

### Scene 6: Adversarial Test — Automated Rollback on Bad Fix
1. **Inject Fault**: Click **BGP Peer Down** again.
2. **Execute Ineffective / Bad Fix**:
   - Show that if a fix does not resolve the failure or fails post-verification, NetSleuth detects that probes still fail.
   - The engine automatically triggers **Automatic Rollback**, restores the pre-snapshot, marks the incident as `rollback`, and writes an immutable audit record to `netsleuth.db`.
3. **Conclusion**: Reset all scenarios with **Clear All**; point out that all 23 nodes and 35 probes return to 100% healthy.

---

## Repository Structure

```
netsleuth/
├── api/             # FastAPI backend (endpoints for topology, incidents, path, remediation, copilot)
├── collectors/      # eAPI pollers, synthetic probe runner (ICMP/HTTP), HashiCorp Vault client
├── engine/          # Deterministic rules (OSPF, BGP, RIP, VARP, intf), blast radius, evidence builder
├── graph/           # NetworkX topology graph and hop-by-hop path tracer with live checks
├── llm/             # Provider-agnostic LLMClient, Gemini API, Pydantic schemas, redaction, RAG
├── remediation/     # Pre-snapshot, eAPI config commit, verification, and automatic rollback engine
├── storage/         # SQLite schema & repository (incidents, timeline, probes, health, audit logs)
└── web/             # Modern hackathon frontend (index.html, styles.css, app.js)
runbooks/            # Markdown runbooks for all 7 fault scenarios
scripts/             # Demo & fault injection CLI (`inject_fault.py`)
tests/               # Unit, integration, and fault injection test suites
```

---

## License & Academic Integrity
Developed for CSCI 5840 (Advanced Computer Networks). Strictly adheres to the evidence-first, read-only-by-default, and secret-redaction architectural principles.
