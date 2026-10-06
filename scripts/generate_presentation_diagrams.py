#!/usr/bin/env python3
"""
Generates visual diagrams and charts for the PowerPoint presentation slides.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = "/home/student/Desktop/lab1/reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set global matplotlib styles
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

def create_datalake_diagram():
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    fig.patch.set_facecolor('#0F172A')
    ax.set_facecolor('#0F172A')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 94, "NMAS Observability & InfluxDB Data Lake Architecture", 
            fontsize=15, fontweight='bold', color='#38BDF8', ha='center')

    # Box 1: Monitored Nodes (Left)
    rect1 = patches.FancyBboxPatch((4, 25), 26, 60, boxstyle="round,pad=1.5", 
                                  facecolor='#1E293B', edgecolor='#06B6D4', linewidth=2)
    ax.add_patch(rect1)
    ax.text(17, 80, "Network Fabric", fontsize=12, fontweight='bold', color='#38BDF8', ha='center')
    ax.text(17, 74, "(16 Live Nodes)", fontsize=10, color='#94A3B8', ha='center')
    nodes = ["Routers R1 - R5", "(Arista cEOS 4.33)", "", "Switches S1 - S4", "(Arista cEOS 4.33)", "", "Hosts H1 - H4", "Web Server (DMZ)"]
    y_pos = 66
    for n in nodes:
        if n:
            ax.text(17, y_pos, n, fontsize=9, color='#F1F5F9' if "(" not in n else '#94A3B8', ha='center')
        y_pos -= 4.2

    # Box 2: NMAS Station & Collector Engine (Center)
    rect2 = patches.FancyBboxPatch((37, 20), 30, 68, boxstyle="round,pad=1.5", 
                                  facecolor='#1E293B', edgecolor='#10B981', linewidth=2)
    ax.add_patch(rect2)
    ax.text(52, 83, "NMAS Management Station", fontsize=12, fontweight='bold', color='#34D399', ha='center')
    ax.text(52, 78, "IP: 172.20.20.100", fontsize=9, color='#94A3B8', ha='center')
    
    # Sub-box: Telegraf & Collector
    sub1 = patches.FancyBboxPatch((39, 52), 26, 20, boxstyle="round,pad=0.8", 
                                 facecolor='#0F172A', edgecolor='#334155', linewidth=1.5)
    ax.add_patch(sub1)
    ax.text(52, 67, "Telegraf Ingest Engine", fontsize=10, fontweight='bold', color='#38BDF8', ha='center')
    ax.text(52, 61, "• SNMP Polling (CPU, Octets)\n• gRPC Streaming Telemetry\n• ICMP Ping Health Checks", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    # Sub-box: Primary InfluxDB
    sub2 = patches.FancyBboxPatch((39, 25), 26, 22, boxstyle="round,pad=0.8", 
                                 facecolor='#0F172A', edgecolor='#10B981', linewidth=1.5)
    ax.add_patch(sub2)
    ax.text(52, 41, "Primary InfluxDB Data Lake", fontsize=10, fontweight='bold', color='#34D399', ha='center')
    ax.text(52, 35, "• Database: 'nmas_datalake'\n• Retention: 7 Days (autogen)\n• Automated Log Cleanup", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    # Box 3: Secondary Backup Node (Right)
    rect3 = patches.FancyBboxPatch((74, 25), 22, 60, boxstyle="round,pad=1.5", 
                                  facecolor='#1E293B', edgecolor='#F59E0B', linewidth=2)
    ax.add_patch(rect3)
    ax.text(85, 80, "Isolated Backup Node", fontsize=11, fontweight='bold', color='#FBBF24', ha='center')
    ax.text(85, 74, "IP: 172.20.20.150", fontsize=9, color='#94A3B8', ha='center')
    
    b_items = ["Secondary Data Lake", "Secure Storage Target", "", "• NMAS Access Only", "• 7-Day Backup Policy", "• Automated Snapshots", "• Offline Archive"]
    y_pos = 66
    for b in b_items:
        if b:
            ax.text(85, y_pos, b, fontsize=8.5, color='#F1F5F9' if "•" not in b else '#CBD5E1', ha='center')
        y_pos -= 4.5

    # Arrows
    # Fabric -> NMAS
    ax.annotate("", xy=(37, 62), xytext=(30, 62),
                arrowprops=dict(arrowstyle="->", color="#06B6D4", lw=2.5))
    ax.text(33.5, 65, "SNMP/gRPC", fontsize=8, color="#06B6D4", ha="center")

    # NMAS -> Backup
    ax.annotate("", xy=(74, 55), xytext=(67, 55),
                arrowprops=dict(arrowstyle="->", color="#F59E0B", lw=2.5))
    ax.text(70.5, 58, "Backup Sync", fontsize=8, color="#F59E0B", ha="center")

    # Footer note
    ax.text(50, 7, "🔒 Isolated Secondary Data Lake strictly accessible only by NMAS management plane", 
            fontsize=9.5, color='#94A3B8', ha='center', style='italic')

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "slide3_datalake_diagram.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Created:", out_path)

def create_nsot_diagram():
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    fig.patch.set_facecolor('#0F172A')
    ax.set_facecolor('#0F172A')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 94, "Django Network Source of Truth (NSoT) & Automation Framework", 
            fontsize=14, fontweight='bold', color='#38BDF8', ha='center')

    # Feature 1: Inventory & Dynamic Provisioning
    f1 = patches.FancyBboxPatch((4, 52), 43, 36, boxstyle="round,pad=1.2", 
                               facecolor='#1E293B', edgecolor='#06B6D4', linewidth=1.8)
    ax.add_patch(f1)
    ax.text(25.5, 83, "1. Dynamic Device Provisioning", fontsize=11, fontweight='bold', color='#38BDF8', ha='center')
    ax.text(25.5, 77, "• Multi-Device Support: Router, Switch, Host, NMAS\n• Dynamic Router Fields: OSPF, BGP ASN, Router-ID\n• Dynamic Switch Fields: VLANs (10-40), Trunks\n• Multi-File Upload: Running configs & Jinja2 (.j2)", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    # Feature 2: Live eAPI Config Extraction
    f2 = patches.FancyBboxPatch((53, 52), 43, 36, boxstyle="round,pad=1.2", 
                               facecolor='#1E293B', edgecolor='#10B981', linewidth=1.8)
    ax.add_patch(f2)
    ax.text(74.5, 83, "2. Live eAPI Configuration Pull", fontsize=11, fontweight='bold', color='#34D399', ha='center')
    ax.text(74.5, 77, "• Arista eAPI JSON-RPC over HTTP (Port 80)\n• Commands: ['enable', 'show running-config']\n• 1-Click Batch Sync: 'Pull All Live Configs'\n• Automatic status & timestamp tracking in DB", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    # Feature 3: Golden Configuration & Diff
    f3 = patches.FancyBboxPatch((4, 12), 43, 36, boxstyle="round,pad=1.2", 
                               facecolor='#1E293B', edgecolor='#F59E0B', linewidth=1.8)
    ax.add_patch(f3)
    ax.text(25.5, 43, "3. Golden Config Archive & Diff Engine", fontsize=11, fontweight='bold', color='#FBBF24', ha='center')
    ax.text(25.5, 37, "• Timestamped Version Snapshots (vYYYYMMDD_HHMMSS)\n• Dual Storage: SQLite DB + 'golden_configs/' directory\n• In-Browser Unified Diff Engine (Side-by-side)\n• Audit trail for configuration change management", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    # Feature 4: Bidirectional Movement & Templates
    f4 = patches.FancyBboxPatch((53, 12), 43, 36, boxstyle="round,pad=1.2", 
                               facecolor='#1E293B', edgecolor='#A855F7', linewidth=1.8)
    ax.add_patch(f4)
    ax.text(74.5, 43, "4. Bidirectional Movement & IaC Studio", fontsize=11, fontweight='bold', color='#C084FC', ha='center')
    ax.text(74.5, 37, "• Bidirectional: Django (Port 8000) <---> Grafana (Port 3000)\n• Live In-Browser Jinja2 + YAML Compiler\n• Multi-Vendor Template Catalog (Arista, Cisco, SONiC)\n• REST API Inventory Endpoint (/api/devices/)", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "slide5_nsot_diagram.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Created:", out_path)

def create_multivendor_matrix():
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    fig.patch.set_facecolor('#0F172A')
    ax.set_facecolor('#0F172A')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 94, "Multi-Vendor IaC Hierarchy & Git CI/CD Ecosystem", 
            fontsize=14, fontweight='bold', color='#38BDF8', ha='center')

    # Table background box
    t_box = patches.FancyBboxPatch((4, 30), 92, 58, boxstyle="round,pad=1.2", 
                                  facecolor='#1E293B', edgecolor='#334155', linewidth=1.5)
    ax.add_patch(t_box)

    # Headers
    headers = ["Hierarchy Tier", "Arista EOS", "Cisco NX-OS", "Cisco XRv 9k", "SONiC VS"]
    x_cols = [15, 35, 54, 73, 88]
    for h, x in zip(headers, x_cols):
        ax.text(x, 83, h, fontsize=10.5, fontweight='bold', color='#38BDF8', ha='center')
    
    # Divider line
    ax.plot([6, 94], [80, 80], color='#475569', lw=1.2)

    # Rows
    rows = [
        ("Tier 1: Distribution (R1-R2)", "r1_r2.j2", "--", "cisco_xrv9k_r1_r2.j2", "sonic_r1_r2.j2"),
        ("Tier 2: ASBR Core (R3-R4)", "r3_r4.j2", "--", "cisco_xrv9k_r3_r4.j2", "sonic_r3_r4.j2"),
        ("Tier 3: PE WAN Gateway (R5)", "r5.j2", "--", "cisco_xrv9k_r5.j2", "--"),
        ("Tier 4: Access Switch (S1-S2)", "s1_s2.j2", "cisco_nxos_s1_s2.j2", "--", "sonic_s1_s2.j2"),
        ("Tier 5: Core Switch (S3-S4)", "s3_s4.j2", "cisco_nxos_s3_s4.j2", "--", "--"),
    ]

    y_pos = 73
    for tier, arista, nxos, xrv, sonic in rows:
        ax.text(x_cols[0], y_pos, tier, fontsize=8.5, fontweight='bold', color='#F1F5F9', ha='center')
        ax.text(x_cols[1], y_pos, arista, fontsize=8, color='#34D399', ha='center')
        ax.text(x_cols[2], y_pos, nxos, fontsize=8, color='#38BDF8' if nxos != "--" else '#64748B', ha='center')
        ax.text(x_cols[3], y_pos, xrv, fontsize=8, color='#FBBF24' if xrv != "--" else '#64748B', ha='center')
        ax.text(x_cols[4], y_pos, sonic, fontsize=8, color='#C084FC' if sonic != "--" else '#64748B', ha='center')
        y_pos -= 8.5

    # Bottom Git Card
    git_box = patches.FancyBboxPatch((4, 6), 92, 20, boxstyle="round,pad=1.0", 
                                    facecolor='#0F172A', edgecolor='#10B981', linewidth=1.5)
    ax.add_patch(git_box)
    ax.text(50, 21, "📦 Git CI/CD & Version Control Infrastructure", fontsize=10.5, fontweight='bold', color='#34D399', ha='center')
    ax.text(50, 13, "• Upstream Repository: github.com/aryastark11/advnetman (Branch: main)\n• Automated Verification: 15/15 Multi-Vendor Render Test Cases PASS\n• Source-of-Truth Decoupling: 16 Standalone YAML Models in data_models/", 
            fontsize=8.5, color='#CBD5E1', ha='center')

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "slide6_multivendor_matrix.png")
    plt.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Created:", out_path)

if __name__ == '__main__':
    create_datalake_diagram()
    create_nsot_diagram()
    create_multivendor_matrix()
