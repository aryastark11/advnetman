#!/usr/bin/env python3
import os
import sys
import time
import json
import socket
import select
import sqlite3
import threading
import subprocess
import base64
import re
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import urllib.request

DATALAKE_DIR = "/opt/nmas/datalake"
BACKUP_HOST = "10.99.99.2"
BACKUP_PORT = 9999
RETENTION_DAYS = 7
DB_PATH = os.path.join(DATALAKE_DIR, "datalake.db")
INFLUX_WRITE_URL = "http://172.20.20.201:8086/write?db=nmas_datalake"

DEVICES = [
    {"name": "r1", "ip": "10.0.0.1", "mgmt_ip": "172.20.20.11", "type": "router"},
    {"name": "r2", "ip": "10.0.0.2", "mgmt_ip": "172.20.20.12", "type": "router"},
    {"name": "r3", "ip": "10.0.0.3", "mgmt_ip": "172.20.20.13", "type": "router"},
    {"name": "r4", "ip": "10.0.0.4", "mgmt_ip": "172.20.20.14", "type": "router"},
    {"name": "r5", "ip": "172.16.35.2", "mgmt_ip": "172.20.20.15", "type": "router"},
    {"name": "s1", "ip": "172.20.20.21", "mgmt_ip": "172.20.20.21", "type": "switch"},
    {"name": "s2", "ip": "172.20.20.22", "mgmt_ip": "172.20.20.22", "type": "switch"},
    {"name": "s3", "ip": "172.20.20.23", "mgmt_ip": "172.20.20.23", "type": "switch"},
    {"name": "s4", "ip": "172.20.20.24", "mgmt_ip": "172.20.20.24", "type": "switch"},
]

OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "hrProcessorLoad": "1.3.6.1.2.1.25.3.3.1.2.1",
    "ssCpuIdle": "1.3.6.1.4.1.2021.11.11.0",
    "ifOperStatus_Et1": "1.3.6.1.2.1.2.2.1.8.1",
    "ifOperStatus_Et2": "1.3.6.1.2.1.2.2.1.8.2",
    "ifInOctets_Et1": "1.3.6.1.2.1.2.2.1.10.1",
    "ifOutOctets_Et1": "1.3.6.1.2.1.2.2.1.16.1"
}

db_lock = threading.Lock()

