#!/usr/bin/env python3
import subprocess
import json
import urllib.request
import base64
import os
import sys

def test(name, check_fn):
    try:
        ok, msg = check_fn()
    except Exception as e:
        ok, msg = False, str(e)
    status = " \033[92mPASS\033[0m" if ok else " \033[91mFAIL\033[0m"
    print(f"[{status}] {name}")
    if not ok and msg:
        print(f"       Details: {msg[:160]}")
    return ok

print("="*75)
print("   LABS 2 & 3 PART 2: GRAFANA DASHBOARDS & NETWORKX TRAFFIC FLOWS   ")
print("="*75)

auth_header = {"Authorization": "Basic " + base64.b64encode(b"admin:admin").decode("utf-8")}
results = []

# 1. InfluxDB Time-Series Engine
def test_influxdb():
    req = urllib.request.Request("http://172.20.20.201:8086/ping")
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status == 204 or resp.status == 200, "InfluxDB responding on port 8086"
results.append(test("InfluxDB Time-Series Engine Active (172.20.20.201:8086)", test_influxdb))

# 2. InfluxDB Data Lake Measurements
def test_influx_measurements():
    req = urllib.request.Request("http://172.20.20.201:8086/query?db=nmas_datalake&q=SHOW+MEASUREMENTS")
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        series = data.get("results", [{}])[0].get("series", [{}])[0].get("values", [])
        m_names = [s[0] for s in series]
        expected = ["snmp_cpu", "syslog_events", "grpc_telemetry", "datalake_summary", "interface_traffic"]
        found = all(e in m_names for e in expected)
        return found, f"Measurements: {m_names}"
results.append(test("InfluxDB Data Lake Measurements Populated (SNMP, Syslog, gRPC, Retention)", test_influx_measurements))

# 3. Grafana Server Health
def test_grafana_health():
    req = urllib.request.Request("http://127.0.0.1:3000/api/health", headers=auth_header)
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("database") == "ok", f"Grafana version: {data.get('version')}"
results.append(test("Grafana Server Online & Healthy (http://localhost:3000)", test_grafana_health))

# 4. Grafana Provisioned Datasource
def test_grafana_datasource():
    req = urllib.request.Request("http://127.0.0.1:3000/api/datasources/uid/P452D8585961534C5/health", headers=auth_header)
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("status") == "OK", data.get("message")
results.append(test("Grafana InfluxDB Datasource Connected & Validated", test_grafana_datasource))

# 5. Grafana Provisioned Dashboards
def test_grafana_dashboard():
    req = urllib.request.Request("http://127.0.0.1:3000/api/search", headers=auth_header)
    with urllib.request.urlopen(req, timeout=3) as resp:
        dashboards = json.loads(resp.read().decode("utf-8"))
        found = any(d.get("uid") == "nmas-noc-master" for d in dashboards)
        return found, f"Dashboards found: {[d.get('title') for d in dashboards]}"
results.append(test("Grafana NMAS NOC Dashboard Provisioned & Loaded", test_grafana_dashboard))

# 6. NetworkX High-Res Static Snapshot
def test_networkx_snapshot():
    path = "/home/student/Desktop/lab1/reports/traffic_flow_snapshot.png"
    exists = os.path.exists(path) and os.path.getsize(path) > 50000
    return exists, f"Snapshot size: {os.path.getsize(path) if exists else 0} bytes"
results.append(test("NetworkX Topology & Multi-Flow Snapshot (PNG)", test_networkx_snapshot))

# 7. NetworkX Dynamic Animated GIF
def test_networkx_gif():
    path = "/home/student/Desktop/lab1/reports/traffic_flow_dynamic.gif"
    exists = os.path.exists(path) and os.path.getsize(path) > 100000
    return exists, f"GIF size: {os.path.getsize(path) if exists else 0} bytes"
results.append(test("NetworkX Dynamic Animated Packet Flow (GIF)", test_networkx_gif))

# 8. Interactive HTML5 Visualizer
def test_networkx_html():
    path = "/home/student/Desktop/lab1/reports/dynamic_traffic_flow.html"
    exists = os.path.exists(path) and os.path.getsize(path) > 5000
    return exists, f"HTML visualizer size: {os.path.getsize(path) if exists else 0} bytes"
results.append(test("Interactive Dynamic Traffic Flow Visualizer (HTML5 / Canvas)", test_networkx_html))

print("\n" + "="*75)
passed = sum(1 for r in results if r)
total = len(results)
print(f"   SUMMARY: {passed}/{total} Part 2 Tests Passed ({(passed/total)*100:.1f}%)")
print("="*75)

if passed == total:
    print("\n \033[92mPART 2 OBJECTIVES (GRAFANA DASHBOARD & NETWORKX TRAFFIC FLOW) VERIFIED! \033[0m\n")
    sys.exit(0)
else:
    sys.exit(1)
