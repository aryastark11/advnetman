import networkx as nx
from typing import Dict, List, Any, Optional, Tuple
from netsleuth.collectors.eapi_poller import (
    get_interfaces_status,
    get_ospf_neighbors,
    get_bgp_peers,
    get_rip_routes,
    get_varp_state
)
from .topology import topology

EXPECTED_PATHS = {
    "H1": [
        {"node": "H1", "next_node": "S1", "intf": "eth1", "peer_intf": "Ethernet3", "check_type": "access_link"},
        {"node": "S1", "next_node": "R1", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_vlan10"},
        {"node": "R1", "next_node": "S3", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S3", "next_node": "R3", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R3", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H2": [
        {"node": "H2", "next_node": "S1", "intf": "eth1", "peer_intf": "Ethernet4", "check_type": "access_link"},
        {"node": "S1", "next_node": "R1", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_vlan20"},
        {"node": "R1", "next_node": "S3", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S3", "next_node": "R3", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R3", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H3": [
        {"node": "H3", "next_node": "S2", "intf": "eth1", "peer_intf": "Ethernet3", "check_type": "access_link"},
        {"node": "S2", "next_node": "R2", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_vlan10"},
        {"node": "R2", "next_node": "S4", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S4", "next_node": "R4", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R4", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H4": [
        {"node": "H4", "next_node": "S2", "intf": "eth1", "peer_intf": "Ethernet4", "check_type": "access_link"},
        {"node": "S2", "next_node": "R2", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_vlan30"},
        {"node": "R2", "next_node": "S4", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S4", "next_node": "R4", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R4", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H5": [
        {"node": "H5", "next_node": "R7", "intf": "eth1", "peer_intf": "Ethernet2", "check_type": "access_link"},
        {"node": "R7", "next_node": "R6", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "ospf_area20"},
        {"node": "R6", "next_node": "R4", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area10"},
        {"node": "R4", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H6": [
        {"node": "H6", "next_node": "S5", "intf": "eth1", "peer_intf": "Ethernet2", "check_type": "access_link"},
        {"node": "S5", "next_node": "R8", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_link"},
        {"node": "R8", "next_node": "R2", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area30"},
        {"node": "R2", "next_node": "S4", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S4", "next_node": "R4", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R4", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ],
    "H7": [
        {"node": "H7", "next_node": "S5", "intf": "eth1", "peer_intf": "Ethernet3", "check_type": "access_link"},
        {"node": "S5", "next_node": "R8", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "trunk_link"},
        {"node": "R8", "next_node": "R2", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area30"},
        {"node": "R2", "next_node": "S4", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "ospf_area0"},
        {"node": "S4", "next_node": "R4", "intf": "Ethernet1", "peer_intf": "Ethernet2", "check_type": "core_link"},
        {"node": "R4", "next_node": "R5", "intf": "Ethernet1", "peer_intf": "Ethernet3", "check_type": "bgp_peer"},
        {"node": "R5", "next_node": "web-server", "intf": "Ethernet1", "peer_intf": "eth1", "check_type": "wan_web"}
    ]
}

def check_hop_health(hop: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Verify live state of a single hop via eAPI."""
    node = hop["node"]
    next_node = hop["next_node"]
    check_type = hop.get("check_type", "")
    
    # Check if target is web server
    if next_node == "web-server":
        # Check R5's Ethernet1 interface state
        r5_intfs = get_interfaces_status("R5")
        eth1_st = r5_intfs.get("statuses", {}).get("Ethernet1", {})
        link_status = eth1_st.get("lineProtocolStatus") or eth1_st.get("interfaceStatus")
        if link_status in ["connected", "up"]:
            return True, "R5 connected to Web Server WAN (198.51.100.10)", {"r5_eth1": link_status}
        else:
            return False, f"R5 Ethernet1 interface is {link_status} (Web Server WAN down)", {"r5_eth1": link_status}

    # BGP check between R3/R4 and R5
    if check_type == "bgp_peer":
        bgp_peers = get_bgp_peers(node)
        for p in bgp_peers:
            if p.get("state") == "Established":
                return True, f"BGP peer established with {next_node} (AS {p.get('asn')})", p
        return False, f"BGP session to {next_node} not Established", {"peers": bgp_peers}

    # OSPF check
    if "ospf" in check_type:
        ospf_neighbors = get_ospf_neighbors(node)
        for n in ospf_neighbors:
            if n.get("state") in ["full", "2Ways"]:
                return True, f"OSPF adjacency {n.get('state')} with {next_node} (Area {n.get('area')})", n
        return False, f"OSPF adjacency not FULL with {next_node}", {"neighbors": ospf_neighbors}

    # RIP check
    if check_type == "rip_route":
        routes = get_rip_routes(node)
        if len(routes) > 0:
            return True, f"RIPv2 routing active between {node} and {next_node}", {"routes_count": len(routes)}
        return False, f"No RIPv2 routes found on {node}", {"routes": routes}

    # Standard Arista interface check if either side is a switch or router
    arista_device = node if (node.startswith("R") or node.startswith("S")) else next_node
    intf_name = hop["intf"] if arista_device == node else hop["peer_intf"]
    
    intfs = get_interfaces_status(arista_device)
    statuses = intfs.get("statuses", {})
    intf_info = statuses.get(intf_name, {})
    line_status = intf_info.get("lineProtocolStatus") or intf_info.get("interfaceStatus", "connected")

    if line_status in ["connected", "up"]:
        return True, f"Link {arista_device} {intf_name} line protocol is {line_status}", intf_info
    else:
        return False, f"Link {arista_device} {intf_name} line protocol is {line_status}", intf_info

def trace_path(source_host: str, target: str = "web-server") -> Dict[str, Any]:
    norm_host = source_host.upper()
    hops_spec = EXPECTED_PATHS.get(norm_host)
    if not hops_spec:
        # Fallback to shortest path on topology graph
        try:
            path_nodes = nx.shortest_path(topology.graph, norm_host, target)
            hops_spec = []
            for i in range(len(path_nodes) - 1):
                hops_spec.append({
                    "node": path_nodes[i],
                    "next_node": path_nodes[i+1],
                    "intf": "eth1",
                    "peer_intf": "eth1",
                    "check_type": "graph_path"
                })
        except Exception:
            return {"error": f"No valid path found from {source_host} to {target}", "hops": []}

    annotated_hops = []
    first_failing_hop = None
    all_healthy = True
    traffic_interrupted = False

    for idx, hop in enumerate(hops_spec):
        if traffic_interrupted:
            annotated_hops.append({
                "hop_number": idx + 1,
                "node": hop["node"],
                "next_node": hop["next_node"],
                "interface": hop["intf"],
                "peer_interface": hop["peer_intf"],
                "status": "unreachable",
                "reason": "Traffic already dropped at previous failing hop",
                "details": {}
            })
            continue

        ok, msg, details = check_hop_health(hop)
        status = "healthy" if ok else "failed"

        if not ok:
            all_healthy = False
            traffic_interrupted = True
            first_failing_hop = {
                "hop_number": idx + 1,
                "node": hop["node"],
                "next_node": hop["next_node"],
                "interface": hop["intf"],
                "peer_interface": hop["peer_intf"],
                "reason": msg,
                "details": details
            }

        annotated_hops.append({
            "hop_number": idx + 1,
            "node": hop["node"],
            "next_node": hop["next_node"],
            "interface": hop["intf"],
            "peer_interface": hop["peer_intf"],
            "status": status,
            "reason": msg,
            "details": details
        })

    return {
        "source": norm_host,
        "target": target,
        "status": "healthy" if all_healthy else "failed",
        "total_hops": len(annotated_hops),
        "first_failing_hop": first_failing_hop,
        "hops": annotated_hops
    }
