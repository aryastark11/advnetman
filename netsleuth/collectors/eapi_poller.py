import pyeapi
import logging
from typing import Dict, List, Any, Optional
from .vault_client import vault_manager

logger = logging.getLogger("netsleuth.eapi")

# Device Management IP Mapping
DEVICE_IPS = {
    "R1": "172.20.20.11",
    "R2": "172.20.20.12",
    "R3": "172.20.20.13",
    "R4": "172.20.20.14",
    "R5": "172.20.20.15",
    "R6": "172.20.20.16",
    "R7": "172.20.20.17",
    "R8": "172.20.20.18",
    "S1": "172.20.20.21",
    "S2": "172.20.20.22",
    "S3": "172.20.20.23",
    "S4": "172.20.20.24",
    "S5": "172.20.20.25",
}

# Add lowercase aliases
for k, v in list(DEVICE_IPS.items()):
    DEVICE_IPS[k.lower()] = v

def get_node_client(hostname: str, timeout: int = 4) -> Optional[pyeapi.client.Node]:
    norm_name = hostname.upper()
    ip = DEVICE_IPS.get(norm_name) or DEVICE_IPS.get(hostname.lower())
    if not ip:
        logger.warning(f"Unknown device IP for {hostname}")
        return None

    username, password = vault_manager.get_device_credentials(norm_name)
    try:
        conn = pyeapi.client.connect(
            transport="http",
            host=ip,
            username=username,
            password=password,
            port=80,
            timeout=timeout
        )
        return pyeapi.client.Node(conn)
    except Exception as e:
        logger.error(f"Failed to connect to {hostname} ({ip}): {e}")
        return None

def run_commands(hostname: str, commands: List[str], encoding: str = "json") -> List[Any]:
    node = get_node_client(hostname)
    if not node:
        return []
    try:
        res = node.enable(commands, encoding=encoding)
        return [r.get("result", {}) for r in res]
    except Exception as e:
        logger.warning(f"eAPI error on {hostname} running {commands}: {e}")
        return []

def get_lldp_neighbors(hostname: str) -> List[Dict[str, Any]]:
    res = run_commands(hostname, ["show lldp neighbors"])
    if not res:
        return []
    return res[0].get("lldpNeighbors", [])

def get_interfaces_status(hostname: str) -> Dict[str, Any]:
    res = run_commands(hostname, ["show interfaces status", "show interfaces counters errors"])
    statuses = res[0].get("interfaceStatuses", {}) if len(res) > 0 else {}
    errors = res[1].get("interfaceErrorCounters", {}) if len(res) > 1 else {}
    return {
        "statuses": statuses,
        "errors": errors
    }

def get_ospf_neighbors(hostname: str) -> List[Dict[str, Any]]:
    res = run_commands(hostname, ["show ip ospf neighbor"])
    if not res:
        return []
    data = res[0]
    neighbors = []
    vrfs = data.get("vrfs", {})
    for vrf_name, vrf_data in vrfs.items():
        inst_list = vrf_data.get("instList", {})
        for inst_id, inst_data in inst_list.items():
            for entry in inst_data.get("ospfNeighborEntries", []):
                neighbors.append({
                    "router_id": entry.get("routerId"),
                    "interface": entry.get("interfaceName"),
                    "ip": entry.get("interfaceAddress"),
                    "state": entry.get("adjacencyState"),
                    "dr_state": entry.get("drState"),
                    "area": entry.get("details", {}).get("areaId")
                })
    return neighbors

def get_bgp_peers(hostname: str) -> List[Dict[str, Any]]:
    res = run_commands(hostname, ["show ip bgp summary"])
    if not res:
        return []
    data = res[0]
    peers = []
    vrfs = data.get("vrfs", {})
    for vrf_name, vrf_data in vrfs.items():
        peer_dict = vrf_data.get("peers", {})
        for peer_ip, pinfo in peer_dict.items():
            peers.append({
                "peer_ip": peer_ip,
                "asn": pinfo.get("asn"),
                "state": pinfo.get("peerState"),
                "prefixes_received": pinfo.get("prefixReceived", 0),
                "up_down_time": pinfo.get("upDownTime")
            })
    return peers

def get_rip_routes(hostname: str) -> List[Dict[str, Any]]:
    # show ip rip database returns text format on cEOS
    res = run_commands(hostname, ["show ip rip database"], encoding="text")
    if not res:
        return []
    text = res[0].get("output", "")
    routes = []
    current_net = None
    for line in text.splitlines():
        line = line.strip()
        if "/255." in line or "/24" in line or "/32" in line or "/30" in line:
            current_net = line.split()[0]
        elif current_net and "via " in line:
            parts = line.split("via ")
            via_part = parts[1].split(",")
            next_hop = via_part[0].strip()
            intf = via_part[2].strip() if len(via_part) > 2 else ""
            routes.append({
                "network": current_net,
                "next_hop": next_hop,
                "interface": intf
            })
            current_net = None
    return routes

def get_varp_state(hostname: str) -> Dict[str, Any]:
    res = run_commands(hostname, ["show ip virtual-router", "show vrrp"])
    varp_data = res[0] if len(res) > 0 else {}
    vrrp_data = res[1] if len(res) > 1 else {}
    return {
        "varp": varp_data,
        "vrrp": vrrp_data.get("virtualRouters", [])
    }

def get_running_config(hostname: str) -> str:
    res = run_commands(hostname, ["show running-config"], encoding="text")
    if not res:
        return ""
    return res[0].get("output", "")

def get_syslog(hostname: str, count: int = 25) -> List[str]:
    res = run_commands(hostname, [f"show logging {count}"], encoding="text")
    if not res:
        return []
    text = res[0].get("output", "")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-count:]

def run_ping(hostname: str, target_ip: str) -> Dict[str, Any]:
    res = run_commands(hostname, [f"ping {target_ip} repeat 2 timeout 1"], encoding="text")
    if not res:
        return {"success": False, "output": "eAPI command failed"}
    output = res[0].get("output", "")
    success = "0% packet loss" in output or "2 received" in output or "1 received" in output
    return {"success": success, "output": output}

def get_full_evidence_for_node(hostname: str) -> Dict[str, Any]:
    norm_name = hostname.upper()
    is_switch = norm_name.startswith("S")
    is_router = norm_name.startswith("R")

    evidence = {
        "device": norm_name,
        "mgmt_ip": DEVICE_IPS.get(norm_name, ""),
        "interfaces": get_interfaces_status(norm_name),
        "lldp": get_lldp_neighbors(norm_name),
        "syslog": get_syslog(norm_name, 15),
    }

    if is_router:
        evidence["ospf"] = get_ospf_neighbors(norm_name)
        evidence["varp"] = get_varp_state(norm_name)
        if norm_name in ["R3", "R4", "R5"]:
            evidence["bgp"] = get_bgp_peers(norm_name)
        if norm_name in ["R1", "R2", "R6", "R7"]:
            evidence["rip"] = get_rip_routes(norm_name)

    return evidence
