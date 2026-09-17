#!/usr/bin/env python3
"""
Dynamic Network Traffic Flow Visualization using NetworkX and Matplotlib.
Models the enterprise topology (16 nodes, multi-tier OSPF/BGP/RIP/VLAN architecture)
and visualizes dynamic multi-protocol traffic flows with bandwidth utilization.
"""

import os
import math
import json
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont

REPORTS_DIR = "/home/student/Desktop/lab1/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# 1. Define Topology Graph with NetworkX
G = nx.Graph()

nodes_info = {
    # Node: (x, y, label, node_type, ip, asn/vlan)
    "H1": (2.0, 1.5, "H1 (Host)", "host", "10.10.10.101", "VLAN 10"),
    "H2": (5.0, 1.5, "H2 (Host)", "host", "10.10.20.102", "VLAN 20"),
    "H3": (9.0, 1.5, "H3 (Host)", "host", "10.10.10.103", "VLAN 10"),
    "H4": (12.0, 1.5, "H4 (Host)", "host", "2001:db8:30::104", "VLAN 30 (IPv6)"),
    
    "S1": (3.5, 3.5, "S1 (Access)", "switch", "172.20.20.21", "VLAN 10,20,30"),
    "S2": (10.5, 3.5, "S2 (Access)", "switch", "172.20.20.22", "VLAN 10,20,30"),
    
    "R1": (3.5, 6.0, "R1 (Dist)", "router", "10.0.0.1", "OSPF A0 / RIP"),
    "R2": (10.5, 6.0, "R2 (Dist/DHCP)", "router", "10.0.0.2", "OSPF A0 / RIP / DHCP"),
    
    "NMAS": (0.8, 8.5, "NMAS Station", "server", "10.0.0.100", "Data Lake / Mgmt"),
    "Backup Server": (0.8, 11.0, "Backup Node", "backup", "10.99.99.2", "Dedicated Backup"),
    
    "S3": (4.5, 8.5, "S3 (Core)", "switch", "172.20.20.23", "OSPF Area 0 Bridge"),
    "S4": (9.5, 8.5, "S4 (Core)", "switch", "172.20.20.24", "OSPF Area 0 Bridge"),
    
    "R3": (4.0, 11.0, "R3 (ASBR)", "router", "10.0.0.3", "AS 65001 | OSPF A0"),
    "R4": (10.0, 11.0, "R4 (ASBR)", "router", "10.0.0.4", "AS 65001 | OSPF A0"),
    
    "R5": (7.0, 13.5, "R5 (PE Router)", "pe_router", "172.16.35.2", "BGP AS 65005"),
    "Web Server": (11.5, 13.5, "Web Server", "server", "198.51.100.10", "HTTP / 2001:db8:100::10"),
}

for node, (x, y, label, ntype, ip, extra) in nodes_info.items():
    G.add_node(node, pos=(x, y), label=label, type=ntype, ip=ip, extra=extra)

# Physical/Logical Links (u, v, link_type, capacity_mbps, latency_ms)
links = [
    ("H1", "S1", "Access VLAN 10", 1000, 0.5),
    ("H2", "S1", "Access VLAN 20", 1000, 0.5),
    ("H3", "S2", "Access VLAN 10", 1000, 0.5),
    ("H4", "S2", "Access VLAN 30 (IPv6)", 1000, 0.5),
    ("S1", "S2", "802.1Q Inter-Switch Trunk", 1000, 1.0),
    ("S1", "R1", "802.1Q Router-on-a-Stick", 1000, 0.8),
    ("S2", "R2", "802.1Q Router-on-a-Stick", 1000, 0.8),
    ("R1", "S3", "OSPF Area 0 Transit", 1000, 1.2),
    ("R2", "S4", "OSPF Area 0 Transit", 1000, 1.2),
    ("S3", "S4", "Core Inter-Switch Link", 10000, 0.3),
    ("S3", "NMAS", "Management / Data Lake Tap", 1000, 0.5),
    ("NMAS", "Backup Server", "Isolated Replication Link (10.99.99.0/30)", 1000, 0.2),
    ("S3", "R3", "OSPF Area 0 Transit", 1000, 1.0),
    ("S4", "R4", "OSPF Area 0 Transit", 1000, 1.0),
    ("R3", "R5", "eBGP Peering (AS 65001 - AS 65005)", 10000, 2.5),
    ("R4", "R5", "eBGP Peering (AS 65001 - AS 65005)", 10000, 2.5),
    ("R5", "Web Server", "Public DMZ Transit (198.51.100.0/24)", 10000, 0.4),
]

