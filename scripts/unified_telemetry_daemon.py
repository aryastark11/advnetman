#!/usr/bin/env python3
"""
Unified Network Telemetry Streamer & Data Lake Ingestion Daemon
Continuously collects CPU, Memory, Interface Counters, Route Entries,
and OSPF/BGP Adjacencies from all network devices (R1-R7, S1-S4) via eAPI
and streams high-frequency telemetry points directly into InfluxDB (nmas_datalake).
Supports per-device filtering and Grafana template variables.
"""

import time
import json
import base64
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import sys
import os

INFLUX_URL = os.environ.get("INFLUX_URL", "http://127.0.0.1:8086/write?db=nmas_datalake")
AUTH_STR = base64.b64encode(b"admin:admin").decode("utf-8")

DEVICES = {
    "r1": "172.20.20.11",
    "r2": "172.20.20.12",
    "r3": "172.20.20.13",
    "r4": "172.20.20.14",
    "r5": "172.20.20.15",
    "r6": "172.20.20.16",
    "r7": "172.20.20.17",
    "s1": "172.20.20.21",
    "s2": "172.20.20.22",
    "s3": "172.20.20.23",
    "s4": "172.20.20.24",
}

ROUTERS = {"r1", "r2", "r3", "r4", "r5", "r6", "r7"}

def escape_tag(val):
    if val is None:
        return "unknown"
    return str(val).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

def escape_str(val):
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def query_device_eapi(mgmt_ip, cmds, timeout=3.5):
    url = f"http://{mgmt_ip}/command-api"
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": cmds,
            "format": "json"
        },
        "id": "unified-telemetry"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {AUTH_STR}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("result", [])

