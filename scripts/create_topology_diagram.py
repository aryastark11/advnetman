import os
import vsdx
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import numpy as np

def generate_vsdx(output_path):
    p = os.path.join(os.path.dirname(vsdx.__file__), "media", "media.vsdx")
    with vsdx.VisioFile(p) as doc:
        page = doc.pages[0]
        page.width = 26.0
        page.height = 20.0

        rect_tpl = page.find_shape_by_text("RECTANGLE")
        circle_tpl = page.find_shape_by_text("CIRCLE")
        conn_tpl = page.find_shape_by_text("STRAIGHT_CONNECTOR")

        nodes_info = {
            "Web Server": (20.5, 15.5, "rect", "#34495e", "Web Server\n198.51.100.10/24\n2001:db8:100::10/64", 2.8, 1.6),
            "R5": (13.0, 15.5, "circle", "#1565c0", "R5 (PE Router)\nBGP AS 65005\nArista cEOS", 2.2, 2.2),
            "R3": (6.8, 12.0, "circle", "#1976d2", "R3 (ASBR)\nAS 65001 | OSPF A0\nArista cEOS", 2.2, 2.2),
            "R4": (19.2, 12.0, "circle", "#1976d2", "R4 (ASBR)\nAS 65001 | OSPF A0\nArista cEOS", 2.2, 2.2),
            "S3": (9.5, 9.0, "rect", "#00838f", "S3 (Core Switch)\nOSPF Area 0 Bridge\nArista cEOS", 2.4, 1.4),
            "S4": (16.5, 9.0, "rect", "#00838f", "S4 (Core Switch)\nOSPF Area 0 Bridge\nArista cEOS", 2.4, 1.4),
            "NMAS": (2.8, 9.0, "rect", "#455a64", "NMAS Station\n10.0.0.100/24\n2001:db8:0::100/64", 2.5, 1.4),
            "Backup Server": (2.8, 12.0, "rect", "#37474f", "Backup Node\n10.99.99.2/30 (eth1)\nIsolated Data Lake Backup", 2.6, 1.5),
            "R1": (6.8, 6.0, "circle", "#0288d1", "R1 (Distribution)\nOSPF A0 / RIPv2\nArista cEOS", 2.2, 2.2),
            "R2": (19.2, 6.0, "circle", "#0288d1", "R2 (Dist / DHCP)\nOSPF A0 / RIPv2 / DHCP\nArista cEOS", 2.2, 2.2),
            "S1": (6.8, 3.2, "rect", "#00897b", "S1 (Access Switch)\nVLAN 10, 20, 30\nArista cEOS", 2.4, 1.4),
            "S2": (19.2, 3.2, "rect", "#00897b", "S2 (Access Switch)\nVLAN 10, 20, 30\nArista cEOS", 2.4, 1.4),
            "H1": (3.6, 1.2, "rect", "#546e7a", "H1 (VLAN 10)\n10.10.10.101/24\n2001:db8:10::101/64", 2.3, 1.3),
            "H2": (9.8, 1.2, "rect", "#546e7a", "H2 (VLAN 20)\n10.10.20.102/24\n2001:db8:20::102/64", 2.3, 1.3),
            "H3": (16.2, 1.2, "rect", "#546e7a", "H3 (VLAN 10)\n10.10.10.103/24\n2001:db8:10::103/64", 2.3, 1.3),
            "H4": (22.4, 1.2, "rect", "#546e7a", "H4 (VLAN 30: IPv6 Only)\n2001:db8:30::104/64", 2.3, 1.3),
        }

        dev_shapes = {}
        for name, (x, y, stype, color, text, w, h) in nodes_info.items():
            tpl = circle_tpl if stype == "circle" else rect_tpl
            sh = tpl.copy(page)
            sh.x = x
            sh.y = y
            sh.width = w
            sh.height = h
            sh.text = text
            sh.fill_color = color
            dev_shapes[name] = sh

        links = [
            ("R5", "Web Server", "Et1 (198.51.100.1)", "eth1 (198.51.100.10)", "198.51.100.0/24 | 2001:db8:100::/64"),
            ("R5", "R3", "Et2 (172.16.35.2)", "Et1 (172.16.35.1)", "eBGP: 172.16.35.0/30 | 2001:db8:35::/64"),
            ("R5", "R4", "Et3 (172.16.45.2)", "Et1 (172.16.45.1)", "eBGP: 172.16.45.0/30 | 2001:db8:45::/64"),
            ("R3", "S3", "Et2 (10.0.0.3)", "Et1", "OSPF Area 0 Link"),
            ("R4", "S4", "Et2 (10.0.0.4)", "Et1", "OSPF Area 0 Link"),
            ("S3", "S4", "Et2", "Et2", "Core Cross-Link (VLAN 1)"),
            ("S3", "R1", "Et3", "Et1 (10.0.0.1)", "OSPF Area 0 Link"),
            ("S4", "R2", "Et3", "Et1 (10.0.0.2)", "OSPF Area 0 Link"),
            ("S3", "NMAS", "Et4", "eth1 (10.0.0.100)", "OSPF Area 0 / NMAS Link"),
            ("NMAS", "Backup Server", "eth2 (10.99.99.1)", "eth1 (10.99.99.2)", "P2P Isolated Link (10.99.99.0/30)"),
            ("R1", "S1", "Et2 (Trunk .10, .20)", "Et1 (Trunk)", "Trunk: VLAN 10, 20 (RIPv2)"),
            ("R2", "S2", "Et2 (Trunk .10, .20, .30)", "Et1 (Trunk)", "Trunk: VLAN 10, 20, 30 (RIPv2 & DHCP)"),
            ("S1", "S2", "Et2 (Trunk)", "Et2 (Trunk)", "Inter-Switch Trunk (VLAN 10, 20, 30)"),
            ("S1", "H1", "Et3 (Access 10)", "eth1", "VLAN 10 Access"),
            ("S1", "H2", "Et4 (Access 20)", "eth1", "VLAN 20 Access"),
            ("S2", "H3", "Et3 (Access 10)", "eth1", "VLAN 10 Access"),
            ("S2", "H4", "Et4 (Access 30)", "eth1", "VLAN 30 Access (IPv6-Only)"),
        ]

        for n1, n2, if1, if2, sub in links:
            s1 = dev_shapes[n1]
            s2 = dev_shapes[n2]
            conn = conn_tpl.copy(page)
            conn.set_start_and_finish((s1.x, s1.y), (s2.x, s2.y))
            conn.text = ""
            conn.line_color = "#37474f"
            conn.line_weight = 0.025

            lbl1 = rect_tpl.copy(page)
            lbl1.x = s1.x + (s2.x - s1.x) * 0.28
            lbl1.y = s1.y + (s2.y - s1.y) * 0.28
            lbl1.width = 1.8
            lbl1.height = 0.4
            lbl1.text = if1
            lbl1.fill_color = "#e3f2fd"
            lbl1.line_color = "#90caf9"

            lbl2 = rect_tpl.copy(page)
            lbl2.x = s1.x + (s2.x - s1.x) * 0.72
            lbl2.y = s1.y + (s2.y - s1.y) * 0.72
            lbl2.width = 1.8
            lbl2.height = 0.4
            lbl2.text = if2
            lbl2.fill_color = "#e3f2fd"
            lbl2.line_color = "#90caf9"

        title_box = rect_tpl.copy(page)
        title_box.x = 13.0
        title_box.y = 18.5
        title_box.width = 15.0
        title_box.height = 0.8
        title_box.text = "ADVANCED NETWORK AUTOMATION - LAB 1 TOPOLOGY DIAGRAM\nArista cEOS Architecture with Interface Names, BGP, OSPF Area 0, RIPv2 & VLANs"
        title_box.fill_color = "#eceff1"
        title_box.line_color = "#78909c"

        for t in [rect_tpl, circle_tpl, conn_tpl, 
                  page.find_shape_by_text("CONNECTED_SHAPE"),
                  page.find_shape_by_text("CURVED_CONNECTOR"),
                  page.find_shape_by_text("LINE")]:
            if t:
                try:
                    t.remove()
                except Exception:
                    pass

        doc.save_vsdx(output_path)
        print("Successfully generated Visio diagram: " + output_path)

