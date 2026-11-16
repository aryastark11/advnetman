import networkx as nx
import json
import os
import csv
from typing import Dict, List, Any, Optional, Tuple
from netsleuth.collectors.eapi_poller import get_lldp_neighbors, get_interfaces_status
from netsleuth.storage.db import get_all_node_health

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Static node metadata & positions (Lab 10 Topology Diagram)
NODE_METADATA = {
    # Edge / Internet
    "web-server": {"name": "Web Server", "role": "server", "ip": "198.51.100.10", "tier": "internet", "x": 500, "y": 60, "vlan": "None (L3/WAN)"},
    "R5": {"name": "R5", "role": "router", "ip": "172.20.20.15", "tier": "pe_wan", "x": 500, "y": 160, "protocols": ["BGP", "Static"]},
    
    # Core ASBR
    "R3": {"name": "R3", "role": "router", "ip": "172.20.20.13", "tier": "asbr_core", "x": 340, "y": 260, "protocols": ["BGP", "OSPF Area 0"]},
    "R4": {"name": "R4", "role": "router", "ip": "172.20.20.14", "tier": "asbr_core", "x": 660, "y": 260, "protocols": ["BGP", "OSPF Area 0", "OSPF Area 10"]},

    # Core Switches (OSPF Area 0 Backbone)
    "S3": {"name": "S3", "role": "switch", "ip": "172.20.20.23", "tier": "core_switch", "x": 340, "y": 380, "protocols": ["OSPF Area 0"]},
    "S4": {"name": "S4", "role": "switch", "ip": "172.20.20.24", "tier": "core_switch", "x": 660, "y": 380, "protocols": ["OSPF Area 0"]},

    # Distribution Routers
    "R1": {"name": "R1", "role": "router", "ip": "172.20.20.11", "tier": "distribution", "x": 260, "y": 500, "protocols": ["OSPF Area 0", "RIPv2", "VARP"]},
    "R2": {"name": "R2", "role": "router", "ip": "172.20.20.12", "tier": "distribution", "x": 740, "y": 500, "protocols": ["OSPF Area 0", "RIPv2", "VARP", "OSPF Area 30"]},

    # Access Switches & End Hosts (Campus LAN)
    "S1": {"name": "S1", "role": "switch", "ip": "172.20.20.21", "tier": "access_switch", "x": 180, "y": 630, "protocols": ["802.1Q", "MSTP"]},
    "S2": {"name": "S2", "role": "switch", "ip": "172.20.20.22", "tier": "access_switch", "x": 380, "y": 630, "protocols": ["802.1Q", "MSTP"]},
    "H1": {"name": "H1", "role": "host", "ip": "10.10.10.101", "tier": "host", "vlan": "10", "x": 100, "y": 760},
    "H2": {"name": "H2", "role": "host", "ip": "10.10.20.102", "tier": "host", "vlan": "20", "x": 220, "y": 760},
    "H3": {"name": "H3", "role": "host", "ip": "10.10.10.103", "tier": "host", "vlan": "10", "x": 340, "y": 760},
    "H4": {"name": "H4", "role": "host", "ip": "2001:db8:30::104", "tier": "host", "vlan": "30", "x": 460, "y": 760},

    # Expansion: Area 10 & RIP Branch (H5)
    "R6": {"name": "R6", "role": "router", "ip": "172.20.20.16", "tier": "distribution", "x": 880, "y": 260, "protocols": ["OSPF Area 10", "RIPv2"]},
    "R7": {"name": "R7", "role": "router", "ip": "172.20.20.17", "tier": "distribution", "x": 1050, "y": 380, "protocols": ["RIPv2"]},
    "H5": {"name": "H5", "role": "host", "ip": "10.70.10.105", "tier": "host", "vlan": "10", "x": 1050, "y": 520},

    # Expansion: Area 30 / ZTP Branch (H6, H7)
    "R8": {"name": "R8", "role": "router", "ip": "172.20.20.18", "tier": "distribution", "x": 900, "y": 540, "protocols": ["OSPF Area 30"]},
    "S5": {"name": "S5", "role": "switch", "ip": "172.20.20.25", "tier": "access_switch", "x": 1050, "y": 650, "protocols": ["802.1Q"]},
    "H6": {"name": "H6", "role": "host", "ip": "10.80.10.106", "tier": "host", "vlan": "10", "x": 970, "y": 770},
    "H7": {"name": "H7", "role": "host", "ip": "10.80.10.107", "tier": "host", "vlan": "10", "x": 1130, "y": 770},

    # Management & Telemetry Stack
    "nmas": {"name": "NMAS Station", "role": "management", "ip": "172.20.20.100", "tier": "nmas", "x": 120, "y": 380},
    "backup-server": {"name": "Backup Server", "role": "management", "ip": "172.20.20.101", "tier": "backup", "x": 50, "y": 260},
}