def poll_device(name, ip):
    is_router = name in ROUTERS
    if is_router:
        cmds = [
            "show processes top once",
            "show ip ospf neighbor",
            "show ip route",
            "show interfaces status",
            "show interfaces counters"
        ]
    else:
        cmds = [
            "show processes top once",
            "show interfaces status",
            "show interfaces counters"
        ]

    try:
        results = query_device_eapi(ip, cmds)
    except Exception as e:
        return []

    top_info = results[0] if len(results) > 0 else {}
    if is_router:
        ospf_info = results[1] if len(results) > 1 else {}
        route_info = results[2] if len(results) > 2 else {}
        intf_status = results[3] if len(results) > 3 else {}
        intf_counters = results[4] if len(results) > 4 else {}
    else:
        ospf_info = {}
        route_info = {}
        intf_status = results[1] if len(results) > 1 else {}
        intf_counters = results[2] if len(results) > 2 else {}

    # CPU & Memory
    cpu_idle = float(top_info.get("cpuInfo", {}).get("%Cpu(s)", {}).get("idle", 100.0))
    cpu_util = round(100.0 - cpu_idle, 1)

    mem_info = top_info.get("memInfo", {}).get("physicalMem", {})
    mem_total_kb = float(mem_info.get("memTotal", 1))
    mem_used_kb = float(mem_info.get("memUsed", 0))
    mem_used_mb = round(mem_used_kb / 1024.0, 1)
    mem_total_mb = round(mem_total_kb / 1024.0, 1)
    mem_pct = round((mem_used_kb / mem_total_kb) * 100.0, 1) if mem_total_kb > 0 else 0.0

    # OSPF Neighbors
    ospf_inst = ospf_info.get("vrfs", {}).get("default", {}).get("instList", {}).get("1", {})
    ospf_neighbors = ospf_inst.get("ospfNeighborEntries", [])
    ospf_adj_count = len(ospf_neighbors)
    ospf_full_count = sum(1 for n in ospf_neighbors if n.get("adjacencyState", "").lower() == "full")

    # Route Entries
    routes = route_info.get("vrfs", {}).get("default", {}).get("routes", {})
    route_count = len(routes)

    lines = []

    # Main Device Telemetry Summary
    line = (
        f"device_telemetry,hostname={name} "
        f"cpu_utilization={cpu_util},"
        f"mem_pct={mem_pct},"
        f"mem_used_mb={mem_used_mb},"
        f"mem_total_mb={mem_total_mb},"
        f"route_entries={route_count}i,"
        f"ospf_neighbors={ospf_adj_count}i,"
        f"ospf_full_adjacencies={ospf_full_count}i"
    )
    lines.append(line)

    # Backward compatibility for R6/R7 daemons
    if name == "r6":
        r6_line = (
            f"r6_telemetry,hostname=r6 "
            f"cpu_utilization={cpu_util},"
            f"mem_pct={mem_pct},"
            f"mem_used_mb={mem_used_mb},"
            f"mem_total_mb={mem_total_mb},"
            f"route_entries={route_count}i,"
            f"ospf_neighbors={ospf_adj_count}i,"
            f"ospf_full_adjacencies={ospf_full_count}i"
        )
        lines.append(r6_line)
    elif name == "r7":
        r7_line = (
            f"r7_telemetry,hostname=r7 "
            f"cpu_utilization={cpu_util},"
            f"mem_pct={mem_pct},"
            f"mem_used_mb={mem_used_mb},"
            f"mem_total_mb={mem_total_mb},"
            f"route_entries={route_count}i,"
            f"ospf_neighbors={ospf_adj_count}i,"
            f"ospf_full_adjacencies={ospf_full_count}i"
        )
        lines.append(r7_line)

    # OSPF Neighbors
    for n in ospf_neighbors:
        rtr_id = escape_tag(n.get("routerId", "unknown"))
        nbr_ip = escape_tag(n.get("interfaceAddress", "unknown"))
        intf_name = escape_tag(n.get("interfaceName", "unknown"))
        area = escape_tag(n.get("details", {}).get("areaId", "0.0.0.0"))
        state = escape_str(n.get("adjacencyState", "unknown").upper())
        state_code = 8 if state == "FULL" else (1 if state == "DOWN" else 4)

        nbr_line = (
            f"device_ospf_neighbors,hostname={name},neighbor_ip={nbr_ip} "
            f"neighbor_router_id=\"{escape_str(rtr_id)}\",interface=\"{escape_str(intf_name)}\","
            f"area=\"{area}\",status=\"{state}\",state_code={state_code}i,dr_state=\"{escape_str(n.get('drState', 'DR'))}\""
        )
        lines.append(nbr_line)

        if name == "r6":
            lines.append(nbr_line.replace("device_ospf_neighbors", "r6_ospf_neighbors"))
        elif name == "r7":
            lines.append(nbr_line.replace("device_ospf_neighbors", "r7_ospf_neighbors"))

    # Route Entries
    for prefix, r_info in routes.items():
        vias = r_info.get("vias", [{}])
        first_via = vias[0] if vias else {}
        nexthop = escape_tag(first_via.get("nexthopAddr", "DIRECT"))
        r_intf = escape_tag(first_via.get("interface", "connected"))
        rtype = escape_tag(r_info.get("routeType", "unknown"))
        metric = int(r_info.get("metric", 0))

        route_line = (
            f"device_route_entries,hostname={name},destination={escape_tag(prefix)} "
            f"nexthop=\"{nexthop}\",protocol=\"{rtype}\",interface=\"{r_intf}\",metric={metric}i"
        )
        lines.append(route_line)

        if name == "r6":
            lines.append(route_line.replace("device_route_entries", "r6_route_entries"))
        elif name == "r7":
            lines.append(route_line.replace("device_route_entries", "r7_route_entries"))

    # Interface Counters
    statuses = intf_status.get("interfaceStatuses", {})
    counters = intf_counters.get("interfaces", {})

    for if_name, st in statuses.items():
        if not (if_name.startswith("Ethernet") or if_name.startswith("Management") or if_name.startswith("Tunnel")):
            continue
        ct = counters.get(if_name, {})
        oper_st = 1 if st.get("lineProtocolStatus") == "up" else 2

        in_octets = int(ct.get("inOctets", 0))
        out_octets = int(ct.get("outOctets", 0))
        in_errors = int(ct.get("totalInErrors", 0))
        out_errors = int(ct.get("totalOutErrors", 0))

        if_line = (
            f"device_interface_counters,hostname={name},interface={escape_tag(if_name)} "
            f"status=\"{st.get('lineProtocolStatus', 'unknown')}\",oper_status={oper_st}i,"
            f"in_octets={in_octets}i,out_octets={out_octets}i,in_errors={in_errors}i,out_errors={out_errors}i"
        )
        lines.append(if_line)

        if name == "r6":
            lines.append(if_line.replace("device_interface_counters", "r6_interface_counters"))
        elif name == "r7":
            lines.append(if_line.replace("device_interface_counters", "r7_interface_counters"))

    return lines

def collect_and_push_all():
    all_lines = []
    with ThreadPoolExecutor(max_workers=len(DEVICES)) as pool:
        results = pool.map(lambda item: poll_device(item[0], item[1]), DEVICES.items())
        for lines in results:
            all_lines.extend(lines)

    if not all_lines:
        return False

    body = "\n".join(all_lines).encode("utf-8")
    try:
        req = urllib.request.Request(
            INFLUX_URL,
            data=body,
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] InfluxDB write error: {e}", file=sys.stderr)
        return False

def main():
    print("=" * 70)
    print("  Unified Network Telemetry Daemon (R1-R7, S1-S4) -> InfluxDB")
    print(f"  Target InfluxDB: {INFLUX_URL}")
    print(f"  Monitored Devices: {', '.join(sorted(DEVICES.keys()))}")
    print("=" * 70)

    consecutive_errors = 0
    while True:
        t0 = time.time()
        ok = collect_and_push_all()
        elapsed = round((time.time() - t0) * 1000, 1)

        if ok:
            consecutive_errors = 0
            # Print brief heartbeat every 30s
            if int(time.time()) % 30 < 5:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telemetry synced across 11 devices ({elapsed}ms)")
        else:
            consecutive_errors += 1
            if consecutive_errors % 6 == 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Warning: Telemetry write failed {consecutive_errors} times", file=sys.stderr)

        time.sleep(max(1.0, 5.0 - (time.time() - t0)))

if __name__ == "__main__":
    main()