def get_db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def write_to_influx(lines):
    if not lines:
        return
    if isinstance(lines, str):
        lines = [lines]
    data = "\n".join(lines).encode("utf-8")
    try:
        req = urllib.request.Request(INFLUX_WRITE_URL, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            pass
    except Exception:
        pass

def escape_influx_tag(val):
    if val is None:
        return "unknown"
    return str(val).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

def escape_influx_str(val):
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def init_datalake():
    for sub in ["snmp", "traps", "syslog", "telemetry", "netconf", "grpc"]:
        os.makedirs(os.path.join(DATALAKE_DIR, sub), exist_ok=True)
        
    with db_lock:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS snmp_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, node_name TEXT, node_ip TEXT, metric_name TEXT, oid TEXT, value TEXT, unit TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS snmp_traps (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, source_ip TEXT, source_node TEXT, trap_type TEXT, enterprise_oid TEXT, details_json TEXT, raw_payload TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS syslog_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, facility TEXT, severity INTEGER, severity_name TEXT, hostname TEXT, source_ip TEXT, mnemonic TEXT, message TEXT, is_critical INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS telemetry_streams (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, node_name TEXT, node_ip TEXT, path TEXT, metric_group TEXT, data_json TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS netconf_states (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, node_name TEXT, node_ip TEXT, module TEXT, state_json TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS grpc_telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, node_name TEXT, node_ip TEXT, sensor_path TEXT, payload_json TEXT, encoding TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS retention_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, action TEXT, files_deleted INTEGER, records_pruned INTEGER, details TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS backup_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, status TEXT, files_synced INTEGER, destination_ip TEXT, details TEXT)")
        conn.commit()
        conn.close()
    print("[NMAS] Data Lake initialized at", DATALAKE_DIR)

def append_jsonl(subdir, filename_prefix, record):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = os.path.join(DATALAKE_DIR, subdir, f"{filename_prefix}_{today}.jsonl")
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def snmp_trap_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 162))
    print("[NMAS] SNMP Trap Receiver listening on 0.0.0.0:162 UDP...")

    ip_to_name = {dev["ip"]: dev["name"] for dev in DEVICES}
    ip_to_name.update({dev["mgmt_ip"]: dev["name"] for dev in DEVICES})

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            src_ip = addr[0]
            now_str = datetime.utcnow().isoformat()
            src_node = ip_to_name.get(src_ip, src_ip)

            raw_text = data.decode("latin1", errors="replace")
            trap_type = "generic_trap"
            if "linkDown" in raw_text or "1.3.6.1.6.3.1.1.5.3" in raw_text:
                trap_type = "linkDown"
            elif "linkUp" in raw_text or "1.3.6.1.6.3.1.1.5.4" in raw_text:
                trap_type = "linkUp"
            elif "coldStart" in raw_text or "1.3.6.1.6.3.1.1.5.1" in raw_text:
                trap_type = "coldStart"
            elif "warmStart" in raw_text or "1.3.6.1.6.3.1.1.5.2" in raw_text:
                trap_type = "warmStart"
            elif "auth" in raw_text.lower() or "1.3.6.1.6.3.1.1.5.5" in raw_text:
                trap_type = "authenticationFailure"

            details = {
                "source_ip": src_ip,
                "source_node": src_node,
                "length": len(data),
                "detected_type": trap_type,
                "hex_summary": data[:48].hex()
            }

            record = {
                "timestamp": now_str,
                "source_ip": src_ip,
                "source_node": src_node,
                "trap_type": trap_type,
                "enterprise_oid": "1.3.6.1.4.1.30065",
                "details": details
            }
            append_jsonl("traps", "traps", record)

            with db_lock:
                conn = get_db_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO snmp_traps (timestamp, source_ip, source_node, trap_type, enterprise_oid, details_json, raw_payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (now_str, src_ip, src_node, trap_type, "1.3.6.1.4.1.30065", json.dumps(details), raw_text[:200]))
                conn.commit()
                conn.close()

            influx_line = f'snmp_traps,source_node={escape_influx_tag(src_node)},source_ip={escape_influx_tag(src_ip)},trap_type={escape_influx_tag(trap_type)} count=1i,enterprise_oid="{escape_influx_str("1.3.6.1.4.1.30065")}",summary="{escape_influx_str(trap_type)} from {src_node}"'
            write_to_influx(influx_line)

            print(f"[NMAS TRAP] Received {trap_type} trap from {src_node} ({src_ip})")
        except Exception:
            time.sleep(0.5)

def poll_snmp_device(dev):
    ip = dev["ip"]
    name = dev["name"]
    now_str = datetime.utcnow().isoformat()
    target_ips = [ip] if ip == dev["mgmt_ip"] else [ip, dev["mgmt_ip"]]

    influx_lines = []

    for target in target_ips:
        for metric_name, oid in OIDS.items():
            cmd = f"snmpget -v 2c -c public -t 1 -r 1 {target} {oid}"
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2.5)
                if res.returncode == 0 and "=" in res.stdout:
                    raw_val = res.stdout.strip().split("=", 1)[1].strip()
                    val = raw_val.split(":", 1)[1].strip() if ":" in raw_val else raw_val
                    val = val.replace(chr(34), "").replace(chr(39), "").strip()

                    unit = "gauge"
                    num_val = None
                    try:
                        num_val = float(re.sub(r"[^\d.]", "", val)) if re.search(r"\d", val) else None
                    except Exception:
                        pass

                    if "UpTime" in metric_name:
                        unit = "timeticks"
                        if num_val is not None:
                            influx_lines.append(f'snmp_uptime,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(target)} uptime_timeticks={num_val},uptime_seconds={num_val/100.0:.2f}')
                    elif "Octets" in metric_name:
                        unit = "bytes"
                        intf = "Ethernet1" if "Et1" in metric_name else "Ethernet2"
                        field_name = "in_octets" if "InOctets" in metric_name else "out_octets"
                        if num_val is not None:
                            influx_lines.append(f'interface_traffic,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(target)},interface={escape_influx_tag(intf)} {field_name}={int(num_val)}i')
                    elif "Load" in metric_name or "Cpu" in metric_name:
                        unit = "percent"
                        if num_val is not None:
                            influx_lines.append(f'snmp_cpu,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(target)} cpu_load={num_val:.2f}')

                    num_field = f",value_numeric={num_val:.2f}" if num_val is not None else ""
                    influx_lines.append(f'snmp_metrics,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(target)},metric_name={escape_influx_tag(metric_name)},unit={escape_influx_tag(unit)} oid="{escape_influx_str(oid)}",value_str="{escape_influx_str(val)}"{num_field}')

                    record = {
                        "timestamp": now_str,
                        "node_name": name,
                        "node_ip": target,
                        "metric_name": metric_name,
                        "oid": oid,
                        "value": val,
                        "unit": unit
                    }
                    append_jsonl("snmp", "snmp", record)

                    with db_lock:
                        conn = get_db_conn()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO snmp_metrics (timestamp, node_name, node_ip, metric_name, oid, value, unit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (now_str, name, target, metric_name, oid, str(val), unit))
                        conn.commit()
                        conn.close()
            except Exception:
                pass

    if influx_lines:
        write_to_influx(influx_lines)

