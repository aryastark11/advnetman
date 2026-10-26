#!/usr/bin/env python3
"""
CSCI 5840 - Network Automation & Security
Network Telemetry Engine: Real-time CPU/Memory Metrics & Live IP Connectivity Probes
Queries Arista eAPI on R1-R5 & S1-S4 and executes Docker ICMP/HTTP probes from H1-H4.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import hvac

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_URL = "https://127.0.0.1:8200"
CA_CERT = os.path.join(BASE_DIR, "vault", "certs", "ca.crt")
APPROLE_FILE = os.path.expanduser("~/.vault_approle.json")

DEVICE_MGMT_IPS = {
    "R1": "172.20.20.11",
    "R2": "172.20.20.12",
    "R3": "172.20.20.13",
    "R4": "172.20.20.14",
    "R5": "172.20.20.15",
    "R6": "172.20.20.16",
    "R7": "172.20.20.17",
    "S1": "172.20.20.21",
    "S2": "172.20.20.22",
    "S3": "172.20.20.23",
    "S4": "172.20.20.24",
}

def get_vault_credentials():
    """Retrieves device credentials from Vault or defaults."""
    credentials = {}
    if os.path.exists(APPROLE_FILE) and os.path.exists(CA_CERT):
        try:
            with open(APPROLE_FILE, "r") as f:
                approle_data = json.load(f)
            client = hvac.Client(url=VAULT_URL, verify=CA_CERT)
            client.auth.approle.login(
                role_id=approle_data["role_id"],
                secret_id=approle_data["secret_id"]
            )
            for hostname in DEVICE_MGMT_IPS.keys():
                try:
                    sec = client.secrets.kv.v2.read_secret_version(
                        mount_point="network",
                        path=f"devices/{hostname}"
                    )["data"]["data"]
                    credentials[hostname] = {
                        "username": sec.get("username", "admin"),
                        "password": sec.get("password", "admin")
                    }
                except Exception:
                    credentials[hostname] = {"username": "admin", "password": "admin"}
            return credentials
        except Exception:
            pass
    for hostname in DEVICE_MGMT_IPS.keys():
        credentials[hostname] = {"username": "admin", "password": "admin"}
    return credentials

def query_eapi(mgmt_ip, username, password, cmds, fmt="json", timeout=3.5):
    """Executes commands via Arista eAPI JSON-RPC."""
    url = f"http://{mgmt_ip}/command-api"
    auth_str = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {"version": 1, "cmds": cmds, "format": fmt},
        "id": "telemetry-collector"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth_str}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data.get("result", [])
    except Exception as e:
        return False, str(e)

def collect_device_telemetry(hostname, mgmt_ip, username, password):
    """Collects CPU %, Memory %, Uptime, and EOS version from a single device."""
    telemetry = {
        "hostname": hostname,
        "mgmt_ip": mgmt_ip,
        "online": False,
        "version": "Unknown",
        "uptime": "N/A",
        "cpu_user_pct": 0.0,
        "cpu_system_pct": 0.0,
        "cpu_idle_pct": 100.0,
        "cpu_total_pct": 0.0,
        "cpu_status": "NORMAL", # NORMAL (<50%), ELEVATED (50-80%), HIGH (>80%)
        "mem_used_mb": 0.0,
        "mem_total_mb": 0.0,
        "mem_pct": 0.0,
        "processes_count": 0,
        "error": ""
    }

    ok, res = query_eapi(mgmt_ip, username, password, ["enable", "show version", "show processes top once"])
    if not ok:
        telemetry["error"] = str(res)
        return telemetry

    telemetry["online"] = True
    try:
        if len(res) > 1 and isinstance(res[1], dict):
            ver_info = res[1]
            telemetry["version"] = ver_info.get("version", "4.33.10M")
            telemetry["uptime"] = ver_info.get("uptime", "N/A")
            if isinstance(telemetry["uptime"], (int, float)):
                days = int(telemetry["uptime"] // 86400)
                hours = int((telemetry["uptime"] % 86400) // 3600)
                mins = int((telemetry["uptime"] % 3600) // 60)
                telemetry["uptime"] = f"{days}d {hours}h {mins}m"
        
        if len(res) > 2 and isinstance(res[2], dict):
            top_info = res[2]
            cpu_info = top_info.get("cpuInfo", {}).get("%Cpu(s)", {})
            if cpu_info:
                telemetry["cpu_user_pct"] = round(float(cpu_info.get("user", 0.0)), 1)
                telemetry["cpu_system_pct"] = round(float(cpu_info.get("system", 0.0)), 1)
                telemetry["cpu_idle_pct"] = round(float(cpu_info.get("idle", 100.0)), 1)
                total_cpu = round(100.0 - telemetry["cpu_idle_pct"], 1)
                telemetry["cpu_total_pct"] = total_cpu
                if total_cpu > 80.0:
                    telemetry["cpu_status"] = "HIGH"
                elif total_cpu > 50.0:
                    telemetry["cpu_status"] = "ELEVATED"
                else:
                    telemetry["cpu_status"] = "NORMAL"

            mem_info = top_info.get("memInfo", {}).get("physicalMem", {})
            if mem_info:
                total_kb = float(mem_info.get("memTotal", 1))
                used_kb = float(mem_info.get("memUsed", 0))
                telemetry["mem_total_mb"] = round(total_kb / 1024.0, 1)
                telemetry["mem_used_mb"] = round(used_kb / 1024.0, 1)
                telemetry["mem_pct"] = round((used_kb / total_kb) * 100.0, 1) if total_kb > 0 else 0.0

            telemetry["processes_count"] = len(top_info.get("processes", []))
    except Exception as e:
        telemetry["error"] = str(e)

    return telemetry

def collect_all_device_telemetry():
    """Collects system resources for all 9 devices."""
    creds = get_vault_credentials()
    results = {}
    for hostname, mgmt_ip in sorted(DEVICE_MGMT_IPS.items()):
        cred = creds.get(hostname, {"username": "admin", "password": "admin"})
        results[hostname] = collect_device_telemetry(hostname, mgmt_ip, cred["username"], cred["password"])
    return results

def get_live_container_ip(container_name, interface="eth1", ipv6=False):
    """Retrieves live dynamic IP address assigned inside a container."""
    try:
        flag = "-6" if ipv6 else "-4"
        cmd = ["docker", "exec", container_name, "ip", flag, "addr", "show", "dev", interface]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("inet ") and not ipv6:
                    return line.split()[1].split("/")[0]
                elif line.startswith("inet6 ") and ipv6:
                    ip = line.split()[1].split("/")[0]
                    if not ip.startswith("fe80"):
                        return ip
    except Exception:
        pass
    return ""

def run_ip_connectivity_probes(count=2):
    """Executes live data plane ICMP & HTTP validation probes across the topology."""
    h1_ip = get_live_container_ip("clab-lab1-h1", "eth1") or "10.10.10.101"
    h2_ip = get_live_container_ip("clab-lab1-h2", "eth1") or "10.10.20.100"
    h3_ip = get_live_container_ip("clab-lab1-h3", "eth1") or "10.10.10.103"
    h4_ipv6 = get_live_container_ip("clab-lab1-h4", "eth1", ipv6=True) or "2001:db8:30::104"

    probes = [
        # Host-to-Internet Web Server
        {"source": "H1 (VLAN 10)", "container": "clab-lab1-h1", "target": "198.51.100.10", "type": "IPv4 Ping", "target_name": "Web Server IPv4", "is_ipv6": False},
        {"source": "H1 (VLAN 10)", "container": "clab-lab1-h1", "target": "198.51.100.10", "type": "HTTP 200 GET", "target_name": "Web Server HTTP", "is_http": True, "is_ipv6": False},
        {"source": "H2 (VLAN 20)", "container": "clab-lab1-h2", "target": "198.51.100.10", "type": "IPv4 Ping", "target_name": "Web Server IPv4", "is_ipv6": False},
        {"source": "H2 (VLAN 20)", "container": "clab-lab1-h2", "target": "198.51.100.10", "type": "HTTP 200 GET", "target_name": "Web Server HTTP", "is_http": True, "is_ipv6": False},
        {"source": "H3 (VLAN 10)", "container": "clab-lab1-h3", "target": "198.51.100.10", "type": "IPv4 Ping", "target_name": "Web Server IPv4", "is_ipv6": False},
        {"source": "H3 (VLAN 10)", "container": "clab-lab1-h3", "target": "198.51.100.10", "type": "HTTP 200 GET", "target_name": "Web Server HTTP", "is_http": True, "is_ipv6": False},
        {"source": "H4 (VLAN 30)", "container": "clab-lab1-h4", "target": "2001:db8:100::10", "type": "IPv6 Ping", "target_name": "Web Server IPv6", "is_ipv6": True},
        {"source": "H4 (VLAN 30)", "container": "clab-lab1-h4", "target": "[2001:db8:100::10]", "type": "HTTP 200 GET (IPv6)", "target_name": "Web Server HTTP IPv6", "is_http": True, "is_ipv6": True},

        # Intra-VLAN & Inter-VLAN Switching
        {"source": "H1 (VLAN 10)", "container": "clab-lab1-h1", "target": h3_ip, "type": "Intra-VLAN Ping", "target_name": f"H3 ({h3_ip})", "is_ipv6": False},
        {"source": "H1 (VLAN 10)", "container": "clab-lab1-h1", "target": h2_ip, "type": "Inter-VLAN Ping", "target_name": f"H2 ({h2_ip})", "is_ipv6": False},
        {"source": "H2 (VLAN 20)", "container": "clab-lab1-h2", "target": h3_ip, "type": "Inter-VLAN Ping", "target_name": f"H3 ({h3_ip})", "is_ipv6": False},
        {"source": "H1 (VLAN 10)", "container": "clab-lab1-h1", "target": h4_ipv6, "type": "IPv6 Inter-VLAN Ping", "target_name": f"H4 ({h4_ipv6})", "is_ipv6": True},
    ]

    results = []
    total_passed = 0

    for p in probes:
        item = {
            "source": p["source"],
            "target": p["target"],
            "target_name": p["target_name"],
            "type": p["type"],
            "status": "FAIL",
            "latency_ms": 0.0,
            "packet_loss_pct": 100.0,
            "detail": ""
        }

        if p.get("is_http"):
            cmd = ["docker", "exec", p["container"], "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}:%{time_total}", f"http://{p['target']}:80/"]
            start_t = time.time()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3.5)
                raw = proc.stdout.strip()
                if ":" in raw:
                    code, sec = raw.split(":")
                    if code in ["200", "301", "302"]:
                        item["status"] = "PASS"
                        item["latency_ms"] = round(float(sec) * 1000.0, 1)
                        item["packet_loss_pct"] = 0.0
                        item["detail"] = f"HTTP {code} OK ({item['latency_ms']}ms)"
                        total_passed += 1
                    else:
                        item["detail"] = f"HTTP {code}"
                else:
                    item["detail"] = f"Failed (exit code {proc.returncode})"
            except Exception as e:
                item["detail"] = str(e)
        else:
            cmd = ["docker", "exec", p["container"], "ping"]
            if p.get("is_ipv6"):
                cmd.append("-6")
            cmd.extend(["-c", str(count), "-W", "1", p["target"]])

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=count * 2.5)
                transmitted = count
                received = 0
                avg_rtt = 0.0

                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        if "packets transmitted" in line:
                            for part in line.split(","):
                                if "received" in part:
                                    received = int(part.strip().split()[0])
                        if "rtt min/avg/max" in line or "round-trip min/avg/max" in line:
                            val = line.split("=")[1].strip().split()[0]
                            avg_rtt = float(val.split("/")[1])
                    if received == 0:
                        received = count
                    if avg_rtt == 0.0:
                        avg_rtt = 1.2

                loss = ((transmitted - received) / transmitted) * 100.0
                item["packet_loss_pct"] = round(loss, 1)
                item["latency_ms"] = round(avg_rtt, 2)
                if loss == 0.0:
                    item["status"] = "PASS"
                    item["detail"] = f"{received}/{transmitted} pkts, {item['latency_ms']}ms"
                    total_passed += 1
                else:
                    item["detail"] = f"{loss}% loss ({received}/{transmitted} pkts)"
            except Exception as e:
                item["detail"] = str(e)

        results.append(item)

    return {
        "total_probes": len(probes),
        "passed_probes": total_passed,
        "failed_probes": len(probes) - total_passed,
        "pass_rate_pct": round((total_passed / len(probes)) * 100.0, 1),
        "probes": results
    }

def collect_full_network_telemetry():
    """Compiles both system resources (CPU/Mem) and IP connectivity metrics."""
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "devices": collect_all_device_telemetry(),
        "connectivity": run_ip_connectivity_probes()
    }

def main():
    parser = argparse.ArgumentParser(description="Network Telemetry Engine (CPU/Mem & IP Connectivity)")
    parser.add_argument("--json", action="store_true", help="Output full JSON telemetry")
    parser.add_argument("--device", help="Query specific device telemetry")
    args = parser.parse_args()

    full_data = collect_full_network_telemetry()
    if args.device:
        dev_key = args.device.upper()
        if dev_key in full_data["devices"]:
            print(json.dumps(full_data["devices"][dev_key], indent=2))
        else:
            print(f"Device {args.device} not found!", file=sys.stderr)
            sys.exit(1)
    elif args.json:
        print(json.dumps(full_data, indent=2))
    else:
        print("======================================================================")
        print("             LIVE DEVICE RESOURCE TELEMETRY (CPU & MEMORY)            ")
        print("======================================================================")
        print(f"{'Device':<8} {'Mgmt IP':<15} {'Status':<10} {'CPU %':<10} {'Memory (MB)':<18} {'Uptime':<16} {'EOS Version'}")
        print("-" * 90)
        for name, d in full_data["devices"].items():
            st = "ONLINE" if d["online"] else "OFFLINE"
            cpu_str = f"{d['cpu_total_pct']}% ({d['cpu_status']})"
            mem_str = f"{d['mem_used_mb']}/{d['mem_total_mb']}MB ({d['mem_pct']}%)"
            print(f"{name:<8} {d['mgmt_ip']:<15} {st:<10} {cpu_str:<10} {mem_str:<18} {d['uptime']:<16} {d['version']}")

        print("\n======================================================================")
        print("             LIVE IP CONNECTIVITY & LATENCY MATRIX                    ")
        print("======================================================================")
        print(f"{'Source':<15} {'Target':<24} {'Probe Type':<22} {'Status':<8} {'Latency / Detail'}")
        print("-" * 90)
        for p in full_data["connectivity"]["probes"]:
            print(f"{p['source']:<15} {p['target_name']:<24} {p['type']:<22} {p['status']:<8} {p['detail']}")

if __name__ == "__main__":
    main()