for u, v, ltype, cap, lat in links:
    G.add_edge(u, v, link_type=ltype, capacity=cap, latency=lat)

# 2. Define Dynamic Traffic Flows
traffic_flows = [
    {
        "id": "flow_h1_web",
        "name": "Flow 1: Host H1 to Web Server (HTTP IPv4)",
        "protocol": "HTTP / TCP 80",
        "source": "H1",
        "destination": "Web Server",
        "path": ["H1", "S1", "R1", "S3", "R3", "R5", "Web Server"],
        "color": "#00e676", # Vibrant Green
        "rate_mbps": 125,
        "description": "User browsing production web application over RIPv2 -> OSPF -> BGP path."
    },
    {
        "id": "flow_h2_web",
        "name": "Flow 2: Host H2 to Web Server (Inter-VLAN / DHCP)",
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
        "name": "Flow 3: Host H4 IPv6 Traffic to Web Server",
        "protocol": "IPv6 HTTP / TCP 80",
        "source": "H4",
        "destination": "Web Server",
        "path": ["H4", "S2", "R2", "S4", "S3", "R3", "R5", "Web Server"],
        "color": "#d500f9", # Magenta / Purple
        "rate_mbps": 60,
        "description": "Native dual-stack IPv6 flow from Host 4 (2001:db8:30::104) to Web Server (2001:db8:100::10)."
    },
    {
        "id": "flow_nmas_telemetry",
        "name": "Flow 4: NMAS Ingestion (SNMP, Syslog, gRPC Streaming)",
        "protocol": "gRPC / gNMI + SNMP + Syslog",
        "source": "R5",
        "destination": "NMAS",
        "path": ["R5", "R3", "S3", "NMAS"],
        "color": "#ffab00", # Amber / Orange
        "rate_mbps": 45,
        "description": "Continuous telemetry streaming and syslog event ingestion to NMAS Data Lake."
    },
    {
        "id": "flow_nmas_backup",
        "name": "Flow 5: Data Lake Isolated Replication to Backup Server",
        "protocol": "TCP 9999 (Encrypted Datalake Sync)",
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
    "backup": "#c62828"
}

NODE_ICONS = {
    "host": "💻",
    "switch": "🔀",
    "router": "🌐",
    "pe_router": "📡",
    "server": "🖥️",
    "backup": "💾"
}

# 3. Generate High-Res Static Snapshot Image
def generate_snapshot():
    fig, ax = plt.subplots(figsize=(18, 12), dpi=150, facecolor="#0f172a")
    ax.set_facecolor("#0f172a")
    ax.set_xlim(-0.5, 14.5)
    ax.set_ylim(0.0, 15.5)
    ax.axis("off")

    # Title & Legend Box
    ax.text(7.0, 14.8, "Enterprise Network Topology & Multi-Protocol Dynamic Traffic Flows",
            color="#ffffff", fontsize=18, fontweight="bold", ha="center", va="center",
            fontfamily="sans-serif")
    ax.text(7.0, 14.3, "Simulated Real-Time Paths with NetworkX Graph Model & Bandwidth Allocation",
            color="#94a3b8", fontsize=11, ha="center", va="center")

    pos = nx.get_node_attributes(G, "pos")

    # Draw Physical Links (Base Layer)
    for u, v in G.edges():
        p1 = pos[u]
        p2 = pos[v]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#334155", lw=3.0, zorder=1, linestyle="-")

    # Overlay Dynamic Traffic Flow Lines with Offsets & Colors
    flow_offsets = [0.0, 0.08, -0.08, 0.14, 0.0]
    for idx, flow in enumerate(traffic_flows):
        path = flow["path"]
        col = flow["color"]
        offset = flow_offsets[idx]
        
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
            # Perpendicular vector for offset
            ox = -dy / dist * offset
            oy = dx / dist * offset

            ax.plot([p1[0] + ox, p2[0] + ox], [p1[1] + oy, p2[1] + oy],
                    color=col, lw=3.5, alpha=0.85, zorder=2, solid_capstyle="round")

            # Draw directional arrows
            mid_x = (p1[0] + p2[0]) / 2 + ox
            mid_y = (p1[1] + p2[1]) / 2 + oy
            ax.annotate("", xy=(mid_x + dx*0.1, mid_y + dy*0.1), xytext=(mid_x - dx*0.1, mid_y - dy*0.1),
                        arrowprops=dict(arrowstyle="->", color=col, lw=2.5, mutation_scale=15), zorder=3)

    # Draw Nodes
    for node, data in G.nodes(data=True):
        x, y = data["pos"]
        ntype = data["type"]
        color = NODE_COLORS.get(ntype, "#64748b")

        # Outer glow circle
        glow = plt.Circle((x, y), 0.65, color=color, alpha=0.25, zorder=4)
        ax.add_patch(glow)
        # Inner node body
        circle = plt.Circle((x, y), 0.48, color=color, ec="#ffffff", lw=1.8, zorder=5)
        ax.add_patch(circle)

        # Node Name & Details
        ax.text(x, y, node, color="#ffffff", fontsize=9, fontweight="bold", ha="center", va="center", zorder=6)
        ax.text(x, y - 0.72, data["label"], color="#e2e8f0", fontsize=8, fontweight="bold", ha="center", va="top", zorder=6)
        ax.text(x, y - 0.95, data["ip"], color="#38bdf8", fontsize=7, ha="center", va="top", zorder=6)
        if data.get("extra"):
            ax.text(x, y - 1.15, data["extra"], color="#94a3b8", fontsize=6.5, ha="center", va="top", zorder=6)

    # Bottom Legend Box
    legend_y = 0.5
    ax.add_patch(patches.Rectangle((-0.2, -0.1), 14.8, 1.4, facecolor="#1e293b", edgecolor="#334155", lw=1.5, zorder=7))
    
    ax.text(0.2, legend_y + 0.4, "ACTIVE TRAFFIC FLOWS (NetworkX Simulated):", color="#f8fafc", fontsize=9, fontweight="bold", zorder=8)
    
    col_x = [0.2, 5.0, 10.0, 0.2, 5.0]
    col_y = [legend_y, legend_y, legend_y, legend_y - 0.35, legend_y - 0.35]
    
    for i, flow in enumerate(traffic_flows):
        cx = col_x[i]
        cy = col_y[i]
        ax.plot([cx, cx + 0.4], [cy + 0.05, cy + 0.05], color=flow["color"], lw=4, zorder=8)
        ax.text(cx + 0.5, cy + 0.05, f"{flow['name']} ({flow['rate_mbps']} Mbps)", color="#cbd5e1", fontsize=7.5, va="center", zorder=8)

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
        fig, ax = plt.subplots(figsize=(14, 9.5), dpi=100, facecolor="#0b132b")
        ax.set_facecolor("#0b132b")
        ax.set_xlim(-0.5, 14.0)
        ax.set_ylim(0.2, 15.0)
        ax.axis("off")

        # Title Banner
        ax.text(6.8, 14.4, "Real-Time Multi-Protocol Traffic Flow Simulation",
                color="#ffffff", fontsize=15, fontweight="bold", ha="center", fontfamily="sans-serif")
        t_phase = (frame_idx / num_frames) * 2 * math.pi
        pulse_alpha = 0.5 + 0.4 * math.sin(t_phase)
        ax.text(6.8, 13.9, f"Frame {frame_idx+1}/{num_frames} | Live Telemetry & Packet Movement Active",
                color="#00e5ff", fontsize=9, ha="center")

        # Draw Base Links
        for u, v in G.edges():
            p1 = pos[u]
            p2 = pos[v]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#1c2541", lw=2.8, zorder=1)

        # Draw Dynamic Flow Pulses & Moving Packet Particles
        for flow_idx, flow in enumerate(traffic_flows):
            path = flow["path"]
            col = flow["color"]
            n_segments = len(path) - 1

            # Base flow path
            for i in range(n_segments):
                p1 = pos[path[i]]
                p2 = pos[path[i+1]]
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=2.2, alpha=0.45, zorder=2)

            # Calculate packet position along total path length
            total_progress = (frame_idx / num_frames + flow_idx * 0.22) % 1.0
            seg_idx = int(total_progress * n_segments)
            seg_progress = (total_progress * n_segments) - seg_idx
            
            p_start = pos[path[seg_idx]]
            p_end = pos[path[seg_idx + 1]]

            packet_x = p_start[0] + (p_end[0] - p_start[0]) * seg_progress
            packet_y = p_start[1] + (p_end[1] - p_start[1]) * seg_progress

            # Draw Glowing Animated Packet
            packet_glow = plt.Circle((packet_x, packet_y), 0.28, color=col, alpha=0.75, zorder=4)
            ax.add_patch(packet_glow)
            packet_core = plt.Circle((packet_x, packet_y), 0.14, color="#ffffff", zorder=5)
            ax.add_patch(packet_core)

        # Draw Nodes
        for node, data in G.nodes(data=True):
            x, y = data["pos"]
            ntype = data["type"]
            color = NODE_COLORS.get(ntype, "#4a5568")

            # Static node circle
            circle = plt.Circle((x, y), 0.42, color=color, ec="#ffffff", lw=1.5, zorder=6)
            ax.add_patch(circle)

            ax.text(x, y, node, color="#ffffff", fontsize=8, fontweight="bold", ha="center", va="center", zorder=7)
            ax.text(x, y - 0.65, data["label"], color="#e2e8f0", fontsize=7, fontweight="bold", ha="center", va="top", zorder=7)

        # In-frame Legend
        ax.add_patch(patches.Rectangle((0.0, 0.4), 13.5, 0.9, facecolor="#1c2541", edgecolor="#3a506b", lw=1, zorder=8))
        for idx, flow in enumerate(traffic_flows):
            lx = 0.3 + (idx % 3) * 4.4
            ly = 1.0 if idx < 3 else 0.6
            ax.plot([lx, lx + 0.3], [ly, ly], color=flow["color"], lw=3, zorder=9)
            ax.text(lx + 0.4, ly, f"{flow['name'].split(':')[0]} ({flow['rate_mbps']}M)", color="#cbd5e1", fontsize=6.5, va="center", zorder=9)

        plt.tight_layout()
        
        # Save temp frame buffer
        fig.canvas.draw()
        img = Image.frombytes('RGBA', fig.canvas.get_width_height(), fig.canvas.buffer_rgba())
        frames.append(img.convert("RGB"))
        plt.close()

    gif_path = os.path.join(REPORTS_DIR, "traffic_flow_dynamic.gif")
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=120, loop=0)
    print(f"[NetworkX] Animated traffic flow GIF saved to {gif_path}")