def snmp_poller_loop():
    time.sleep(5)
    while True:
        for dev in DEVICES:
            threading.Thread(target=poll_snmp_device, args=(dev,), daemon=True).start()
        time.sleep(20)

SEVERITY_NAMES = {
    0: "EMERGENCY", 1: "ALERT", 2: "CRITICAL", 3: "ERROR",
    4: "WARNING", 5: "NOTICE", 6: "INFORMATIONAL", 7: "DEBUG"
}

FACILITY_NAMES = {
    0: "kern", 1: "user", 2: "mail", 3: "daemon", 4: "auth", 5: "syslog",
    16: "local0", 17: "local1", 18: "local2", 19: "local3", 20: "local4",
    21: "local5", 22: "local6", 23: "local7"
}

def syslog_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 514))
    print("[NMAS] Syslog Receiver listening on 0.0.0.0:514 UDP...")

    ip_to_name = {dev["ip"]: dev["name"] for dev in DEVICES}
    ip_to_name.update({dev["mgmt_ip"]: dev["name"] for dev in DEVICES})

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            src_ip = addr[0]
            now_str = datetime.utcnow().isoformat()
            raw_msg = data.decode("utf-8", errors="replace").strip()

            facility = "local0"
            severity = 6
            message = raw_msg
            hostname = ip_to_name.get(src_ip, src_ip)
            mnemonic = "GENERIC"

            if raw_msg.startswith("<"):
                end_pri = raw_msg.find(">")
                if end_pri != -1:
                    pri_val = int(raw_msg[1:end_pri])
                    fac_num = pri_val >> 3
                    severity = pri_val & 7
                    facility = FACILITY_NAMES.get(fac_num, f"local{fac_num}")
                    message = raw_msg[end_pri+1:].strip()

            if "%" in message:
                parts = message.split("%", 1)[1]
                mnemonic_candidate = parts.split(":", 1)[0].strip()
                if mnemonic_candidate:
                    mnemonic = mnemonic_candidate

            is_critical = 1 if severity <= 3 else 0
            sev_name = SEVERITY_NAMES.get(severity, "UNKNOWN")

            record = {
                "timestamp": now_str,
                "facility": facility,
                "severity": severity,
                "severity_name": sev_name,
                "hostname": hostname,
                "source_ip": src_ip,
                "mnemonic": mnemonic,
                "message": message,
                "is_critical": is_critical
            }
            append_jsonl("syslog", "syslog", record)

            with db_lock:
                conn = get_db_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO syslog_events (timestamp, facility, severity, severity_name, hostname, source_ip, mnemonic, message, is_critical) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (now_str, facility, severity, sev_name, hostname, src_ip, mnemonic, message, is_critical))
                conn.commit()
                conn.close()

            influx_line = f'syslog_events,hostname={escape_influx_tag(hostname)},source_ip={escape_influx_tag(src_ip)},facility={escape_influx_tag(facility)},severity_name={escape_influx_tag(sev_name)},mnemonic={escape_influx_tag(mnemonic)},is_critical={is_critical} severity_level={severity}i,event_count=1i,message="{escape_influx_str(message)}"'
            write_to_influx(influx_line)

            if is_critical:
                print(f"[NMAS CRITICAL SYSLOG] [{sev_name}] from {hostname} ({src_ip}): {message}")
        except Exception:
            time.sleep(0.5)

