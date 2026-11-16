import time
from typing import Dict, List, Any
from netsleuth.storage.db import add_evidence

_evidence_counter = 100

def generate_evidence_id(evidence_type: str) -> str:
    global _evidence_counter
    _evidence_counter += 1
    type_code = evidence_type.upper().replace(" ", "_")[:6]
    return f"EVID-{type_code}-{_evidence_counter}"

def build_evidence_item(incident_id: str, device: str, evidence_type: str,
                        source: str, summary: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    ev_id = generate_evidence_id(evidence_type)
    evidence_dict = {
        "id": ev_id,
        "incident_id": incident_id,
        "device": device,
        "evidence_type": evidence_type,
        "source": source,
        "summary": summary,
        "raw_data": raw_data,
        "timestamp": time.time()
    }
    add_evidence(evidence_dict)
    return evidence_dict

def compile_incident_evidence(incident_id: str, violation: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence_list = []
    dev = violation.get("device", "Network")
    ev_type = violation.get("evidence_type", "general")
    detail = violation.get("detail", "")
    raw = violation.get("raw_data", {})

    # Main evidence from the rule check
    primary_ev = build_evidence_item(
        incident_id=incident_id,
        device=dev,
        evidence_type=ev_type,
        source="deterministic_rule",
        summary=detail,
        raw_data=raw
    )
    evidence_list.append(primary_ev)

    return evidence_list