def generate_images(png_path, svg_path):
    fig, ax = plt.subplots(figsize=(26, 20), dpi=300)
    ax.set_xlim(0, 26)
    ax.set_ylim(-0.5, 19.5)
    ax.axis("off")

    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    header = FancyBboxPatch((1.0, 18.0), 24.0, 1.2,
                            boxstyle="round,pad=0.1,rounding_size=0.15",
                            facecolor="#0f172a", edgecolor="#334155", linewidth=1.5, zorder=1)
    ax.add_patch(header)
    ax.text(13.0, 18.75, "ADVANCED NETWORK AUTOMATION — LAB 1 NETWORK TOPOLOGY",
            color="#ffffff", fontsize=19, fontweight="bold", ha="center", va="center", zorder=2)
    ax.text(13.0, 18.3, "Arista cEOS Architecture | Multi-Protocol BGP (AS 65001 / 65005) | OSPF Area 0 Core | RIPv2 & 802.1Q Access | Dual-Stack IPv4 & IPv6",
            color="#94a3b8", fontsize=11.5, ha="center", va="center", zorder=2)

    ospf_circle = patches.Ellipse((13.0, 8.8), 15.6, 8.6,
                                  facecolor="#eff6ff", edgecolor="#2563eb",
                                  linewidth=2.2, linestyle="--", alpha=0.8, zorder=2)
    ax.add_patch(ospf_circle)
    ax.text(13.0, 12.0, "OSPF Area 0 (Core Backbone)",
            color="#1d4ed8", fontsize=15, fontweight="bold", ha="center", va="center", zorder=3)
    ax.text(13.0, 11.65, "Subnet: 10.0.0.0/24 | 2001:db8:0::/64",
            color="#3b82f6", fontsize=10.5, fontstyle="italic", ha="center", va="center", zorder=3)

    rip_box = FancyBboxPatch((3.4, 2.0), 19.2, 4.2,
                             boxstyle="round,pad=0.2,rounding_size=0.3",
                             facecolor="#fdf4ff", edgecolor="#9333ea",
                             linewidth=2.2, linestyle="--", alpha=0.75, zorder=2)
    ax.add_patch(rip_box)
    ax.text(13.0, 4.6, "RIPv2 & 802.1Q Access Routing Domain",
            color="#7e22ce", fontsize=14, fontweight="bold", ha="center", va="center", zorder=3)
    ax.text(13.0, 4.25, "Mutual Redistribution: RIPv2 ↔ OSPF Area 0 | R2 DHCPv4 & DHCPv6 Server",
            color="#a855f7", fontsize=9.5, fontstyle="italic", ha="center", va="center", zorder=3)

    bgp_banner = FancyBboxPatch((9.6, 12.8), 6.8, 1.2,
                                boxstyle="round,pad=0.1,rounding_size=0.15",
                                facecolor="#ecfdf5", edgecolor="#059669",
                                linewidth=1.5, linestyle="-.", zorder=2)
    ax.add_patch(bgp_banner)
    ax.text(13.0, 13.6, "eBGP Peering Domain",
            color="#047857", fontsize=13, fontweight="bold", ha="center", va="center", zorder=3)
    ax.text(13.0, 13.15, "AS 65005 (PE) ↔ AS 65001 (Core) | Dual-Stack IPv4/IPv6",
            color="#059669", fontsize=9.5, ha="center", va="center", zorder=3)

    cloud_box = FancyBboxPatch((17.6, 13.2), 7.2, 3.8,
                               boxstyle="round,pad=0.1,rounding_size=0.25",
                               facecolor="#f1f5f9", edgecolor="#64748b",
                               linewidth=1.8, linestyle=":", zorder=2)
    ax.add_patch(cloud_box)
    ax.text(21.2, 16.6, "Simulated Internet / Cloud",
            color="#334155", fontsize=12, fontweight="bold", ha="center", va="center", zorder=3)

    backup_domain_box = FancyBboxPatch((0.8, 10.4), 4.0, 3.6,
                                       boxstyle="round,pad=0.1,rounding_size=0.2",
                                       facecolor="#fef2f2", edgecolor="#ef4444",
                                       linewidth=1.8, linestyle="--", alpha=0.75, zorder=2)
    ax.add_patch(backup_domain_box)
    ax.text(2.8, 13.7, "Isolated Backup Domain",
            color="#dc2626", fontsize=10.5, fontweight="bold", ha="center", va="center", zorder=3)
    ax.text(2.8, 13.35, "Strict NMAS-Only Access (10.99.99.0/30)",
            color="#b91c1c", fontsize=7.5, fontstyle="italic", ha="center", va="center", zorder=3)

    nodes = {
        "web-server": {"pos": (21.2, 15.0), "type": "server", "name": "Web Server",
                       "card_offset": (0.0, -1.25),
                       "line1": "Public Server (Dual-Stack)", "line2": "198.51.100.10/24", "line3": "2001:db8:100::10/64"},
        "r5": {"pos": (13.0, 15.0), "type": "router", "name": "R5",
               "card_offset": (0.0, 1.3),
               "line1": "PE Router (Arista cEOS)", "line2": "BGP AS 65005", "line3": "Default Route Origination"},
        "r3": {"pos": (6.8, 11.6), "type": "router", "name": "R3",
               "card_offset": (-1.75, 0.0),
               "line1": "ASBR / Core Router", "line2": "BGP AS 65001 | OSPF A0", "line3": "10.0.0.3 | 2001:db8:0::3"},
        "r4": {"pos": (19.2, 11.6), "type": "router", "name": "R4",
               "card_offset": (1.75, 0.0),
               "line1": "ASBR / Core Router", "line2": "BGP AS 65001 | OSPF A0", "line3": "10.0.0.4 | 2001:db8:0::4"},
        "s3": {"pos": (9.2, 8.8), "type": "switch", "name": "S3",
               "card_offset": (0.0, -1.1),
               "line1": "Core Backbone Switch", "line2": "OSPF Area 0 Bridge", "line3": "Arista cEOS"},
        "s4": {"pos": (16.8, 8.8), "type": "switch", "name": "S4",
               "card_offset": (0.0, -1.1),
               "line1": "Core Backbone Switch", "line2": "OSPF Area 0 Bridge", "line3": "Arista cEOS"},
        "nmas": {"pos": (2.8, 8.8), "type": "server", "name": "NMAS Station",
                 "card_offset": (0.0, -1.25),
                 "line1": "Mgmt & Monitoring VM", "line2": "10.0.0.100/24", "line3": "2001:db8:0::100/64"},
        "backup-server": {"pos": (2.8, 11.7), "type": "server", "name": "Backup Node",
                          "card_offset": (0.0, 1.0),
                          "line1": "Isolated Data Lake Storage", "line2": "10.99.99.2/30 (eth1)", "line3": "Accessible ONLY by NMAS"},
        "r1": {"pos": (6.8, 5.8), "type": "router", "name": "R1",
               "card_offset": (-1.75, 0.0),
               "line1": "Distribution Router", "line2": "OSPF A0 | RIPv2 GW", "line3": "10.0.0.1 | 10.10.10/20.1"},
        "r2": {"pos": (19.2, 5.8), "type": "router", "name": "R2",
               "card_offset": (1.75, 0.0),
               "line1": "Dist Router & DHCP Server", "line2": "OSPF A0 | RIPv2 | DHCP", "line3": "VLAN 10/20/30 (IPv6 GW)"},
        "s1": {"pos": (6.8, 3.1), "type": "switch", "name": "S1",
               "card_offset": (-1.75, 0.0),
               "line1": "Access Switch (VLAN 10,20)", "line2": "802.1Q Trunks to R1 & S2", "line3": "Arista cEOS"},
        "s2": {"pos": (19.2, 3.1), "type": "switch", "name": "S2",
               "card_offset": (1.75, 0.0),
               "line1": "Access Switch (VLAN 10,20,30)", "line2": "802.1Q Trunks to R2 & S1", "line3": "Arista cEOS"},
        "h1": {"pos": (3.6, 1.1), "type": "host", "name": "H1",
               "card_offset": (0.0, -0.75),
               "line1": "VLAN 10 (Dual-Stack)", "line2": "10.10.10.101/24", "line3": "2001:db8:10::101/64"},
        "h2": {"pos": (9.8, 1.1), "type": "host", "name": "H2",
               "card_offset": (0.0, -0.75),
               "line1": "VLAN 20 (Dual-Stack)", "line2": "10.10.20.102/24", "line3": "2001:db8:20::102/64"},
        "h3": {"pos": (16.2, 1.1), "type": "host", "name": "H3",
               "card_offset": (0.0, -0.75),
               "line1": "VLAN 10 (Dual-Stack)", "line2": "10.10.10.103/24", "line3": "2001:db8:10::103/64"},
        "h4": {"pos": (22.4, 1.1), "type": "host", "name": "H4",
               "card_offset": (0.0, -0.75),
               "line1": "VLAN 30 (Strict IPv6-Only)", "line2": "No IPv4 Assigned", "line3": "2001:db8:30::104/64"},
    }

    # Links with custom label positions: (n1, n2, if1, if2, sub_text, color, lp1, lp2, sub_pos)
    # Using explicit coordinates for badges guarantees 100% clean visual presentation!
    link_specs = [
        ("r5", "web-server", "Ethernet1\n198.51.100.1", "eth1\n198.51.100.10", "198.51.100.0/24 | 2001:db8:100::/64", "#0284c7",
         (14.8, 15.4), (19.4, 15.4), (17.1, 15.4)),
        ("r5", "r3", "Ethernet2\n172.16.35.2", "Ethernet1\n172.16.35.1", "eBGP: 172.16.35.0/30 | 2001:db8:35::/64", "#059669",
         (11.3, 14.3), (7.9, 12.5), (9.6, 13.5)),
        ("r5", "r4", "Ethernet3\n172.16.45.2", "Ethernet1\n172.16.45.1", "eBGP: 172.16.45.0/30 | 2001:db8:45::/64", "#059669",
         (14.7, 14.3), (18.1, 12.5), (16.4, 13.5)),
        ("r3", "s3", "Ethernet2\n10.0.0.3", "Ethernet1", "OSPF Area 0 Link", "#2563eb",
         (7.6, 10.5), (8.7, 9.6), (8.2, 10.1)),
        ("r4", "s4", "Ethernet2\n10.0.0.4", "Ethernet1", "OSPF Area 0 Link", "#2563eb",
         (18.4, 10.5), (17.3, 9.6), (17.8, 10.1)),
        ("s3", "s4", "Ethernet2", "Ethernet2", "Core Cross-Link (VLAN 1)", "#0284c7",
         (10.8, 9.1), (15.2, 9.1), (13.0, 9.1)),
        ("s3", "r1", "Ethernet3", "Ethernet1\n10.0.0.1", "OSPF Area 0 Link", "#2563eb",
         (8.7, 8.0), (7.6, 7.0), (8.2, 7.5)),
        ("s4", "r2", "Ethernet3", "Ethernet1\n10.0.0.2", "OSPF Area 0 Link", "#2563eb",
         (17.3, 8.0), (18.4, 7.0), (17.8, 7.5)),
        ("s3", "nmas", "Ethernet4", "eth1\n10.0.0.100", "OSPF Area 0 / NMAS Link", "#475569",
         (7.6, 8.8), (4.4, 8.8), (6.0, 9.1)),
        ("nmas", "backup-server", "eth2\n10.99.99.1", "eth1\n10.99.99.2", "Dedicated P2P Link (10.99.99.0/30)", "#dc2626",
         (1.7, 9.8), (1.7, 10.7), (3.9, 10.25)),
        ("r1", "s1", "Ethernet2 (Trunk)\n.10: 10.10.10.1\n.20: 10.10.20.1", "Ethernet1\n(Trunk: 10, 20)", "Trunk: VLAN 10, 20 (RIPv2)", "#7c3aed",
         (5.4, 4.8), (8.1, 3.8), (6.8, 4.3)),
        ("r2", "s2", "Ethernet2 (Trunk)\n.10: .2 | .20: .2\n.30: 2001:db8:30::2", "Ethernet1\n(Trunk: 10, 20, 30)", "Trunk: VLAN 10, 20, 30 (RIPv2 & DHCP)", "#7c3aed",
         (17.8, 4.8), (20.5, 3.8), (19.2, 4.3)),
        ("s1", "s2", "Ethernet2\n(Trunk)", "Ethernet2\n(Trunk)", "Inter-Switch Trunk (VLAN 10, 20, 30)", "#9333ea",
         (8.4, 2.8), (17.6, 2.8), (13.0, 2.8)),
        ("s1", "h1", "Ethernet3\n(Access 10)", "eth1", "VLAN 10 Access", "#0891b2",
         (5.6, 2.3), (4.2, 1.6), (4.9, 2.0)),
        ("s1", "h2", "Ethernet4\n(Access 20)", "eth1", "VLAN 20 Access", "#0891b2",
         (8.0, 2.3), (9.2, 1.6), (8.6, 2.0)),
        ("s2", "h3", "Ethernet3\n(Access 10)", "eth1", "VLAN 10 Access", "#0891b2",
         (18.0, 2.3), (16.8, 1.6), (17.4, 2.0)),
        ("s2", "h4", "Ethernet4\n(Access 30)", "eth1", "VLAN 30 (IPv6-Only)", "#d97706",
         (20.4, 2.3), (21.8, 1.6), (21.1, 2.0)),
    ]

    for n1, n2, if1, if2, sub_text, lcolor, lp1, lp2, sub_pos in link_specs:
        p1 = nodes[n1]["pos"]
        p2 = nodes[n2]["pos"]

        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=lcolor, linestyle="-", linewidth=2.5, zorder=4)

        ax.text(lp1[0], lp1[1], if1, fontsize=7.2, fontweight="bold", color="#1e293b",
                ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=1.0, alpha=0.98))

        ax.text(lp2[0], lp2[1], if2, fontsize=7.2, fontweight="bold", color="#1e293b",
                ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=1.0, alpha=0.98))

        if sub_text:
            ax.text(sub_pos[0], sub_pos[1], sub_text, fontsize=7.2, color="#334155",
                    ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="square,pad=0.25", facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.8, alpha=0.95))

    for key, info in nodes.items():
        x, y = info["pos"]
        ntype = info["type"]
        name = info["name"]
        cx_off, cy_off = info["card_offset"]

        if ntype == "router":
            out_c = Circle((x, y), 0.95, facecolor="#1e40af", edgecolor="#1e3a8a", linewidth=2.5, zorder=7)
            ax.add_patch(out_c)
            in_c = Circle((x, y), 0.88, facecolor="#3b82f6", edgecolor="none", zorder=8)
            ax.add_patch(in_c)

            for angle in [0, 90, 180, 270]:
                rad = np.radians(angle)
                ax.annotate("", xy=(x + np.cos(rad)*0.75, y + np.sin(rad)*0.75),
                            xytext=(x + np.cos(rad)*0.25, y + np.sin(rad)*0.25),
                            arrowprops=dict(arrowstyle="->", color="#ffffff", lw=1.8), zorder=9)

            ax.text(x, y - 0.05, name, color="#ffffff", fontsize=12, fontweight="bold", ha="center", va="center", zorder=10)

            card_x = x + cx_off
            card_y = y + cy_off
            card_text = "\n".join([info["line1"], info["line2"], info["line3"]])
            ax.text(card_x, card_y, card_text,
                    color="#0f172a", fontsize=7.6, ha="center", va="center", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=1.1, alpha=0.98))

        elif ntype == "switch":
            sw_box = FancyBboxPatch((x - 1.05, y - 0.65), 2.1, 1.3,
                                    boxstyle="round,pad=0.1,rounding_size=0.15",
                                    facecolor="#0d9488", edgecolor="#115e59", linewidth=2.0, zorder=7)
            ax.add_patch(sw_box)

            ax.annotate("", xy=(x + 0.65, y + 0.18), xytext=(x - 0.65, y + 0.18),
                        arrowprops=dict(arrowstyle="<->", color="#ffffff", lw=2.0), zorder=8)
            ax.annotate("", xy=(x - 0.65, y - 0.18), xytext=(x + 0.65, y - 0.18),
                        arrowprops=dict(arrowstyle="<->", color="#ffffff", lw=2.0), zorder=8)

            ax.text(x, y + 0.02, name, color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center", zorder=9)

            card_x = x + cx_off
            card_y = y + cy_off
            card_text = "\n".join([info["line1"], info["line2"], info["line3"]])
            ax.text(card_x, card_y, card_text,
                    color="#0f172a", fontsize=7.6, ha="center", va="center", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#f0fdfa", edgecolor="#5eead4", linewidth=1.1, alpha=0.98))

        elif ntype == "server":
            srv_box = FancyBboxPatch((x - 1.15, y - 0.75), 2.3, 1.5,
                                     boxstyle="round,pad=0.1,rounding_size=0.18",
                                     facecolor="#334155", edgecolor="#1e293b", linewidth=2.0, zorder=7)
            ax.add_patch(srv_box)

            for offset in [-0.35, 0.0, 0.35]:
                ax.plot([x - 0.85, x + 0.55], [y + offset, y + offset], color="#64748b", lw=1.5, zorder=8)
                ax.plot([x + 0.75], [y + offset], marker="o", markersize=3.5, color="#22c55e", zorder=9)

            ax.text(x, y + 0.02, name, color="#ffffff", fontsize=10.5, fontweight="bold", ha="center", va="center", zorder=10)

            card_x = x + cx_off
            card_y = y + cy_off
            card_text = "\n".join([info["line1"], info["line2"], info["line3"]])
            ax.text(card_x, card_y, card_text,
                    color="#0f172a", fontsize=7.6, ha="center", va="center", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8fafc", edgecolor="#94a3b8", linewidth=1.1, alpha=0.98))

        elif ntype == "host":
            pc_box = FancyBboxPatch((x - 1.05, y - 0.35), 2.1, 0.95,
                                    boxstyle="round,pad=0.08,rounding_size=0.12",
                                    facecolor="#475569", edgecolor="#1e293b", linewidth=2.0, zorder=7)
            ax.add_patch(pc_box)
            screen = FancyBboxPatch((x - 0.9, y - 0.25), 1.8, 0.75,
                                    boxstyle="square,pad=0.02",
                                    facecolor="#0284c7" if "VLAN 10" in info["line1"] else ("#7c3aed" if "VLAN 20" in info["line1"] else "#d97706"),
                                    edgecolor="none", zorder=8)
            ax.add_patch(screen)
            ax.plot([x, x], [y - 0.35, y - 0.52], color="#334155", lw=3.0, zorder=7)
            ax.plot([x - 0.35, x + 0.35], [y - 0.52, y - 0.52], color="#334155", lw=3.0, zorder=7)

            ax.text(x, y + 0.1, name, color="#ffffff", fontsize=11, fontweight="bold", ha="center", va="center", zorder=9)

            card_x = x + cx_off
            card_y = y + cy_off
            card_text = "\n".join([info["line1"], info["line2"], info["line3"]])
            ax.text(card_x, card_y, card_text,
                    color="#0f172a", fontsize=7.4, ha="center", va="center", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=1.0, alpha=0.98))

    leg_box = FancyBboxPatch((0.8, 14.3), 4.5, 3.4,
                             boxstyle="round,pad=0.15,rounding_size=0.2",
                             facecolor="#ffffff", edgecolor="#94a3b8", linewidth=1.2, zorder=11)
    ax.add_patch(leg_box)
    ax.text(1.1, 17.4, "TOPOLOGY LEGEND", fontsize=10.5, fontweight="bold", color="#0f172a", zorder=12)
    ax.plot([1.1, 5.0], [17.25, 17.25], color="#cbd5e1", lw=1.0, zorder=12)

    legend_items = [
        ("BGP AS 65005 / 65001 Links", "#059669", "-"),
        ("OSPF Area 0 Core Links", "#2563eb", "-"),
        ("Trunk Links (802.1Q / RIPv2)", "#7c3aed", "-"),
        ("VLAN Access Links (10, 20)", "#0891b2", "-"),
        ("VLAN 30 (Strict IPv6-Only)", "#d97706", "-"),
        ("Isolated NMAS Backup Link", "#dc2626", "-"),
        ("Arista cEOS Routers", "#1e40af", "circle"),
        ("Arista cEOS Switches", "#0d9488", "square"),
    ]

    curr_y = 16.9
    for text, col, style in legend_items:
        if style == "circle":
            ax.plot([1.3], [curr_y], marker="o", markersize=7, color=col, zorder=12)
        elif style == "square":
            ax.plot([1.3], [curr_y], marker="s", markersize=7, color=col, zorder=12)
        else:
            ax.plot([1.1, 1.5], [curr_y, curr_y], color=col, lw=2.5, linestyle=style, zorder=12)
        ax.text(1.7, curr_y, text, fontsize=7.8, color="#334155", va="center", zorder=12)
        curr_y -= 0.33

    plt.tight_layout()
    plt.savefig(png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.savefig(svg_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print("Successfully generated PNG diagram: " + png_path)
    print("Successfully generated SVG diagram: " + svg_path)

if __name__ == "__main__":
    base_dir = "/home/student/Desktop/lab1"
    vsdx_out = os.path.join(base_dir, "network_topology.vsdx")
    png_out = os.path.join(base_dir, "network_topology.png")
    svg_out = os.path.join(base_dir, "network_topology.svg")

    generate_vsdx(vsdx_out)
    generate_images(png_out, svg_out)
