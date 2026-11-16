#!/usr/bin/env python3
"""
Dynamic Network Traffic Flow Visualization using NetworkX and Matplotlib.
Models the enterprise topology (23 nodes, multi-tier OSPF Area 0/10/20/30, BGP, RIP, and VLAN architecture)
and visualizes dynamic multi-protocol traffic flows with bandwidth utilization and protocol highlighting.
"""

import os
import math
import json
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

REPORTS_DIR = "/home/student/Desktop/lab1/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# 1. Define Topology Graph with NetworkX
G = nx.Graph()

nodes_info = {
    # Node: (x, y, label, node_type, ip, extra, routing_protocol)
    # Legacy Hosts & Servers
    "H1": (1.8, 1.8, "H1 (Campus Host)", "host", "10.10.10.101", "VLAN 10", "Static GW (10.10.10.254)"),
    "H2": (4.2, 1.8, "H2 (Campus Host)", "host", "10.10.20.102", "VLAN 20", "Static GW (10.10.20.254)"),
    "H3": (6.6, 1.8, "H3 (Campus Host)", "host", "10.10.10.103", "VLAN 10", "Static GW (10.10.10.254)"),
    "H4": (9.0, 1.8, "H4 (Campus Host)", "host", "2001:db8:30::104", "VLAN 30 (IPv6)", "Static GW (IPv6)"),

    # Access Switches (Legacy)
    "S1": (3.0, 4.2, "S1 (Access Switch)", "switch", "172.20.20.21", "VLAN 10,20,30", "Layer 2 802.1Q Trunk"),
    "S2": (7.8, 4.2, "S2 (Access Switch)", "switch", "172.20.20.22", "VLAN 10,20,30", "Layer 2 802.1Q Trunk"),

    # Distribution Routers (Area 0 Backbone & Access)
    "R1": (3.0, 7.0, "R1 (Dist / Master)", "router", "10.0.0.1", "VRRP Master", "OSPF Area 0 / RIPv2"),
    "R2": (7.8, 7.0, "R2 (Dist / ABR)", "router", "10.0.0.2", "VRRP Backup / DHCP", "OSPF Area 0 & Area 30 ABR / RIPv2"),

    # Observability & Management
    "NMAS": (1.0, 9.4, "NMAS Station", "server", "10.0.0.100", "Data Lake / NOC", "Host / Telemetry Collector"),
    "Backup Server": (1.0, 12.0, "Backup Node", "backup", "10.99.99.2", "Isolated Backup", "Direct Route (10.99.99.0/30)"),

    # Core Backbone Switches (Area 0)
    "S3": (3.8, 9.4, "S3 (Core Switch)", "switch", "172.20.20.23", "Area 0 Bridge", "OSPF Area 0 Backbone"),
    "S4": (7.0, 9.4, "S4 (Core Switch)", "switch", "172.20.20.24", "Area 0 Bridge", "OSPF Area 0 Backbone"),

    # Core ASBRs
    "R3": (3.5, 12.0, "R3 (ASBR)", "router", "10.0.0.3", "AS 65001 ASBR", "eBGP AS 65005 & OSPF Area 0"),
    "R4": (7.2, 12.0, "R4 (ASBR / ABR)", "router", "10.0.0.4", "AS 65001 ASBR", "eBGP AS 65005, OSPF Area 0 & Area 10"),

    # Provider Edge & WAN Web Services
    "R5": (5.4, 14.4, "R5 (PE Router)", "pe_router", "172.16.35.2", "BGP AS 65005", "eBGP AS 65001 / Connected DMZ"),
    "Web Server": (9.0, 14.4, "Web Server", "server", "198.51.100.10", "HTTP DMZ", "Connected WAN (198.51.100.0/24)"),

    # --- NEW EXPANSION DEVICES & ROUTING PROTOCOLS ---
    # OSPF Area 10 & Area 20 Branch
    "R6": (11.5, 12.0, "R6 (Edge / ABR)", "new_router", "10.46.46.6", "Area Border Router", "OSPF Area 10 & Area 20"),
    "R7": (15.2, 12.0, "R7 (Edge Router)", "new_router", "10.67.67.7", "Branch Distribution", "OSPF Area 20 (10.70.10.0/24)"),
    "H5": (15.2, 9.4, "H5 (Branch Host)", "new_host", "10.70.10.105", "VLAN 10 Subnet", "Default GW via R7 (OSPF Area 20)"),

    # OSPF Area 30 & S5 Access Branch
    "R8": (11.5, 7.0, "R8 (Distribution)", "new_router", "10.28.28.100", "Branch Distribution", "OSPF Area 30 (10.80.10.0/24)"),
    "S5": (11.5, 4.2, "S5 (Access Switch)", "new_switch", "172.20.20.25", "VLAN 10 Access Switch", "Layer 2 802.1Q Trunk to R8"),
    "H6": (11.5, 1.8, "H6 (Campus Host)", "new_host", "10.80.10.106", "VLAN 10 Subnet", "Default GW via R8 (OSPF Area 30)"),
    "H7": (14.0, 1.8, "H7 (Campus Host)", "new_host", "10.80.10.107", "VLAN 10 Subnet", "Default GW via R8 (OSPF Area 30)"),
}