def query_device_eapi(dev):
    now_str = datetime.utcnow().isoformat()
    name = dev["name"]
    ip = dev["ip"]

    url = f"http://{ip}/command-api"
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": [
                "show version",
                "show interfaces status",
                "show ip bgp summary",
                "show ip ospf neighbor",
                "show processes top once"
            ],
            "format": "json"
        },
        "id": "nmas-telemetry"
    }

    auth_str = base64.b64encode(b"admin:admin").decode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_str}"
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                res_data = json.loads(resp.read().decode("utf-8"))
                results = res_data.get("result", [])
                
                version_info = results[0] if len(results) > 0 else {}
                intf_info = results[1] if len(results) > 1 else {}
                bgp_info = results[2] if len(results) > 2 else {}
                ospf_info = results[3] if len(results) > 3 else {}
                top_procs = results[4] if len(results) > 4 else {}

                telem_record = {
                    "timestamp": now_str,
                    "node_name": name,
                    "node_ip": ip,
                    "path": "/eos/telemetry/runtime",
                    "metric_group": "system_and_protocols",
                    "data": {
                        "version": version_info,
                        "interfaces": intf_info,
                        "bgp": bgp_info,
                        "ospf": ospf_info,
                        "top_processes": top_procs
                    }
                }
                append_jsonl("telemetry", "telemetry", telem_record)

                netconf_record = {
                    "timestamp": now_str,
                    "node_name": name,
                    "node_ip": ip,
                    "module": "openconfig-interfaces:interfaces",
                    "state": intf_info
                }
                append_jsonl("netconf", "netconf", netconf_record)

                with db_lock:
                    conn = get_db_conn()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO telemetry_streams (timestamp, node_name, node_ip, path, metric_group, data_json) VALUES (?, ?, ?, ?, ?, ?)",
                                (now_str, name, ip, "/eos/telemetry/runtime", "system_and_protocols", json.dumps(telem_record["data"])))
                    
                    cur.execute("INSERT INTO netconf_states (timestamp, node_name, node_ip, module, state_json) VALUES (?, ?, ?, ?, ?)",
                                (now_str, name, ip, "openconfig-interfaces", json.dumps(netconf_record["state"])))
                    conn.commit()
                    conn.close()

                # Extract protocol counts for InfluxDB
                bgp_vrfs = bgp_info.get("vrfs", {})
                bgp_peers = bgp_vrfs.get("default", {}).get("peers", {})
                bgp_up_count = sum(1 for p in bgp_peers.values() if p.get("peerState") == "Established")
                
                ospf_inst = ospf_info.get("vrfs", {}).get("default", {}).get("instList", {})
                ospf_adj_count = sum(len(inst.get("ospfNeighborList", [])) for inst in ospf_inst.values()) if isinstance(ospf_inst, dict) else 0

                influx_line = f'streaming_telemetry,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(ip)},metric_group=system_and_protocols bgp_peers_established={bgp_up_count}i,ospf_neighbors={ospf_adj_count}i,eos_version="{escape_influx_str(version_info.get("version", "vEOS-lab"))}",count=1i'
                write_to_influx(influx_line)

    except Exception:
        pass

def telemetry_collector_loop():
    time.sleep(5)
    while True:
        for dev in DEVICES:
            threading.Thread(target=query_device_eapi, args=(dev,), daemon=True).start()
        time.sleep(20)

def query_device_grpc(dev):
    now_str = datetime.utcnow().isoformat()
    name = dev["name"]
    mgmt_ip = dev["mgmt_ip"]
    target = f"{mgmt_ip}:6030"

    paths = [
        "/system/state",
        "/interfaces/interface[name=Ethernet1]/state",
        "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors"
    ]

    for p in paths:
        try:
            cmd = [
                "gnmic", "-a", target,
                "-u", "admin", "-p", "admin",
                "--insecure",
                "--encoding", "json_ietf",
                "get",
                "--path", p
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                record = {
                    "timestamp": now_str,
                    "node_name": name,
                    "node_ip": mgmt_ip,
                    "transport": "gRPC",
                    "protocol": "gNMI",
                    "sensor_path": p,
                    "data": data
                }
                append_jsonl("grpc", f"grpc_{name}", record)

                with db_lock:
                    conn = get_db_conn()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO grpc_telemetry (timestamp, node_name, node_ip, sensor_path, payload_json, encoding) VALUES (?, ?, ?, ?, ?, ?)",
                                (now_str, name, mgmt_ip, p, json.dumps(data), "json_ietf"))
                    conn.commit()
                    conn.close()

                # Influx metric line
                summary_str = f"gNMI {p} OK"
                influx_line = f'grpc_telemetry,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(mgmt_ip)},sensor_path={escape_influx_tag(p)},protocol=gNMI,encoding=json_ietf count=1i,status_code=0i,status="ESTABLISHED",summary="{escape_influx_str(summary_str)}"'
                write_to_influx(influx_line)
        except Exception:
            pass

