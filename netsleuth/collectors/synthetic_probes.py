import subprocess
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
from netsleuth.storage.db import record_probe, add_timeline_event

logger = logging.getLogger("netsleuth.probes")

HOST_CONFIGS = {
    "H1": {
        "container": "clab-lab1-h1",
        "gateway": "10.10.10.254",
        "core": "10.0.0.1",
        "r5": "172.16.35.2",
        "web": "198.51.100.10",
        "ipv6": False
    },
    "H2": {
        "container": "clab-lab1-h2",
        "gateway": "10.10.20.254",
        "core": "10.0.0.1",
        "r5": "172.16.35.2",
        "web": "198.51.100.10",
        "ipv6": False
    },
    "H3": {
        "container": "clab-lab1-h3",
        "gateway": "10.10.10.254",
        "core": "10.0.0.2",
        "r5": "172.16.45.2",
        "web": "198.51.100.10",
        "ipv6": False
    },
    "H4": {
        "container": "clab-lab1-h4",
        "gateway": "2001:db8:30::254",
        "core": "2001:db8:0::2",
        "r5": "2001:db8:100::1",
        "web": "2001:db8:100::10",
        "ipv6": True
    },
    "H5": {
        "container": "clab-lab1-h5",
        "gateway": "10.70.10.1",
        "core": "10.0.0.4",
        "r5": "172.16.45.2",
        "web": "198.51.100.10",
        "ipv6": False
    },
    "H6": {
        "container": "clab-lab1-h6",
        "gateway": "10.80.10.1",
        "core": "10.0.0.2",
        "r5": "172.16.35.2",
        "web": "198.51.100.10",
        "ipv6": False
    },
    "H7": {
        "container": "clab-lab1-h7",
        "gateway": "10.80.10.1",
        "core": "10.0.0.2",
        "r5": "172.16.35.2",
        "web": "198.51.100.10",
        "ipv6": False
    }
}

def exec_in_container(container: str, cmd: str, timeout: int = 3) -> Dict[str, Any]:
    full_cmd = f"docker exec {container} {cmd}"
    t0 = time.time()
    try:
        res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "elapsed_ms": elapsed_ms
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "elapsed_ms": elapsed_ms
        }

def probe_single_target(host_name: str, target_name: str, target_ip: str, probe_type: str, is_ipv6: bool = False) -> Dict[str, Any]:
    cfg = HOST_CONFIGS.get(host_name)
    if not cfg:
        return {"success": False, "error": "Unknown host"}

    container = cfg["container"]
    if probe_type == "icmp":
        ping_cmd = f"ping6 -c 1 -W 1 {target_ip}" if is_ipv6 else f"ping -c 1 -W 1 {target_ip}"
        res = exec_in_container(container, ping_cmd, timeout=2)
        success = res["success"]
        rtt = res["elapsed_ms"] if success else None
        record_probe(
            source_host=host_name,
            target_name=target_name,
            target_ip=target_ip,
            probe_type="icmp",
            success=success,
            rtt_ms=rtt,
            error_msg=None if success else res["stderr"] or "Timeout"
        )
        return {
            "host": host_name,
            "target": target_name,
            "ip": target_ip,
            "type": "icmp",
            "success": success,
            "rtt_ms": rtt
        }
    elif probe_type == "http":
        curl_cmd = f"curl -g -6 -s -o /dev/null -w '%{{http_code}}' -m 3 http://[{target_ip}]/" if is_ipv6 else f"curl -s -o /dev/null -w '%{{http_code}}' -m 2 http://{target_ip}"
        res = exec_in_container(container, curl_cmd, timeout=4)
        http_code = int(res["stdout"]) if res["stdout"].isdigit() else 0
        success = (http_code == 200)
        record_probe(
            source_host=host_name,
            target_name=target_name,
            target_ip=target_ip,
            probe_type="http",
            success=success,
            http_status=http_code,
            error_msg=None if success else f"HTTP code {http_code}"
        )
        return {
            "host": host_name,
            "target": target_name,
            "ip": target_ip,
            "type": "http",
            "success": success,
            "http_status": http_code
        }
    return {"success": False, "error": "Unknown probe type"}

def probe_host(host_name: str) -> List[Dict[str, Any]]:
    cfg = HOST_CONFIGS.get(host_name)
    if not cfg:
        return []
    is_v6 = cfg.get("ipv6", False)
    results = []

    # 1. Gateway
    results.append(probe_single_target(host_name, "Gateway", cfg["gateway"], "icmp", is_v6))
    # 2. Core
    results.append(probe_single_target(host_name, "Core", cfg["core"], "icmp", is_v6))
    # 3. R5 Edge
    results.append(probe_single_target(host_name, "R5", cfg["r5"], "icmp", is_v6))
    # 4. Web Server ICMP
    results.append(probe_single_target(host_name, "Web Server", cfg["web"], "icmp", is_v6))
    # 5. Web Server HTTP
    results.append(probe_single_target(host_name, "Web Server", cfg["web"], "http", is_v6))

    return results

def run_all_probes() -> Dict[str, Any]:
    start_t = time.time()
    all_results = []
    failed_probes = []

    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(probe_host, h): h for h in HOST_CONFIGS}
        for f in futures:
            try:
                host_results = f.result()
                all_results.extend(host_results)
                for pr in host_results:
                    if not pr["success"]:
                        failed_probes.append(pr)
            except Exception as e:
                logger.error(f"Error probing host {futures[f]}: {e}")

    elapsed_ms = round((time.time() - start_t) * 1000, 1)
    return {
        "timestamp": time.time(),
        "elapsed_ms": elapsed_ms,
        "total_probes": len(all_results),
        "failed_count": len(failed_probes),
        "failures": failed_probes,
        "results": all_results
    }

class ProbeRunnerThread:
    def __init__(self, interval: int = 10):
        self.interval = interval
        self._running = False
        self._thread = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("Synthetic probe runner thread started (10s interval)")

    def stop(self):
        self._running = False

    def _run_loop(self):
        # Initial probe
        time.sleep(2)
        while self._running:
            try:
                run_all_probes()
            except Exception as e:
                logger.error(f"Probe cycle error: {e}")
            time.sleep(self.interval)

probe_runner = ProbeRunnerThread()