for node, (x, y, label, ntype, ip, extra, proto) in nodes_info.items():
    G.add_node(node, pos=(x, y), label=label, type=ntype, ip=ip, extra=extra, protocol=proto)

# Physical/Logical Links (u, v, link_type, capacity_mbps, latency_ms, protocol_domain, color)
links = [
    # Legacy Access Links
    ("H1", "S1", "Access VLAN 10", 1000, 0.5, "L2 Access", "#94a3b8"),
    ("H2", "S1", "Access VLAN 20", 1000, 0.5, "L2 Access", "#94a3b8"),
    ("H3", "S2", "Access VLAN 10", 1000, 0.5, "L2 Access", "#94a3b8"),
    ("H4", "S2", "Access VLAN 30 (IPv6)", 1000, 0.5, "L2 Access", "#94a3b8"),
    ("S1", "S2", "802.1Q Inter-Switch Trunk", 1000, 1.0, "802.1Q Trunk", "#94a3b8"),
    ("S1", "R1", "802.1Q Router-on-a-Stick", 1000, 0.8, "RIPv2 / VRRP", "#c084fc"),
    ("S2", "R2", "802.1Q Router-on-a-Stick", 1000, 0.8, "RIPv2 / VRRP", "#c084fc"),
    ("R1", "R2", "Distribution VRRP Cross-Link", 1000, 0.5, "VRRP / RIPv2", "#c084fc"),
    
    # Core Backbone Area 0 Links
    ("R1", "S3", "OSPF Area 0 Transit", 1000, 1.2, "OSPF Area 0", "#38bdf8"),
    ("R2", "S4", "OSPF Area 0 Transit", 1000, 1.2, "OSPF Area 0", "#38bdf8"),
    ("S3", "S4", "Core Inter-Switch Link", 10000, 0.3, "OSPF Area 0 Bridge", "#38bdf8"),
    ("S3", "NMAS", "Management / Data Lake Tap", 1000, 0.5, "OSPF Area 0 Tap", "#64748b"),
    ("NMAS", "Backup Server", "Isolated Replication Link (10.99.99.0/30)", 1000, 0.2, "P2P Backup", "#ef4444"),
    ("S3", "R3", "OSPF Area 0 Transit", 1000, 1.0, "OSPF Area 0", "#38bdf8"),
    ("S4", "R4", "OSPF Area 0 Transit", 1000, 1.0, "OSPF Area 0", "#38bdf8"),
    
    # WAN / BGP Peering
    ("R3", "R5", "eBGP Peering (AS 65001 - AS 65005)", 10000, 2.5, "eBGP AS 65001/65005", "#34d399"),
    ("R4", "R5", "eBGP Peering (AS 65001 - AS 65005)", 10000, 2.5, "eBGP AS 65001/65005", "#34d399"),
    ("R5", "Web Server", "Public DMZ Transit (198.51.100.0/24)", 10000, 0.4, "Connected WAN", "#64748b"),

    # --- NEW LINKS HIGHLIGHTING ROUTING PROTOCOLS ---
    # OSPF Area 10: R4 <-> R6
    ("R4", "R6", "OSPF Area 10 Transit (10.46.46.0/24)", 1000, 1.0, "OSPF Area 10", "#00e5ff"),
    # OSPF Area 20: R6 <-> R7 & R7 <-> H5
    ("R6", "R7", "OSPF Area 20 Transit (10.67.67.0/24)", 1000, 1.0, "OSPF Area 20", "#fb923c"),
    ("R7", "H5", "VLAN 10 Sub-Interface (10.70.10.1/24)", 1000, 0.5, "OSPF Area 20 Access", "#fdba74"),

    # OSPF Area 30: R2 <-> R8 & R8 <-> S5 <-> H6/H7
    ("R2", "R8", "OSPF Area 30 Transit (10.28.28.0/24)", 1000, 1.0, "OSPF Area 30", "#e879f9"),
    ("R8", "S5", "802.1Q Trunk / VLAN 10 GW (10.80.10.1/24)", 1000, 0.8, "OSPF Area 30 Subnet", "#f0abfc"),
    ("S5", "H6", "Access VLAN 10 (10.80.10.106/24)", 1000, 0.5, "L2 Access VLAN 10", "#d8b4fe"),
    ("S5", "H7", "Access VLAN 10 (10.80.10.107/24)", 1000, 0.5, "L2 Access VLAN 10", "#d8b4fe"),
]

for u, v, ltype, cap, lat, pdom, lcol in links:
    G.add_edge(u, v, link_type=ltype, capacity=cap, latency=lat, protocol=pdom, color=lcol)