STATIC_LINKS = [
    # Internet Edge
    {"source": "web-server", "target": "R5", "src_intf": "eth1", "tgt_intf": "Ethernet1", "protocol": "Static / HTTP", "type": "wan"},
    {"source": "R5", "target": "R3", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "eBGP (AS 65005-65001)", "type": "wan"},
    {"source": "R5", "target": "R4", "src_intf": "Ethernet3", "tgt_intf": "Ethernet1", "protocol": "eBGP (AS 65005-65001)", "type": "wan"},

    # Core Backbone (OSPF Area 0)
    {"source": "R3", "target": "S3", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 0", "type": "core"},
    {"source": "R4", "target": "S4", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 0", "type": "core"},
    {"source": "S3", "target": "S4", "src_intf": "Ethernet2", "tgt_intf": "Ethernet2", "protocol": "OSPF Area 0 / Trunk", "type": "core"},
    {"source": "S3", "target": "R1", "src_intf": "Ethernet3", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 0", "type": "core"},
    {"source": "S4", "target": "R2", "src_intf": "Ethernet3", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 0", "type": "core"},
    {"source": "S3", "target": "nmas", "src_intf": "Ethernet4", "tgt_intf": "eth1", "protocol": "L3 Management", "type": "mgmt"},
    {"source": "nmas", "target": "backup-server", "src_intf": "eth2", "tgt_intf": "eth1", "protocol": "P2P Backup", "type": "mgmt"},

    # Access Layer (RIPv2 / VARP)
    {"source": "R1", "target": "S1", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "RIPv2 / 802.1Q", "type": "trunk"},
    {"source": "R2", "target": "S2", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "RIPv2 / 802.1Q", "type": "trunk"},
    {"source": "S1", "target": "S2", "src_intf": "Ethernet2", "tgt_intf": "Ethernet2", "protocol": "802.1Q Trunk", "type": "trunk"},
    {"source": "S1", "target": "H1", "src_intf": "Ethernet3", "tgt_intf": "eth1", "protocol": "VLAN 10 Access", "type": "access"},
    {"source": "S1", "target": "H2", "src_intf": "Ethernet4", "tgt_intf": "eth1", "protocol": "VLAN 20 Access", "type": "access"},
    {"source": "S2", "target": "H3", "src_intf": "Ethernet3", "tgt_intf": "eth1", "protocol": "VLAN 10 Access", "type": "access"},
    {"source": "S2", "target": "H4", "src_intf": "Ethernet4", "tgt_intf": "eth1", "protocol": "VLAN 30 IPv6 Access", "type": "access"},

    # Branch: Area 10 & RIP (R4 -> R6 -> R7 -> H5)
    {"source": "R4", "target": "R6", "src_intf": "Ethernet3", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 10", "type": "branch"},
    {"source": "R6", "target": "R7", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "RIPv2", "type": "branch"},
    {"source": "R7", "target": "H5", "src_intf": "Ethernet2", "tgt_intf": "eth1", "protocol": "VLAN 10 Access", "type": "access"},

    # Branch: Area 30 / ZTP (R2 -> R8 -> S5 -> H6, H7)
    {"source": "R2", "target": "R8", "src_intf": "Ethernet3", "tgt_intf": "Ethernet1", "protocol": "OSPF Area 30", "type": "branch"},
    {"source": "R8", "target": "S5", "src_intf": "Ethernet2", "tgt_intf": "Ethernet1", "protocol": "802.1Q Trunk", "type": "trunk"},
    {"source": "S5", "target": "H6", "src_intf": "Ethernet2", "tgt_intf": "eth1", "protocol": "VLAN 10 Access", "type": "access"},
    {"source": "S5", "target": "H7", "src_intf": "Ethernet3", "tgt_intf": "eth1", "protocol": "VLAN 10 Access", "type": "access"},
]

class NetworkTopology:
    def __init__(self):
        self.graph = nx.Graph()
        self._build_static_graph()

    def _build_static_graph(self):
        # Add all nodes
        for node_id, meta in NODE_METADATA.items():
            self.graph.add_node(node_id, **meta)

        # Add all static links
        for link in STATIC_LINKS:
            self.graph.add_edge(
                link["source"],
                link["target"],
                src_intf=link["src_intf"],
                tgt_intf=link["tgt_intf"],
                protocol=link["protocol"],
                link_type=link["type"],
                status="up"
            )

    def get_topology_data(self) -> Dict[str, Any]:
        """Return full topology structure with live health annotations for frontend."""
        health_map = get_all_node_health()

        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node_health_info = health_map.get(node_id) or health_map.get(node_id.upper()) or {}
            health = node_health_info.get("health", "healthy")
            
            nodes.append({
                "id": node_id,
                "label": data.get("name", node_id),
                "role": data.get("role", "host"),
                "tier": data.get("tier", "access"),
                "ip": data.get("ip", ""),
                "protocols": data.get("protocols", []),
                "vlan": data.get("vlan", ""),
                "x": data.get("x", 0),
                "y": data.get("y", 0),
                "health": health,
                "health_details": node_health_info.get("details", {})
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            # Edge health is warning/critical if either endpoint is degraded
            u_health = (health_map.get(u) or health_map.get(u.upper()) or {}).get("health", "healthy")
            v_health = (health_map.get(v) or health_map.get(v.upper()) or {}).get("health", "healthy")
            edge_health = "healthy"
            if "critical" in [u_health, v_health]:
                edge_health = "critical"
            elif "warning" in [u_health, v_health]:
                edge_health = "warning"

            edges.append({
                "id": f"{u}--{v}",
                "source": u,
                "target": v,
                "src_intf": data.get("src_intf", ""),
                "tgt_intf": data.get("tgt_intf", ""),
                "protocol": data.get("protocol", ""),
                "type": data.get("link_type", "core"),
                "status": data.get("status", "up"),
                "health": edge_health
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "routers": 8,
                "switches": 5,
                "hosts": 7,
                "management": 2,
                "web_servers": 1
            }
        }

topology = NetworkTopology()