def grpc_collector_loop():
    time.sleep(3)
    print("[NMAS] gRPC / gNMI Streaming Telemetry Collector active...")
    while True:
        for dev in DEVICES:
            threading.Thread(target=query_device_grpc, args=(dev,), daemon=True).start()
        time.sleep(15)

def sync_datalake_to_backup():
    time.sleep(10)
    while True:
        now_str = datetime.utcnow().isoformat()
        files_synced = 0
        try:
            for root, dirs, files in os.walk(DATALAKE_DIR):
                for f in files:
                    if f.endswith(".jsonl") or f.endswith(".log"):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, DATALAKE_DIR)
                        with open(full_path, "r", encoding="utf-8") as file_handle:
                            content = file_handle.read()
                        
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(4.0)
                        s.connect((BACKUP_HOST, BACKUP_PORT))
                        req = json.dumps({"action": "sync_file", "rel_path": rel_path, "content": content})
                        s.sendall(req.encode("utf-8"))
                        s.shutdown(socket.SHUT_WR)
                        s.recv(4096)
                        s.close()
                        files_synced += 1

            with db_lock:
                conn = get_db_conn()
                sql_dump = "\n".join(conn.iterdump())
                conn.close()

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((BACKUP_HOST, BACKUP_PORT))
            req = json.dumps({"action": "sync_db_dump", "sql_dump": sql_dump})
            s.sendall(req.encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            s.recv(4096)
            s.close()

            with db_lock:
                conn = get_db_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO backup_logs (timestamp, status, files_synced, destination_ip, details) VALUES (?, ?, ?, ?, ?)",
                            (now_str, "SUCCESS", files_synced, BACKUP_HOST, f"Synchronized {files_synced} files and database dump to {BACKUP_HOST}"))
                conn.commit()
                conn.close()

            influx_line = f'backup_logs,destination_ip={escape_influx_tag(BACKUP_HOST)},status=SUCCESS files_synced={files_synced}i,success=1i'
            write_to_influx(influx_line)

            with open(os.path.join(DATALAKE_DIR, "backup.log"), "a") as bf:
                bf.write(f"[{now_str}] Backup completed successfully to {BACKUP_HOST}: {files_synced} files synced.\n")

        except Exception as e:
            with open(os.path.join(DATALAKE_DIR, "backup.log"), "a") as bf:
                bf.write(f"[{now_str}] Backup retry/log to {BACKUP_HOST}: {str(e)}\n")
            influx_line = f'backup_logs,destination_ip={escape_influx_tag(BACKUP_HOST)},status=ERROR files_synced=0i,success=0i'
            write_to_influx(influx_line)
        
        time.sleep(25)

def enforce_7day_retention():
    while True:
        try:
            now = datetime.utcnow()
            cutoff_date = now - timedelta(days=RETENTION_DAYS)
            cutoff_ts = cutoff_date.isoformat()
            deleted_files = []
            records_pruned = 0

            for root, dirs, files in os.walk(DATALAKE_DIR):
                for f in files:
                    if f.endswith(".log") or f.endswith(".db") or f.endswith(".db-wal") or f.endswith(".db-shm") or f.endswith(".db-journal"):
                        continue
                    full_path = os.path.join(root, f)
                    try:
                        mtime = datetime.utcfromtimestamp(os.path.getmtime(full_path))
                        if mtime < cutoff_date:
                            os.remove(full_path)
                            deleted_files.append(full_path)
                    except Exception:
                        pass

            with db_lock:
                conn = get_db_conn()
                cur = conn.cursor()
                for table in ["snmp_metrics", "snmp_traps", "syslog_events", "telemetry_streams", "netconf_states", "grpc_telemetry"]:
                    cur.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_ts,))
                    records_pruned += cur.rowcount
                
                cur.execute("INSERT INTO retention_logs (timestamp, action, files_deleted, records_pruned, details) VALUES (?, ?, ?, ?, ?)",
                            (now.isoformat(), "7_DAY_PURGE", len(deleted_files), records_pruned, f"Cutoff: {cutoff_ts}. Enforced 7-day retention."))
                conn.commit()
                conn.close()

            influx_line = f'retention_logs,action=7_DAY_PURGE files_deleted={len(deleted_files)}i,records_pruned={records_pruned}i,retention_days={RETENTION_DAYS}i'
            write_to_influx(influx_line)

            with open(os.path.join(DATALAKE_DIR, "retention.log"), "a") as rf:
                rf.write(f"[{now.isoformat()}] 7-Day Retention cycle completed. Deleted {len(deleted_files)} files, pruned {records_pruned} database records.\n")
                for df in deleted_files:
                    rf.write(f"  - Purged file: {df}\n")

        except Exception:
            pass
        time.sleep(300)

