import unittest
import os
import sys
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from netsleuth.scripts.inject_fault import inject_scenario, clear_scenario, clear_all
from netsleuth.remediation.engine import execute_remediation
from netsleuth.collectors.synthetic_probes import run_all_probes
from netsleuth.storage.db import get_incident_by_id, get_audit_logs

API_URL = "http://127.0.0.1:8000"

class TestFaultInjectionSuites(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure clean state
        clear_all()
        time.sleep(3.0)
        from netsleuth.engine.incident_engine import incident_engine
        incident_engine.scan_and_reconcile()

    @classmethod
    def tearDownClass(cls):
        clear_all()
        time.sleep(1.0)

    def test_01_bgp_peer_down(self):
        print("\n--- Testing Scenario: bgp-peer-down ---")
        try:
            ok = inject_scenario("bgp-peer-down")
            self.assertTrue(ok)
            time.sleep(2.0)

            res = requests.get(f"{API_URL}/api/incidents").json()
            bgp_incs = [i for i in res if i["category"] == "Control Plane - BGP" and i["status"] == "open"]
            self.assertGreaterEqual(len(bgp_incs), 1)

            r5_incs = [i for i in bgp_incs if i["root_cause_device"] == "R5"]
            self.assertGreaterEqual(len(r5_incs), 1)
            inc = r5_incs[0]
            self.assertEqual(inc["root_cause_device"], "R5")
            self.assertIn("H1", inc["blast_radius_hosts"])

            # Test Closed-Loop Remediation
            fix_res = execute_remediation(
                incident_id=inc["id"],
                commands=["router bgp 65005", "no neighbor 172.16.35.1 shutdown"],
                device="R5",
                operator="test_runner"
            )
            self.assertTrue(fix_res["success"])
            self.assertEqual(fix_res["status"], "resolved")
        finally:
            clear_scenario("bgp-peer-down")
            time.sleep(1.0)

    def test_02_interface_down(self):
        print("\n--- Testing Scenario: interface-down ---")
        try:
            ok = inject_scenario("interface-down")
            self.assertTrue(ok)
            time.sleep(2.0)

            res = requests.get(f"{API_URL}/api/incidents").json()
            intf_incs = [i for i in res if i["status"] == "open" and (i["category"] == "Data Plane - Interface" or i["root_cause_device"] == "R1")]
            self.assertGreaterEqual(len(intf_incs), 1)
            r1_inc = [i for i in intf_incs if i["root_cause_device"] == "R1"][0]
            self.assertIn("R1", r1_inc["root_cause_device"])
        finally:
            clear_scenario("interface-down")
            time.sleep(1.0)

    def test_03_ospf_area_mismatch(self):
        print("\n--- Testing Scenario: ospf-area-mismatch ---")
        try:
            ok = inject_scenario("ospf-area-mismatch")
            self.assertTrue(ok)
            time.sleep(4.5)

            res = requests.get(f"{API_URL}/api/incidents").json()
            ospf_incs = [i for i in res if i["category"] == "Control Plane - OSPF" and i["status"] == "open"]
            self.assertGreaterEqual(len(ospf_incs), 1)
            inc = ospf_incs[0]
            self.assertIn(inc["root_cause_device"], ["R4", "R6"])
        finally:
            clear_scenario("ospf-area-mismatch")
            time.sleep(1.5)

    def test_04_rip_missing_network(self):
        print("\n--- Testing Scenario: rip-missing-network ---")
        try:
            ok = inject_scenario("rip-missing-network")
            self.assertTrue(ok)
            time.sleep(2.0)

            res = requests.get(f"{API_URL}/api/incidents").json()
            rip_incs = [i for i in res if i["category"] == "Control Plane - RIP" and i["status"] == "open"]
            self.assertGreaterEqual(len(rip_incs), 1)
            inc = rip_incs[0]
            self.assertEqual(inc["root_cause_device"], "R1")
        finally:
            clear_scenario("rip-missing-network")
            time.sleep(1.0)

    def test_05_vlan_trunk_missing(self):
        print("\n--- Testing Scenario: vlan-trunk-missing ---")
        try:
            ok = inject_scenario("vlan-trunk-missing")
            self.assertTrue(ok)
            time.sleep(1.5)

            probe_res = run_all_probes()
            self.assertGreaterEqual(probe_res["failed_count"], 1)
            failing_hosts = [f["host"] for f in probe_res["failures"]]
            self.assertIn("H1", failing_hosts)
        finally:
            clear_scenario("vlan-trunk-missing")
            time.sleep(1.0)

    def test_06_varp_gateway_down(self):
        print("\n--- Testing Scenario: varp-gateway-down ---")
        try:
            ok = inject_scenario("varp-gateway-down")
            self.assertTrue(ok)
            time.sleep(2.0)

            res = requests.get(f"{API_URL}/api/incidents").json()
            varp_or_intf = [i for i in res if i["status"] == "open" and i["root_cause_device"] == "R1"]
            self.assertGreaterEqual(len(varp_or_intf), 1)
        finally:
            clear_scenario("varp-gateway-down")
            time.sleep(1.0)

    def test_07_webserver_down(self):
        print("\n--- Testing Scenario: webserver-down ---")
        try:
            ok = inject_scenario("webserver-down")
            self.assertTrue(ok)
            time.sleep(1.5)

            probe_res = run_all_probes()
            self.assertGreaterEqual(probe_res["failed_count"], 1)

            res = requests.get(f"{API_URL}/api/incidents").json()
            web_incs = [i for i in res if i["status"] == "open" and i["root_cause_device"] == "Web Server"]
            self.assertGreaterEqual(len(web_incs), 1)
            self.assertGreaterEqual(len(web_incs[0]["blast_radius_hosts"]), 5)
        finally:
            clear_scenario("webserver-down")
            time.sleep(1.0)

    def test_08_deliberate_bad_fix_rollback(self):
        print("\n--- Testing Scenario: Deliberate Bad Fix Rollback Verification ---")
        try:
            # 1. Inject fault on BGP
            inject_scenario("bgp-peer-down")
            time.sleep(2.0)

            res = requests.get(f"{API_URL}/api/incidents").json()
            bgp_incs = [i for i in res if i["category"] == "Control Plane - BGP" and i["status"] == "open"]
            self.assertGreaterEqual(len(bgp_incs), 1)
            inc_id = bgp_incs[0]["id"]

            # 2. Attempt a valid syntax command that does NOT fix the BGP neighbor (ineffective fix)
            # Setting an interface comment/description applies cleanly via eAPI but leaves BGP down
            bad_fix_res = execute_remediation(
                incident_id=inc_id,
                commands=["interface Loopback999", "description INEFFECTIVE_FIX_TRIGGER"],
                device="R5",
                operator="qa_adversary",
                rollback=["no interface Loopback999"]
            )

            # 3. Verify that remediation engine flagged verification failure and initiated rollback
            self.assertFalse(bad_fix_res["success"])
            self.assertEqual(bad_fix_res["status"], "rollback")
            self.assertFalse(bad_fix_res["verified"])

            # 4. Check audit log has rollback entry
            audits = get_audit_logs(inc_id)
            self.assertGreaterEqual(len(audits), 1)
            rollback_audits = [a for a in audits if a["action"] == "rollback"]
            self.assertGreaterEqual(len(rollback_audits), 1)
        finally:
            # Clean up
            clear_scenario("bgp-peer-down")
            time.sleep(1.0)

if __name__ == "__main__":
    unittest.main()
