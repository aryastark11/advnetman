#!/usr/bin/env python3
"""
R7 Telemetry Streamer & Data Lake Ingestion Engine
Continuously collects CPU, Memory, Interface Counters, Route Entries,
and OSPF Adjacencies from R7 via eAPI and streams high-frequency points
directly into InfluxDB (nmas_datalake).
"""

import time
import json
import base64
import urllib.request
import urllib.parse
import sys
import os

INFLUX_URL = os.environ.get("INFLUX_URL", "http://127.0.0.1:8086/write?db=nmas_datalake")
R7_MGMT_IP = os.environ.get("R7_MGMT_IP", "172.20.20.17")
AUTH_STR = base64.b64encode(b"admin:admin").decode("utf-8")

def escape_tag(val):
    if val is None:
        return "unknown"
    return str(val).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

def escape_str(val):
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def query_r7_eapi(cmds):
    url = f"http://{R7_MGMT_IP}/command-api"
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": cmds,
            "format": "json"
        },
        "id": "r7-telemetry-collector"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {AUTH_STR}"}
    )
    with urllib.request.urlopen(req, timeout=4.0) as resp:
        return json.loads(resp.read().decode("utf-8")).get("result", [])

def collect_and_push():
    cmds = [
        "show processes top once",
        "show ip ospf neighbor",
        "show ip route",
        "show interfaces status",
        "show interfaces counters"
    ]
    try:
        results = query_r7_eapi(cmds)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error querying R7 eAPI: {e}", file=sys.stderr)
        return False

    top_info = results[0] if len(results) > 0 else {}
    ospf_info = results[1] if len(results) > 1 else {}
    route_info = results[2] if len(results) > 2 else {}
    intf_status = results[3] if len(results) > 3 else {}
    intf_counters = results[4] if len(results) > 4 else {}

    # 1. CPU & Memory Metrics
    cpu_idle = float(top_info.get("cpuInfo", {}).get("%Cpu(s)", {}).get("idle", 100.0))
    cpu_util = round(100.0 - cpu_idle, 1)
    
    mem_info = top_info.get("memInfo", {}).get("physicalMem", {})
    mem_total_kb = float(mem_info.get("memTotal", 1))
    mem_used_kb = float(mem_info.get("memUsed", 0))
    mem_used_mb = round(mem_used_kb / 1024.0, 1)
    mem_total_mb = round(mem_total_kb / 1024.0, 1)
    mem_pct = round((mem_used_kb / mem_total_kb) * 100.0, 1) if mem_total_kb > 0 else 0.0

    # 2. OSPF Neighbor Metrics
    ospf_inst = ospf_info.get("vrfs", {}).get("default", {}).get("instList", {}).get("1", {})
    ospf_neighbors = ospf_inst.get("ospfNeighborEntries", [])
    ospf_adj_count = len(ospf_neighbors)
    ospf_full_count = sum(1 for n in ospf_neighbors if n.get("adjacencyState", "").lower() == "full")

    # 3. Route Entries Metrics
    routes = route_info.get("vrfs", {}).get("default", {}).get("routes", {})
    route_count = len(routes)

    lines = []

    # Main Summary Point
    summary_line = (
        f"r7_telemetry,hostname=r7 "
        f"cpu_utilization={cpu_util},"
        f"mem_pct={mem_pct},"
        f"mem_used_mb={mem_used_mb},"
        f"mem_total_mb={mem_total_mb},"
        f"route_entries={route_count}i,"
        f"ospf_neighbors={ospf_adj_count}i,"
        f"ospf_full_adjacencies={ospf_full_count}i"
    )
    lines.append(summary_line)

    # Individual OSPF Neighbors
    for n in ospf_neighbors:
        rtr_id = escape_tag(n.get("routerId", "unknown"))
        nbr_ip = escape_tag(n.get("interfaceAddress", "unknown"))
        intf_name = escape_tag(n.get("interfaceName", "unknown"))
        area = escape_tag(n.get("details", {}).get("areaId", "0.0.0.20"))
        state = escape_str(n.get("adjacencyState", "unknown").upper())
        state_code = 8 if state == "FULL" else (1 if state == "DOWN" else 4)

        nbr_line = (
            f"r7_ospf_neighbors,hostname=r7,neighbor_ip={nbr_ip} "
            f"neighbor_router_id=\"{escape_str(rtr_id)}\",interface=\"{escape_str(intf_name)}\","
            f"area=\"{area}\",status=\"{state}\",state_code={state_code}i,dr_state=\"{escape_str(n.get('drState', 'DR'))}\""
        )
        lines.append(nbr_line)

    # Individual Route Entries
    for prefix, r_info in routes.items():
        vias = r_info.get("vias", [{}])
        first_via = vias[0] if vias else {}
        nexthop = escape_tag(first_via.get("nexthopAddr", "DIRECT"))
        r_intf = escape_tag(first_via.get("interface", "connected"))
        rtype = escape_tag(r_info.get("routeType", "unknown"))
        metric = int(r_info.get("metric", 0))

        route_line = (
            f"r7_route_entries,hostname=r7,destination={escape_tag(prefix)} "
            f"nexthop=\"{nexthop}\",protocol=\"{rtype}\",interface=\"{r_intf}\",metric={metric}i"
        )
        lines.append(route_line)

    # Interface Counters
    statuses = intf_status.get("interfaceStatuses", {})
    counters = intf_counters.get("interfaces", {})

    for if_name in ["Ethernet1", "Management0"]:
        st = statuses.get(if_name, {})
        ct = counters.get(if_name, {})
        oper_st = 1 if st.get("lineProtocolStatus") == "up" else 2

        in_octets = int(ct.get("inOctets", 0))
        out_octets = int(ct.get("outOctets", 0))
        in_errors = int(ct.get("totalInErrors", 0))
        out_errors = int(ct.get("totalOutErrors", 0))
        in_discards = int(ct.get("inDiscards", 0))
        out_discards = int(ct.get("outDiscards", 0))

        intf_line = (
            f"r7_interface_counters,hostname=r7,interface={escape_tag(if_name)} "
            f"oper_status={oper_st}i,in_octets={in_octets}i,out_octets={out_octets}i,"
            f"in_errors={in_errors}i,out_errors={out_errors}i,in_discards={in_discards}i,out_discards={out_discards}i"
        )
        lines.append(intf_line)

    # Post to InfluxDB
    data_payload = "\n".join(lines).encode("utf-8")
    for endpoint in [INFLUX_URL, "http://172.20.20.201:8086/write?db=nmas_datalake"]:
        try:
            req = urllib.request.Request(endpoint, data=data_payload, method="POST")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                pass
            return True
        except Exception:
            pass

    return False

def main():
    if "--once" in sys.argv:
        ok = collect_and_push()
        print("Collected and pushed 1 telemetry batch for R7:", "SUCCESS" if ok else "FAILED")
        sys.exit(0 if ok else 1)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] R7 Telemetry Daemon started (Streaming every 5s to InfluxDB)...")
    while True:
        collect_and_push()
        time.sleep(5)

if __name__ == "__main__":
    main()