def publish_datalake_status_loop():
    time.sleep(5)
    while True:
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM snmp_metrics")
            snmp_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM snmp_traps")
            traps_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM syslog_events")
            syslog_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM syslog_events WHERE is_critical = 1")
            crit_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM telemetry_streams")
            telem_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM grpc_telemetry")
            grpc_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM backup_logs")
            backup_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM retention_logs")
            ret_c = cur.fetchone()[0]
            conn.close()

            line = f'datalake_summary,status=online,backup_node={escape_influx_tag(BACKUP_HOST)} snmp_metrics_total={snmp_c}i,snmp_traps_total={traps_c}i,syslog_events_total={syslog_c}i,critical_syslogs_total={crit_c}i,telemetry_streams_total={telem_c}i,grpc_telemetry_total={grpc_c}i,backup_syncs_total={backup_c}i,retention_cycles_total={ret_c}i,retention_days={RETENTION_DAYS}i'
            write_to_influx(line)
        except Exception:
            pass
        time.sleep(10)

def backfill_datalake_history():
    print("[NMAS] Backfilling recent Data Lake history to InfluxDB...")
    try:
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Backfill SNMP metrics
        cur.execute("SELECT * FROM snmp_metrics ORDER BY id DESC LIMIT 500")
        rows = cur.fetchall()
        snmp_lines = []
        for r in rows:
            name = r["node_name"]
            ip = r["node_ip"]
            metric_name = r["metric_name"]
            unit = r["unit"]
            val = r["value"]
            oid = r["oid"]
            num_val = None
            try:
                num_val = float(re.sub(r"[^\d.]", "", val)) if re.search(r"\d", val) else None
            except Exception:
                pass
            if "Load" in metric_name or "Cpu" in metric_name:
                if num_val is not None:
                    snmp_lines.append(f'snmp_cpu,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(ip)} cpu_load={num_val:.2f}')
            elif "UpTime" in metric_name and num_val is not None:
                snmp_lines.append(f'snmp_uptime,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(ip)} uptime_timeticks={num_val},uptime_seconds={num_val/100.0:.2f}')
            elif "Octets" in metric_name and num_val is not None:
                intf = "Ethernet1" if "Et1" in metric_name else "Ethernet2"
                field_name = "in_octets" if "InOctets" in metric_name else "out_octets"
                snmp_lines.append(f'interface_traffic,node_name={escape_influx_tag(name)},node_ip={escape_influx_tag(ip)},interface={escape_influx_tag(intf)} {field_name}={int(num_val)}i')

        write_to_influx(snmp_lines)

        # 2. Backfill Syslog
        cur.execute("SELECT * FROM syslog_events ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
        syslog_lines = []
        for r in rows:
            syslog_lines.append(f'syslog_events,hostname={escape_influx_tag(r["hostname"])},source_ip={escape_influx_tag(r["source_ip"])},facility={escape_influx_tag(r["facility"])},severity_name={escape_influx_tag(r["severity_name"])},mnemonic={escape_influx_tag(r["mnemonic"])},is_critical={r["is_critical"]} severity_level={r["severity"]}i,event_count=1i,message="{escape_influx_str(r["message"])}"')
        write_to_influx(syslog_lines)

        # 3. Backfill gRPC
        cur.execute("SELECT * FROM grpc_telemetry ORDER BY id DESC LIMIT 100")
        rows = cur.fetchall()
        grpc_lines = []
        for r in rows:
            grpc_lines.append(f'grpc_telemetry,node_name={escape_influx_tag(r["node_name"])},node_ip={escape_influx_tag(r["node_ip"])},sensor_path={escape_influx_tag(r["sensor_path"])},protocol=gNMI,encoding={escape_influx_tag(r["encoding"])} count=1i,status_code=0i,status="ESTABLISHED",summary="gNMI Telemetry Record"')
        write_to_influx(grpc_lines)

        conn.close()
        print(f"[NMAS] Backfill completed ({len(snmp_lines)} snmp, {len(syslog_lines)} syslog, {len(grpc_lines)} grpc).")
    except Exception as e:
        print(f"[NMAS] Backfill error: {e}")

class DataLakeAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        resp_data = {}
        if path == "/api/datalake/summary":
            cur.execute("SELECT COUNT(*) as c FROM snmp_metrics")
            snmp_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM snmp_traps")
            traps_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM syslog_events")
            syslog_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM syslog_events WHERE is_critical = 1")
            crit_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM telemetry_streams")
            telem_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM netconf_states")
            netconf_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM grpc_telemetry")
            grpc_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM backup_logs")
            backup_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) as c FROM retention_logs")
            ret_c = cur.fetchone()["c"]
            
            resp_data = {
                "status": "online",
                "retention_period_days": RETENTION_DAYS,
                "backup_destination": BACKUP_HOST,
                "counts": {
                    "snmp_metrics": snmp_c,
                    "snmp_traps": traps_c,
                    "syslog_events": syslog_c,
                    "critical_syslogs": crit_c,
                    "telemetry_streams": telem_c,
                    "netconf_states": netconf_c,
                    "grpc_telemetry": grpc_c,
                    "backup_syncs": backup_c,
                    "retention_cycles": ret_c
                },
                "datalake_path": DATALAKE_DIR,
                "timestamp": datetime.utcnow().isoformat()
            }
        elif path == "/api/datalake/snmp":
            cur.execute("SELECT * FROM snmp_metrics ORDER BY id DESC LIMIT 50")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/traps":
            cur.execute("SELECT * FROM snmp_traps ORDER BY id DESC LIMIT 50")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/syslog":
            cur.execute("SELECT * FROM syslog_events ORDER BY id DESC LIMIT 50")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/syslog/critical":
            cur.execute("SELECT * FROM syslog_events WHERE is_critical = 1 ORDER BY id DESC LIMIT 50")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/telemetry":
            cur.execute("SELECT * FROM telemetry_streams ORDER BY id DESC LIMIT 20")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/netconf":
            cur.execute("SELECT * FROM netconf_states ORDER BY id DESC LIMIT 20")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/grpc":
            cur.execute("SELECT * FROM grpc_telemetry ORDER BY id DESC LIMIT 50")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/backup":
            cur.execute("SELECT * FROM backup_logs ORDER BY id DESC LIMIT 20")
            resp_data = [dict(row) for row in cur.fetchall()]
        elif path == "/api/datalake/retention":
            cur.execute("SELECT * FROM retention_logs ORDER BY id DESC LIMIT 20")
            resp_data = [dict(row) for row in cur.fetchall()]
        else:
            resp_data = {"error": "Endpoint not found", "available_endpoints": [
                "/api/datalake/summary",
                "/api/datalake/snmp",
                "/api/datalake/traps",
                "/api/datalake/syslog",
                "/api/datalake/syslog/critical",
                "/api/datalake/telemetry",
                "/api/datalake/netconf",
                "/api/datalake/grpc",
                "/api/datalake/backup",
                "/api/datalake/retention"
            ]}

        conn.close()

        body = json.dumps(resp_data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def start_http_api():
    server = HTTPServer(("0.0.0.0", 8080), DataLakeAPIHandler)
    print("[NMAS] REST Data Lake Query API listening on http://0.0.0.0:8080...")
    server.serve_forever()

if __name__ == "__main__":
    init_datalake()
    backfill_datalake_history()
    
    threads = [
        threading.Thread(target=snmp_trap_receiver, daemon=True),
        threading.Thread(target=snmp_poller_loop, daemon=True),
        threading.Thread(target=syslog_receiver, daemon=True),
        threading.Thread(target=telemetry_collector_loop, daemon=True),
        threading.Thread(target=grpc_collector_loop, daemon=True),
        threading.Thread(target=sync_datalake_to_backup, daemon=True),
        threading.Thread(target=enforce_7day_retention, daemon=True),
        threading.Thread(target=publish_datalake_status_loop, daemon=True),
        threading.Thread(target=start_http_api, daemon=True),
    ]
    
    for t in threads:
        t.start()
        
    print("[NMAS] All monitoring, collection, backup, and retention services active.")
    while True:
        time.sleep(3600)