# 2. Define Dynamic Traffic Flows (Highlighting New Multi-Area Protocol Paths)
traffic_flows = [
    {
        "id": "flow_h1_web",
        "name": "Flow 1: H1 to Web Server (RIPv2 -> OSPF A0 -> BGP)",
        "protocol": "HTTP / TCP 80",
        "source": "H1",
        "destination": "Web Server",
        "path": ["H1", "S1", "R1", "S3", "R3", "R5", "Web Server"],
        "color": "#00e676", # Vibrant Green
        "rate_mbps": 125,
        "description": "Legacy VLAN 10 client traversing RIPv2 -> OSPF Area 0 -> eBGP to Web Server."
    },
    {
        "id": "flow_h2_web",
        "name": "Flow 2: H2 to Web Server (Inter-VLAN / DHCP)",
        "protocol": "HTTPS / TCP 443",
        "source": "H2",
        "destination": "Web Server",
        "path": ["H2", "S1", "S2", "R2", "S4", "R4", "R5", "Web Server"],
        "color": "#00b0ff", # Bright Blue
        "rate_mbps": 85,
        "description": "VLAN 20 client routed via Distribution R2 across ASBR R4 to public Web Server."
    },
    {
        "id": "flow_h4_ipv6",
        "name": "Flow 3: H4 IPv6 Traffic to Web Server",
        "protocol": "IPv6 HTTP / TCP 80",
        "source": "H4",
        "destination": "Web Server",
        "path": ["H4", "S2", "R2", "S4", "S3", "R3", "R5", "Web Server"],
        "color": "#d500f9", # Magenta / Purple
        "rate_mbps": 60,
        "description": "Native dual-stack IPv6 flow from Host 4 (2001:db8:30::104) to Web Server (2001:db8:100::10)."
    },
    {
        "id": "flow_h5_r7_web",
        "name": "Flow 4: NEW Host H5 to Web Server (OSPF Area 20 -> 10 -> BGP)",
        "protocol": "HTTP / TCP 80 (OSPF Multi-Area)",
        "source": "H5",
        "destination": "Web Server",
        "path": ["H5", "R7", "R6", "R4", "R5", "Web Server"],
        "color": "#ff6d00", # Vivid Orange
        "rate_mbps": 110,
        "description": "Host H5 in VLAN 10 (10.70.10.105) traversing OSPF Area 20 -> Area 10 -> eBGP to Internet."
    },
    {
        "id": "flow_h6_r8_web",
        "name": "Flow 5: NEW Host H6 to Web Server (OSPF Area 30 -> 0 -> BGP)",
        "protocol": "HTTP / TCP 80 (OSPF Area 30)",
        "source": "H6",
        "destination": "Web Server",
        "path": ["H6", "S5", "R8", "R2", "S4", "R4", "R5", "Web Server"],
        "color": "#e040fb", # Bright Violet
        "rate_mbps": 115,
        "description": "Host H6 in VLAN 10 (10.80.10.106) routed via Switch S5 -> R8 in OSPF Area 30 -> R2 ABR -> Internet."
    },
    {
        "id": "flow_inter_area_h6_h5",
        "name": "Flow 6: NEW Inter-Area Mesh H6 (Area 30) <-> H5 (Area 20)",
        "protocol": "ICMP / Multi-Area Mesh",
        "source": "H6",
        "destination": "H5",
        "path": ["H6", "S5", "R8", "R2", "S4", "R4", "R6", "R7", "H5"],
        "color": "#76ff03", # Neon Lime
        "rate_mbps": 95,
        "description": "Direct Inter-Area routing across OSPF Area 30 -> Area 0 -> Area 10 -> Area 20."
    },
    {
        "id": "flow_nmas_telemetry",
        "name": "Flow 7: NMAS Telemetry Ingestion (R6, R7, R8, S5 Streaming)",
        "protocol": "gRPC / gNMI + SNMP",
        "source": "R8",
        "destination": "NMAS",
        "path": ["R8", "R2", "S4", "S3", "NMAS"],
        "color": "#ffab00", # Amber
        "rate_mbps": 50,
        "description": "Unified telemetry streaming from all new devices (R6, R7, R8, S5) into InfluxDB data lake."
    },
    {
        "id": "flow_nmas_backup",
        "name": "Flow 8: NMAS Data Lake Isolated Backup Replication",
        "protocol": "TCP 9999 (Encrypted Replication)",
        "source": "NMAS",
        "destination": "Backup Server",
        "path": ["NMAS", "Backup Server"],
        "color": "#ff1744", # Red
        "rate_mbps": 350,
        "description": "Out-of-band P2P backup replication across private 10.99.99.0/30 interface."
    }
]

# Color map for node types
NODE_COLORS = {
    "host": "#37474f",
    "switch": "#00838f",
    "router": "#0288d1",
    "pe_router": "#1565c0",
    "server": "#2e7d32",
    "backup": "#c62828",
    "new_router": "#0097a7",  # Distinctive Teal for New Routers
    "new_switch": "#00796b",  # Distinctive Emerald for New Switch
    "new_host": "#455a64",    # Slate Blue for New Hosts
}

