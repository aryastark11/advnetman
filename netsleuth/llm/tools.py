import os
from typing import Dict, List, Any
from netsleuth.collectors.eapi_poller import (
    get_ospf_neighbors as eapi_get_ospf,
    get_bgp_peers as eapi_get_bgp,
    get_rip_routes as eapi_get_rip,
    get_interfaces_status as eapi_get_intf,
    get_syslog as eapi_get_syslog,
    run_ping as eapi_run_ping,
    get_running_config
)
from netsleuth.graph.path_tracer import trace_path
from netsleuth.storage.db import get_config_drift
from .redaction import redact_sensitive_data

TOOL_DEFINITIONS = [
    {
        "name": "get_path",
        "description": "Trace hop-by-hop expected path from host to Web Server with live health checks",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source host, e.g. H1, H2, H3, H4, H5, H6, H7"},
                "target": {"type": "string", "description": "Target service/node, default web-server"}
            },
            "required": ["source"]
        }
    },
    {
        "name": "get_ospf_neighbors",
        "description": "Query OSPF neighbor adjacencies, state (FULL/2Ways), and area for a router",
        "parameters": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Hostname, e.g. R1, R2, R3, R4, R6, R7, R8"}},
            "required": ["device"]
        }
    },
    {
        "name": "get_bgp_peers",
        "description": "Query eBGP peer sessions, state (Established/Idle/Active), and prefix counts",
        "parameters": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Hostname, e.g. R3, R4, R5"}},
            "required": ["device"]
        }
    },
    {
        "name": "get_rip_routes",
        "description": "Query RIPv2 routing database for advertised network subnets",
        "parameters": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Hostname, e.g. R1, R2, R6, R7"}},
            "required": ["device"]
        }
    },
    {
        "name": "get_interface_stats",
        "description": "Query interface line protocol status and input/output error counters",
        "parameters": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Hostname, e.g. R1-R8, S1-S5"}},
            "required": ["device"]
        }
    },
    {
        "name": "get_logs",
        "description": "Retrieve recent system logging messages and error events from a device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Hostname"},
                "count": {"type": "integer", "description": "Number of recent lines to retrieve, default 15"}
            },
            "required": ["device"]
        }
    },
    {
        "name": "get_config_diff",
        "description": "Retrieve running configuration diff against golden baseline v1.0",
        "parameters": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Hostname"}},
            "required": ["device"]
        }
    },
    {
        "name": "run_ping",
        "description": "Execute ICMP ping test from a network device toward a target IP",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Source device"},
                "target_ip": {"type": "string", "description": "Destination IP address"}
            },
            "required": ["device", "target_ip"]
        }
    }
]

def execute_read_only_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute sanctioned read-only tool for evidence collection."""
    if tool_name == "get_path":
        src = args.get("source", "H1")
        tgt = args.get("target", "web-server")
        return trace_path(src, tgt)

    elif tool_name == "get_ospf_neighbors":
        dev = args.get("device", "R1")
        return {"device": dev, "neighbors": eapi_get_ospf(dev)}

    elif tool_name == "get_bgp_peers":
        dev = args.get("device", "R5")
        return {"device": dev, "peers": eapi_get_bgp(dev)}

    elif tool_name == "get_rip_routes":
        dev = args.get("device", "R1")
        return {"device": dev, "routes": eapi_get_rip(dev)}

    elif tool_name == "get_interface_stats":
        dev = args.get("device", "R1")
        return {"device": dev, "interfaces": eapi_get_intf(dev)}

    elif tool_name == "get_logs":
        dev = args.get("device", "R1")
        cnt = args.get("count", 15)
        raw_logs = eapi_get_syslog(dev, cnt)
        redacted_logs = [redact_sensitive_data(l) for l in raw_logs]
        return {"device": dev, "syslog": redacted_logs}

    elif tool_name == "get_config_diff":
        dev = args.get("device", "R1")
        drifts = get_config_drift(dev)
        if drifts:
            diff = drifts[0].get("diff_text", "")
            return {"device": dev, "has_drift": bool(drifts[0].get("has_drift")), "diff": redact_sensitive_data(diff)}
        return {"device": dev, "has_drift": False, "diff": "No drift detected."}

    elif tool_name == "run_ping":
        dev = args.get("device", "R1")
        ip = args.get("target_ip", "198.51.100.10")
        return eapi_run_ping(dev, ip)

    return {"error": f"Unknown tool '{tool_name}'"}
