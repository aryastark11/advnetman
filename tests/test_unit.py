import unittest
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from netsleuth.llm.redaction import redact_sensitive_data
from netsleuth.llm.schema import LLMDiagnosis, Hypothesis, ProposedFix
from netsleuth.engine.blast_radius import compute_blast_radius
from netsleuth.graph.topology import topology
from netsleuth.storage.db import (
    init_db,
    save_incident,
    get_incident_by_id,
    add_evidence,
    get_evidence_for_incident,
    add_timeline_event,
    get_timeline,
    record_audit_action,
    get_audit_logs
)

class TestUnitNetSleuth(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_redaction_secrets(self):
        raw_cfg = """
        username admin secret sha512 $6$0EpeAr86ZqgoZ07r$xiDp3lefZnL6ZYJ3h1ZfuVyLAbj6C
        password cisco
        snmp-server community private rw
        root_token = "hvs.DUMMY_MOCK_TOKEN_NOT_A_REAL_SECRET_TEST"
        api_key = "AIzaSyD-fakeKey1234567890abcdef"
        """
        redacted = redact_sensitive_data(raw_cfg)
        self.assertNotIn("$6$0EpeAr86ZqgoZ07r", redacted)
        self.assertNotIn("private rw", redacted)
        self.assertNotIn("hvs.DUMMY_MOCK_TOKEN", redacted)
        self.assertNotIn("AIzaSyD-fakeKey", redacted)
        self.assertIn("[REDACTED_PASSWORD_HASH]", redacted)
        self.assertIn("[REDACTED_COMMUNITY]", redacted)

    def test_schema_validation(self):
        valid_data = {
            "summary": "BGP session down between R5 and R3",
            "hypotheses": [
                {
                    "cause": "External ASBR peering down",
                    "confidence": 0.95,
                    "evidence_ids": ["EVID-BGP-001"],
                    "next_test": "Verify BGP state"
                }
            ],
            "proposed_fix": {
                "description": "Re-enable BGP neighbor",
                "device": "R5",
                "commands": ["router bgp 65005", "no neighbor 172.16.35.1 shutdown"],
                "risk": "low",
                "rollback": ["router bgp 65005", "neighbor 172.16.35.1 shutdown"]
            }
        }
        diag = LLMDiagnosis.model_validate(valid_data)
        self.assertEqual(diag.proposed_fix.device, "R5")
        self.assertEqual(len(diag.hypotheses), 1)

    def test_blast_radius_computation(self):
        # 1. Edge/BGP failure -> all hosts impacted
        br_edge = compute_blast_radius("R5", "Control Plane - BGP", {})
        self.assertEqual(br_edge["impact_level"], "critical")
        self.assertEqual(len(br_edge["affected_hosts"]), 7)

        # 2. Area 10 failure -> H5 impacted
        br_a10 = compute_blast_radius("R6", "Control Plane - OSPF", {})
        self.assertIn("H5", br_a10["affected_hosts"])
        self.assertEqual(len(br_a10["affected_hosts"]), 1)

        # 3. Area 30 failure -> H6, H7 impacted
        br_a30 = compute_blast_radius("R8", "Control Plane - OSPF", {})
        self.assertIn("H6", br_a30["affected_hosts"])
        self.assertIn("H7", br_a30["affected_hosts"])

    def test_topology_graph_integrity(self):
        data = topology.get_topology_data()
        self.assertEqual(data["summary"]["routers"], 8)
        self.assertEqual(data["summary"]["switches"], 5)
        self.assertEqual(data["summary"]["hosts"], 7)
        self.assertGreaterEqual(len(data["edges"]), 20)

    def test_storage_crud(self):
        inc_id = f"INC-UNITTEST-{int(time.time()*1000)}"
        save_incident({
            "id": inc_id,
            "title": "Unit test incident",
            "severity": "medium",
            "category": "Test",
            "status": "open",
            "root_cause_device": "R1"
        })
        inc = get_incident_by_id(inc_id)
        self.assertIsNotNone(inc)
        self.assertEqual(inc["title"], "Unit test incident")

        ev_id = add_evidence({
            "incident_id": inc_id,
            "device": "R1",
            "evidence_type": "unit_test",
            "source": "pytest",
            "summary": "Unit test evidence summary",
            "raw_data": {"test_key": "test_val"}
        })
        evs = get_evidence_for_incident(inc_id)
        self.assertGreaterEqual(len(evs), 1)
        self.assertIn(ev_id, [e["id"] for e in evs])

if __name__ == "__main__":
    unittest.main()