# 3. Generate High-Res Static Snapshot Image with Protocol Area Highlights
def generate_snapshot():
    fig, ax = plt.subplots(figsize=(22, 16), dpi=150, facecolor="#0f172a")
    ax.set_facecolor("#0f172a")
    ax.set_xlim(-0.5, 17.5)
    ax.set_ylim(0.0, 16.5)
    ax.axis("off")

    # Master Title & Subtitle Banner
    ax.text(8.5, 16.0, "RoboControl Networks: Multi-Area Enterprise Topology & Traffic Flow Visualizer",
            color="#ffffff", fontsize=20, fontweight="bold", ha="center", va="center", fontfamily="sans-serif")
    ax.text(8.5, 15.5, "NetworkX Graph Model Highlighting OSPF Area 0, Area 10, Area 20, Area 30, BGP & 802.1Q Access Domains",
            color="#38bdf8", fontsize=12, ha="center", va="center")

    pos = nx.get_node_attributes(G, "pos")

    # --- DRAW PROTOCOL AREA SHADING ENCLOSURES ---
    # 1. OSPF Area 0 (Backbone Fabric)
    area0_box = patches.FancyBboxPatch((2.2, 5.8), 6.6, 7.2,
                                       boxstyle="round,pad=0.25,rounding_size=0.4",
                                       facecolor="#1e3a8a", edgecolor="#3b82f6",
                                       linewidth=2.0, linestyle="--", alpha=0.18, zorder=1)
    ax.add_patch(area0_box)
    ax.text(5.5, 8.2, "OSPF Area 0 (Core Backbone Fabric)\nSubnet: 10.0.0.0/24 | 2001:db8:0::/64",
            color="#60a5fa", fontsize=10, fontweight="bold", ha="center", va="center", alpha=0.85, zorder=2)

    # 2. OSPF Area 10 (Branch Interconnect R4 <-> R6)
    area10_box = patches.FancyBboxPatch((6.4, 11.0), 6.0, 2.0,
                                        boxstyle="round,pad=0.2,rounding_size=0.3",
                                        facecolor="#083344", edgecolor="#00e5ff",
                                        linewidth=2.0, linestyle="--", alpha=0.25, zorder=1)
    ax.add_patch(area10_box)
    ax.text(9.4, 13.1, "OSPF Area 10 (10.46.46.0/24)",
            color="#00e5ff", fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=2)

    # 3. OSPF Area 20 (Edge Router R7 & Host H5)
    area20_box = patches.FancyBboxPatch((10.6, 8.4), 5.6, 4.6,
                                        boxstyle="round,pad=0.2,rounding_size=0.3",
                                        facecolor="#451a03", edgecolor="#fb923c",
                                        linewidth=2.0, linestyle="--", alpha=0.25, zorder=1)
    ax.add_patch(area20_box)
    ax.text(13.4, 13.6, "OSPF Area 20 (10.67.67.0/24 & 10.70.10.0/24)\n[New Devices: R6, R7, Host H5]",
            color="#fb923c", fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=2)

    # 4. OSPF Area 30 (Distribution R8, Switch S5, Hosts H6 & H7)
    area30_box = patches.FancyBboxPatch((7.0, 0.8), 8.0, 7.2,
                                        boxstyle="round,pad=0.25,rounding_size=0.4",
                                        facecolor="#3b0764", edgecolor="#e879f9",
                                        linewidth=2.0, linestyle="--", alpha=0.2, zorder=1)
    ax.add_patch(area30_box)
    ax.text(11.0, 8.2, "OSPF Area 30 (10.28.28.0/24 & 10.80.10.0/24)\n[New Devices: R8, Switch S5, Hosts H6/H7]",
            color="#e879f9", fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=2)

    # 5. eBGP Peering Domain (R5 <-> R3/R4)
    bgp_box = patches.FancyBboxPatch((2.6, 11.2), 5.6, 3.8,
                                     boxstyle="round,pad=0.2,rounding_size=0.3",
                                     facecolor="#064e3b", edgecolor="#34d399",
                                     linewidth=1.8, linestyle="-.", alpha=0.18, zorder=1)
    ax.add_patch(bgp_box)
    ax.text(3.8, 14.8, "eBGP Peering Domain\n(AS 65005 ↔ AS 65001)",
            color="#34d399", fontsize=9, fontweight="bold", ha="center", va="center", zorder=2)

    # 6. RIPv2 Legacy Domain
    rip_box = patches.FancyBboxPatch((1.0, 0.8), 7.8, 4.4,
                                     boxstyle="round,pad=0.2,rounding_size=0.3",
                                     facecolor="#581c87", edgecolor="#c084fc",
                                     linewidth=1.5, linestyle=":", alpha=0.15, zorder=1)
    ax.add_patch(rip_box)
    ax.text(4.9, 3.2, "RIPv2 & VRRP Legacy Access Domain",
            color="#c084fc", fontsize=8.5, fontstyle="italic", ha="center", va="center", zorder=2)

    # Draw Physical Links (Base Layer)
    for u, v, data in G.edges(data=True):
        p1 = pos[u]
        p2 = pos[v]
        lcol = data.get("color", "#334155")
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=lcol, lw=3.0, zorder=3, linestyle="-")

    # Overlay Dynamic Traffic Flow Lines with Offsets & Colors
    flow_offsets = [0.0, 0.08, -0.08, 0.12, -0.12, 0.16, -0.16, 0.0]
    for idx, flow in enumerate(traffic_flows):
        path = flow["path"]
        col = flow["color"]
        offset = flow_offsets[idx % len(flow_offsets)]

        for i in range(len(path) - 1):
            n1 = path[i]
            n2 = path[i+1]
            p1 = pos[n1]
            p2 = pos[n2]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.hypot(dx, dy)
            if dist == 0:
                continue
            ox = -dy / dist * offset
            oy = dx / dist * offset

            ax.plot([p1[0] + ox, p2[0] + ox], [p1[1] + oy, p2[1] + oy],
                    color=col, lw=3.2, alpha=0.85, zorder=4, solid_capstyle="round")

            # Directional arrow
            mid_x = (p1[0] + p2[0]) / 2 + ox
            mid_y = (p1[1] + p2[1]) / 2 + oy
            ax.annotate("", xy=(mid_x + dx*0.08, mid_y + dy*0.08), xytext=(mid_x - dx*0.08, mid_y - dy*0.08),
                        arrowprops=dict(arrowstyle="->", color=col, lw=2.2, mutation_scale=14), zorder=5)

    # Draw Nodes
    for node, data in G.nodes(data=True):
        x, y = data["pos"]
        ntype = data["type"]
        color = NODE_COLORS.get(ntype, "#64748b")
        is_new = "new" in ntype

        # Node outer halo
        halo_color = "#38bdf8" if is_new else color
        glow = plt.Circle((x, y), 0.58, color=halo_color, alpha=0.35 if is_new else 0.2, zorder=6)
        ax.add_patch(glow)

        # Node main circle
        circle = plt.Circle((x, y), 0.42, color=color, ec="#ffffff" if is_new else "#94a3b8", lw=2.2 if is_new else 1.4, zorder=7)
        ax.add_patch(circle)

        # NEW Badge indicator for new devices
        if is_new:
            new_badge = patches.FancyBboxPatch((x + 0.15, y + 0.2), 0.5, 0.22,
                                               boxstyle="round,pad=0.04",
                                               facecolor="#e11d48", edgecolor="#ffffff", lw=1.0, zorder=10)
            ax.add_patch(new_badge)
            ax.text(x + 0.4, y + 0.31, "NEW", color="#ffffff", fontsize=6, fontweight="bold", ha="center", va="center", zorder=11)

        # Node Name & Labels
        ax.text(x, y, node, color="#ffffff", fontsize=8.5, fontweight="bold", ha="center", va="center", zorder=8)
        ax.text(x, y - 0.58, data["label"], color="#e2e8f0", fontsize=7.5, fontweight="bold", ha="center", va="top", zorder=8)
        ax.text(x, y - 0.78, data["ip"], color="#38bdf8", fontsize=6.8, ha="center", va="top", zorder=8)
        
        # Highlighting Protocol in Node Cards
        proto_color = "#f59e0b" if "OSPF" in data.get("protocol", "") else "#a7f3d0"
        ax.text(x, y - 0.96, f"[{data.get('protocol', '')}]", color=proto_color, fontsize=6.2, fontweight="bold", ha="center", va="top", zorder=8)

    # --- BOTTOM LEGEND & METRICS PANEL ---
    legend_y = 0.55
    ax.add_patch(patches.Rectangle((-0.3, -0.1), 17.8, 1.4, facecolor="#1e293b", edgecolor="#334155", lw=1.5, zorder=9))

    ax.text(0.1, legend_y + 0.45, "ACTIVE MULTI-AREA TRAFFIC FLOWS (NetworkX Simulated):", color="#f8fafc", fontsize=9, fontweight="bold", zorder=10)

    # Multi-column flow listing
    col_x = [0.1, 4.4, 8.8, 13.0, 0.1, 4.4, 8.8, 13.0]
    col_y = [legend_y + 0.12, legend_y + 0.12, legend_y + 0.12, legend_y + 0.12,
             legend_y - 0.25, legend_y - 0.25, legend_y - 0.25, legend_y - 0.25]

    for i, flow in enumerate(traffic_flows):
        cx = col_x[i]
        cy = col_y[i]
        ax.plot([cx, cx + 0.35], [cy + 0.05, cy + 0.05], color=flow["color"], lw=4, zorder=10)
        ax.text(cx + 0.45, cy + 0.05, f"{flow['name'].split(':')[0]} ({flow['rate_mbps']}M)",
                color="#cbd5e1", fontsize=7.2, va="center", zorder=10)

    snapshot_path = os.path.join(REPORTS_DIR, "traffic_flow_snapshot.png")
    plt.tight_layout()
    plt.savefig(snapshot_path, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close()
    print(f"[NetworkX] High-res snapshot saved to {snapshot_path}")

# 4. Generate Dynamic Animated GIF
def generate_animated_gif():
    pos = nx.get_node_attributes(G, "pos")
    frames = []
    num_frames = 24

    for frame_idx in range(num_frames):
        fig, ax = plt.subplots(figsize=(16, 11), dpi=100, facecolor="#0b132b")
        ax.set_facecolor("#0b132b")
        ax.set_xlim(-0.5, 17.5)
        ax.set_ylim(0.2, 16.0)
        ax.axis("off")

        # Title Banner
        ax.text(8.5, 15.4, "Real-Time Multi-Area Traffic Flow Simulation (OSPF Areas 0/10/20/30 & BGP)",
                color="#ffffff", fontsize=15, fontweight="bold", ha="center", fontfamily="sans-serif")
        ax.text(8.5, 14.9, f"Frame {frame_idx+1}/{num_frames} | Showing R6, R7, R8, S5, H5, H6, H7 Multi-Area Packet Flow",
                color="#00e5ff", fontsize=9.5, ha="center")

        # Draw Base Links
        for u, v, data in G.edges(data=True):
            p1 = pos[u]
            p2 = pos[v]
            lcol = data.get("color", "#1c2541")
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=lcol, lw=2.6, alpha=0.6, zorder=1)

        # Draw Dynamic Flow Pulses & Moving Packet Particles
        for flow_idx, flow in enumerate(traffic_flows):
            path = flow["path"]
            col = flow["color"]
            n_segments = len(path) - 1

            for i in range(n_segments):
                p1 = pos[path[i]]
                p2 = pos[path[i+1]]
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=2.0, alpha=0.4, zorder=2)

            total_progress = (frame_idx / num_frames + flow_idx * 0.15) % 1.0
            seg_idx = int(total_progress * n_segments)
            seg_progress = (total_progress * n_segments) - seg_idx

            p_start = pos[path[seg_idx]]
            p_end = pos[path[seg_idx + 1]]

            packet_x = p_start[0] + (p_end[0] - p_start[0]) * seg_progress
            packet_y = p_start[1] + (p_end[1] - p_start[1]) * seg_progress

            packet_glow = plt.Circle((packet_x, packet_y), 0.26, color=col, alpha=0.75, zorder=4)
            ax.add_patch(packet_glow)
            packet_core = plt.Circle((packet_x, packet_y), 0.12, color="#ffffff", zorder=5)
            ax.add_patch(packet_core)

        # Draw Nodes
        for node, data in G.nodes(data=True):
            x, y = data["pos"]
            ntype = data["type"]
            color = NODE_COLORS.get(ntype, "#4a5568")

            circle = plt.Circle((x, y), 0.38, color=color, ec="#ffffff", lw=1.5, zorder=6)
            ax.add_patch(circle)

            ax.text(x, y, node, color="#ffffff", fontsize=7.5, fontweight="bold", ha="center", va="center", zorder=7)
            ax.text(x, y - 0.55, data["label"], color="#e2e8f0", fontsize=6.8, fontweight="bold", ha="center", va="top", zorder=7)

        # Legend Box
        ax.add_patch(patches.Rectangle((0.0, 0.4), 17.0, 0.9, facecolor="#1c2541", edgecolor="#3a506b", lw=1, zorder=8))
        for idx, flow in enumerate(traffic_flows):
            lx = 0.3 + (idx % 4) * 4.2
            ly = 0.95 if idx < 4 else 0.6
            ax.plot([lx, lx + 0.3], [ly, ly], color=flow["color"], lw=3, zorder=9)
            ax.text(lx + 0.4, ly, f"{flow['name'].split(':')[0]} ({flow['rate_mbps']}M)", color="#cbd5e1", fontsize=6.2, va="center", zorder=9)

        plt.tight_layout()
        fig.canvas.draw()
        img = Image.frombytes('RGBA', fig.canvas.get_width_height(), fig.canvas.buffer_rgba())
        frames.append(img.convert("RGB"))
        plt.close()

    gif_path = os.path.join(REPORTS_DIR, "traffic_flow_dynamic.gif")
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=120, loop=0)
    print(f"[NetworkX] Animated traffic flow GIF saved to {gif_path}")

