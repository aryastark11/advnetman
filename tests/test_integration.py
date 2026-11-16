import unittest
import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from netsleuth.collectors.eapi_poller import (
    get_interfaces_status,
    get_ospf_neighbors,
    get_bgp_peers,
    get_rip_routes,
    get_varp_state,
    get_syslog
)
from netsleuth.collectors.synthetic_probes import run_all_probes
from netsleuth.graph.path_tracer import trace_path

API_URL = os.environ.get("NETSLEUTH_URL", "http://127.0.0.1:8000")

class TestIntegrationLive(unittest.TestCase):

    def test_eapi_collectors(self):
        # 1. Interface status on R1
        intfs = get_interfaces_status("R1")
        self.assertIn("statuses", intfs)
        self.assertIn("Ethernet1", intfs["statuses"])

        # 2. OSPF neighbors on R1
        ospf = get_ospf_neighbors("R1")
        self.assertGreaterEqual(len(ospf), 1)

        # 3. BGP peers on R5
        bgp = get_bgp_peers("R5")
        self.assertGreaterEqual(len(bgp), 1)
        self.assertEqual(bgp[0]["state"], "Established")

        # 4. RIP routes on R1
        rip = get_rip_routes("R1")
        self.assertGreaterEqual(len(rip), 1)

        # 5. VARP on R1
        varp = get_varp_state("R1")
        self.assertIn("varp", varp)

        # 6. Syslog on R1
        logs = get_syslog("R1", 5)
        self.assertGreaterEqual(len(logs), 1)

    def test_synthetic_probes_nominal(self):
        res = run_all_probes()
        self.assertEqual(res["failed_count"], 0)
        self.assertEqual(res["total_probes"], 35)

    def test_path_tracer_nominal(self):
        for h in ["H1", "H2", "H3", "H4", "H5", "H6", "H7"]:
            res = trace_path(h)
            self.assertEqual(res["status"], "healthy", f"Path for {h} should be healthy")
            self.assertGreaterEqual(res["total_hops"], 4)

    def test_fastapi_endpoints(self):
        # Topology endpoint
        res = requests.get(f"{API_URL}/api/topology")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["summary"]["total_nodes"], 23)

        # Evidence endpoint
        res = requests.get(f"{API_URL}/api/nodes/R1/evidence")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["device"], "R1")

        # Path endpoint
        res = requests.get(f"{API_URL}/api/path?source=H1&target=web-server")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

        # Chat endpoint
        res = requests.post(f"{API_URL}/api/chat", json={"message": "Trace path for H1"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("response", res.json())

if __name__ == "__main__":
    unittest.main()