# 5. Generate Interactive HTML5 Visualizer
def generate_interactive_html():
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dynamic Network Traffic Flow Visualizer (NetworkX)</title>
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
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #3a506b;
    }}
    header h1 {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      background: #00b4d8;
      color: #0b132b;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: bold;
    }}
    .main-container {{
      display: flex;
      flex: 1;
      height: calc(100vh - 65px);
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
      width: 380px;
      background: #1c2541;
      border-left: 2px solid #3a506b;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}
    .card {{
      background: #0b132b;
      border-radius: 8px;
      padding: 14px;
      border: 1px solid #3a506b;
    }}
    .card h3 {{
      font-size: 0.95rem;
      color: #48cae4;
      margin-bottom: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .flow-btn {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 10px 12px;
      margin-bottom: 8px;
      background: #1c2541;
      border: 1px solid #3a506b;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s ease;
      text-align: left;
    }}
    .flow-btn:hover, .flow-btn.active {{
      background: #3a506b;
      border-color: #00b4d8;
      transform: translateX(4px);
    }}
    .flow-indicator {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 8px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 8px;
    }}
    .stat-box {{
      background: #1c2541;
      padding: 10px;
      border-radius: 6px;
      border: 1px solid #3a506b;
      text-align: center;
    }}
    .stat-val {{
      font-size: 1.25rem;
      font-weight: bold;
      color: #00b4d8;
    }}
    .stat-label {{
      font-size: 0.7rem;
      color: #90e0ef;
      margin-top: 4px;
    }}
    .btn-group {{
      display: flex;
      gap: 8px;
    }}
    .btn {{
      flex: 1;
      padding: 8px;
      background: #0077b6;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      font-size: 0.8rem;
    }}
    .btn:hover {{ background: #0096c7; }}
  </style>
</head>
<body>
  <header>
    <h1>🌐 Dynamic Network Traffic Flow Visualizer <span class="badge">NetworkX Model</span></h1>
    <div>
      <a href="http://localhost:3000" target="_blank" style="color: #00b4d8; text-decoration: none; font-size: 0.85rem; font-weight: bold; padding: 6px 12px; border: 1px solid #00b4d8; border-radius: 4px;">📊 Open Grafana NOC Dashboard</a>
    </div>
  </header>

  <div class="main-container">
    <div class="canvas-panel">
      <canvas id="flowCanvas"></canvas>
    </div>

    <div class="side-panel">
      <div class="card">
        <h3>Traffic Flows</h3>
        <div id="flowButtons"></div>
        <div class="btn-group" style="margin-top: 10px;">
          <button class="btn" id="toggleAllBtn">Show All Flows</button>
          <button class="btn" id="pauseBtn" style="background: #e63946;">Pause / Play</button>
        </div>
      </div>

      <div class="card">
        <h3>Active Flow Details</h3>
        <div id="flowDetails" style="font-size: 0.85rem; line-height: 1.5; color: #cbd5e1;">
          Select a flow to inspect routing path, protocol, and throughput.
        </div>
      </div>

      <div class="card">
        <h3>Network Topology Metrics</h3>
        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-val">16</div>
            <div class="stat-label">Total Nodes</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">17</div>
            <div class="stat-label">Active Links</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">665 Mbps</div>
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

    const nodes = {json.dumps(nodes_info)};
    const links = {json.dumps(links)};
    const flows = {json.dumps(traffic_flows)};

    let activeFlowIndex = -1; // -1 means all
    let isPaused = false;
    let animationOffset = 0;

    function resize() {{
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }}
    window.addEventListener('resize', resize);
    resize();

    // Map graph coordinates to canvas
    function getCanvasCoords(gx, gy) {{
      const padX = 60;
      const padY = 60;
      const scaleX = (canvas.width - padX * 2) / 14.0;
      const scaleY = (canvas.height - padY * 2) / 15.0;
      return {{
        x: padX + gx * scaleX,
        y: canvas.height - (padY + gy * scaleY)
      }};
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw Grid / Stars Background
      ctx.fillStyle = "#0b132b";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw Base Links
      links.forEach(l => {{
        const p1 = getCanvasCoords(nodes[l[0]][0], nodes[l[0]][1]);
        const p2 = getCanvasCoords(nodes[l[1]][0], nodes[l[1]][1]);

        ctx.strokeStyle = "#1c2541";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }});

      // Draw Flows and Animated Particles
      flows.forEach((flow, fIdx) => {{
        if (activeFlowIndex !== -1 && activeFlowIndex !== fIdx) return;

        const path = flow.path;
        ctx.strokeStyle = flow.color;
        ctx.lineWidth = activeFlowIndex === fIdx ? 4.5 : 2.5;
        ctx.globalAlpha = activeFlowIndex === fIdx ? 0.9 : 0.6;

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
        const totalProgress = ((animationOffset + fIdx * 0.2) % 1.0);
        const curSeg = Math.min(Math.floor(totalProgress * nSegs), nSegs - 1);
        const segProg = (totalProgress * nSegs) - curSeg;

        const pA = getCanvasCoords(nodes[path[curSeg]][0], nodes[path[curSeg]][1]);
        const pB = getCanvasCoords(nodes[path[curSeg + 1]][0], nodes[path[curSeg + 1]][1]);

        const pktX = pA.x + (pB.x - pA.x) * segProg;
        const pktY = pA.y + (pB.y - pA.y) * segProg;

        // Glow
        const grad = ctx.createRadialGradient(pktX, pktY, 2, pktX, pktY, 12);
        grad.addColorStop(0, '#ffffff');
        grad.addColorStop(0.4, flow.color);
        grad.addColorStop(1, 'transparent');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(pktX, pktY, 12, 0, Math.PI * 2);
        ctx.fill();

        // Core
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(pktX, pktY, 3, 0, Math.PI * 2);
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

        // Outer circle
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 16, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(key, p.x, p.y);

        // Subtext
        ctx.font = "10px sans-serif";
        ctx.fillStyle = "#90e0ef";
        ctx.fillText(n[4], p.x, p.y + 24);
      }});

      if (!isPaused) {{
        animationOffset += 0.006;
      }}
      requestAnimationFrame(draw);
    }}

    // UI Buttons
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
      document.getElementById('flowDetails').innerHTML = "Displaying all multi-protocol dynamic traffic flows simultaneously.";
    }};

    document.getElementById('pauseBtn').onclick = () => {{
      isPaused = !isPaused;
    }};

    function updateDetails(f) {{
      document.getElementById('flowDetails').innerHTML = `
        <div style="font-weight:bold; color:#00b4d8; font-size:1rem; margin-bottom:6px;">${{f.name}}</div>
        <p><strong>Protocol:</strong> ${{f.protocol}}</p>
        <p><strong>Throughput:</strong> ${{f.rate_mbps}} Mbps</p>
        <p><strong>Source:</strong> ${{f.source}} &rarr; <strong>Destination:</strong> ${{f.destination}}</p>
        <p style="margin-top:6px;"><strong>Network Path:</strong><br><code style="color:#a7f3d0;">${{f.path.join(' &rarr; ')}}</code></p>
        <p style="margin-top:6px; color:#94a3b8;">${{f.description}}</p>
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
    print("[NetworkX] Generating dynamic traffic flow models & visualizations...")
    generate_snapshot()
    generate_animated_gif()
    generate_interactive_html()
    print("[NetworkX] All traffic flow visualization artifacts completed successfully.")