# 5. Generate Interactive HTML5 Visualizer
def generate_interactive_html():
    nodes_payload = {k: list(v) for k, v in nodes_info.items()}
    links_payload = [[l[0], l[1], l[2], l[5], l[6]] for l in links]

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Multi-Area Dynamic Network Traffic Flow Visualizer (NetworkX)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0b132b;
      color: #e0e1dd;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background: #1c2541;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #3a506b;
    }}
    header h1 {{
      font-size: 1.2rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      background: #00b4d8;
      color: #0b132b;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: bold;
    }}
    .badge-ospf {{
      background: #e879f9;
      color: #1e1b4b;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: bold;
    }}
    .main-container {{
      display: flex;
      flex: 1;
      height: calc(100vh - 60px);
    }}
    .canvas-panel {{
      flex: 1;
      position: relative;
      background: #0b132b;
    }}
    canvas {{
      width: 100%;
      height: 100%;
      display: block;
    }}
    .side-panel {{
      width: 420px;
      background: #1c2541;
      border-left: 2px solid #3a506b;
      padding: 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .card {{
      background: #0b132b;
      border-radius: 8px;
      padding: 14px;
      border: 1px solid #3a506b;
    }}
    .card h3 {{
      font-size: 0.9rem;
      color: #48cae4;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .flow-btn {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 8px 10px;
      margin-bottom: 6px;
      background: #1c2541;
      border: 1px solid #3a506b;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.2s ease;
      text-align: left;
    }}
    .flow-btn:hover, .flow-btn.active {{
      background: #3a506b;
      border-color: #00b4d8;
      transform: translateX(4px);
    }}
    .flow-indicator {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 8px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 6px;
    }}
    .stat-box {{
      background: #1c2541;
      padding: 8px;
      border-radius: 6px;
      border: 1px solid #3a506b;
      text-align: center;
    }}
    .stat-val {{
      font-size: 1.15rem;
      font-weight: bold;
      color: #00b4d8;
    }}
    .stat-label {{
      font-size: 0.68rem;
      color: #90e0ef;
      margin-top: 2px;
    }}
    .btn-group {{
      display: flex;
      gap: 6px;
    }}
    .btn {{
      flex: 1;
      padding: 7px;
      background: #0077b6;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      font-size: 0.78rem;
    }}
    .btn:hover {{ background: #0096c7; }}
    .proto-tag {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.68rem;
      font-weight: bold;
      margin-right: 4px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🌐 Multi-Area Traffic Flow Visualizer <span class="badge">NetworkX Model</span> <span class="badge-ospf">OSPF Areas 0/10/20/30</span></h1>
    <div>
      <a href="http://localhost:3000/d/nmas-noc-master" target="_blank" style="color: #00b4d8; text-decoration: none; font-size: 0.85rem; font-weight: bold; padding: 6px 12px; border: 1px solid #00b4d8; border-radius: 4px;">📊 Open Grafana NOC</a>
    </div>
  </header>

  <div class="main-container">
    <div class="canvas-panel">
      <canvas id="flowCanvas"></canvas>
    </div>

    <div class="side-panel">
      <div class="card">
        <h3>Routing Domains & Protocols</h3>
        <div style="font-size: 0.78rem; line-height: 1.6;">
          <p><span class="proto-tag" style="background:#1e3a8a; color:#93c5fd;">OSPF Area 0</span> Core Backbone (R1-R4, S3-S4)</p>
          <p><span class="proto-tag" style="background:#083344; color:#67e8f9;">OSPF Area 10</span> R4 ↔ R6 (10.46.46.0/24)</p>
          <p><span class="proto-tag" style="background:#451a03; color:#fdba74;">OSPF Area 20</span> R6 ↔ R7 ↔ H5 (10.67.67.0/24, 10.70.10.0/24)</p>
          <p><span class="proto-tag" style="background:#3b0764; color:#f0abfc;">OSPF Area 30</span> R2 ↔ R8 ↔ S5 ↔ H6/H7 (10.28.28.0/24, 10.80.10.0/24)</p>
          <p><span class="proto-tag" style="background:#064e3b; color:#6ee7b7;">eBGP AS 65005/65001</span> R5 ↔ R3, R4</p>
          <p><span class="proto-tag" style="background:#581c87; color:#d8b4fe;">RIPv2 / VRRP</span> Legacy Access VLANs 10, 20, 30</p>
        </div>
      </div>

      <div class="card">
        <h3>Active Traffic Flows</h3>
        <div id="flowButtons"></div>
        <div class="btn-group" style="margin-top: 8px;">
          <button class="btn" id="toggleAllBtn">Show All Flows</button>
          <button class="btn" id="pauseBtn" style="background: #e63946;">Pause / Play</button>
        </div>
      </div>

      <div class="card">
        <h3>Active Flow Details</h3>
        <div id="flowDetails" style="font-size: 0.8rem; line-height: 1.45; color: #cbd5e1;">
          Select a traffic flow to inspect its multi-area routing path and protocol hop breakdown.
        </div>
      </div>

      <div class="card">
        <h3>Topology Metrics</h3>
        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-val">23</div>
            <div class="stat-label">Total Nodes</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">25</div>
            <div class="stat-label">Active Links</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">1,010 Mbps</div>
            <div class="stat-label">Aggregate Load</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">100%</div>
            <div class="stat-label">Graph Health</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const canvas = document.getElementById('flowCanvas');
    const ctx = canvas.getContext('2d');

    const nodes = {json.dumps(nodes_payload)};
    const links = {json.dumps(links_payload)};
    const flows = {json.dumps(traffic_flows)};

    let activeFlowIndex = -1;
    let isPaused = false;
    let animationOffset = 0;

    function resize() {{
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }}
    window.addEventListener('resize', resize);
    resize();

    function getCanvasCoords(gx, gy) {{
      const padX = 50;
      const padY = 50;
      const scaleX = (canvas.width - padX * 2) / 17.5;
      const scaleY = (canvas.height - padY * 2) / 16.5;
      return {{
        x: padX + gx * scaleX,
        y: canvas.height - (padY + gy * scaleY)
      }};
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#0b132b";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw Base Links
      links.forEach(l => {{
        const p1 = getCanvasCoords(nodes[l[0]][0], nodes[l[0]][1]);
        const p2 = getCanvasCoords(nodes[l[1]][0], nodes[l[1]][1]);

        ctx.strokeStyle = l[4] || "#1c2541";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }});

      // Draw Flows and Animated Packets
      flows.forEach((flow, fIdx) => {{
        if (activeFlowIndex !== -1 && activeFlowIndex !== fIdx) return;

        const path = flow.path;
        ctx.strokeStyle = flow.color;
        ctx.lineWidth = activeFlowIndex === fIdx ? 4.5 : 2.5;
        ctx.globalAlpha = activeFlowIndex === fIdx ? 0.95 : 0.6;

        ctx.beginPath();
        for (let i = 0; i < path.length; i++) {{
          const p = getCanvasCoords(nodes[path[i]][0], nodes[path[i]][1]);
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }}
        ctx.stroke();
        ctx.globalAlpha = 1.0;

        // Animate Packets
        const nSegs = path.length - 1;
        const totalProgress = ((animationOffset + fIdx * 0.15) % 1.0);
        const curSeg = Math.min(Math.floor(totalProgress * nSegs), nSegs - 1);
        const segProg = (totalProgress * nSegs) - curSeg;

        const pA = getCanvasCoords(nodes[path[curSeg]][0], nodes[path[curSeg]][1]);
        const pB = getCanvasCoords(nodes[path[curSeg + 1]][0], nodes[path[curSeg + 1]][1]);

        const pktX = pA.x + (pB.x - pA.x) * segProg;
        const pktY = pA.y + (pB.y - pA.y) * segProg;

        const grad = ctx.createRadialGradient(pktX, pktY, 2, pktX, pktY, 10);
        grad.addColorStop(0, '#ffffff');
        grad.addColorStop(0.5, flow.color);
        grad.addColorStop(1, 'transparent');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(pktX, pktY, 10, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(pktX, pktY, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }});

      // Draw Nodes
      Object.keys(nodes).forEach(key => {{
        const n = nodes[key];
        const p = getCanvasCoords(n[0], n[1]);
        const ntype = n[3];

        let col = "#0288d1";
        if (ntype === "host") col = "#37474f";
        else if (ntype === "switch") col = "#00838f";
        else if (ntype === "pe_router") col = "#1565c0";
        else if (ntype === "server") col = "#2e7d32";
        else if (ntype === "backup") col = "#c62828";
        else if (ntype === "new_router") col = "#0097a7";
        else if (ntype === "new_switch") col = "#00796b";
        else if (ntype === "new_host") col = "#455a64";

        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 14, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = ntype.includes("new") ? "#00e5ff" : "#ffffff";
        ctx.lineWidth = ntype.includes("new") ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 10px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(key, p.x, p.y);

        ctx.font = "9px sans-serif";
        ctx.fillStyle = "#90e0ef";
        ctx.fillText(n[4], p.x, p.y + 20);

        ctx.font = "italic 8px sans-serif";
        ctx.fillStyle = "#f59e0b";
        ctx.fillText(n[6] ? n[6].split('/')[0] : "", p.x, p.y + 30);
      }});

      if (!isPaused) {{
        animationOffset += 0.005;
      }}
      requestAnimationFrame(draw);
    }}

    // Setup Flow Buttons
    const btnContainer = document.getElementById('flowButtons');
    flows.forEach((flow, idx) => {{
      const btn = document.createElement('button');
      btn.className = 'flow-btn';
      btn.innerHTML = `<span><span class="flow-indicator" style="background: ${{flow.color}}"></span>${{flow.name.split(':')[0]}}</span> <span style="font-weight:bold; color: #00b4d8;">${{flow.rate_mbps}}M</span>`;
      btn.onclick = () => {{
        activeFlowIndex = idx;
        document.querySelectorAll('.flow-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        updateDetails(flow);
      }};
      btnContainer.appendChild(btn);
    }});

    document.getElementById('toggleAllBtn').onclick = () => {{
      activeFlowIndex = -1;
      document.querySelectorAll('.flow-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('flowDetails').innerHTML = "Displaying all multi-area dynamic traffic flows simultaneously.";
    }};

    document.getElementById('pauseBtn').onclick = () => {{
      isPaused = !isPaused;
    }};

    function updateDetails(f) {{
      document.getElementById('flowDetails').innerHTML = `
        <div style="font-weight:bold; color:#00b4d8; font-size:0.95rem; margin-bottom:6px;">${{f.name}}</div>
        <p><strong>Protocol:</strong> ${{f.protocol}}</p>
        <p><strong>Throughput:</strong> ${{f.rate_mbps}} Mbps</p>
        <p><strong>Source:</strong> ${{f.source}} &rarr; <strong>Destination:</strong> ${{f.destination}}</p>
        <p style="margin-top:6px;"><strong>Network Path:</strong><br><code style="color:#a7f3d0; font-size:0.75rem;">${{f.path.join(' &rarr; ')}}</code></p>
        <p style="margin-top:6px; color:#94a3b8; font-size:0.75rem;">${{f.description}}</p>
      `;
    }}

    draw();
  </script>
</body>
</html>
"""
    html_path = os.path.join(REPORTS_DIR, "dynamic_traffic_flow.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[NetworkX] Interactive HTML visualizer saved to {html_path}")

if __name__ == "__main__":
    print("[NetworkX] Generating dynamic multi-area traffic flow models & visualizations...")
    generate_snapshot()
    generate_animated_gif()
    generate_interactive_html()
    print("[NetworkX] All traffic flow visualization artifacts completed successfully.")
