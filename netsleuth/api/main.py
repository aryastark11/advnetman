import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure netsleuth is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from netsleuth.storage.db import (
    init_db,
    get_incidents,
    get_incident_by_id,
    save_incident,
    get_evidence_for_incident,
    get_evidence_by_device,
    get_timeline,
    get_recent_probes,
    get_audit_logs,
    get_config_drift,
    save_config_drift,
    update_node_health
)
from netsleuth.graph.topology import topology
from netsleuth.graph.path_tracer import trace_path
from netsleuth.collectors.eapi_poller import get_full_evidence_for_node, get_running_config
from netsleuth.collectors.synthetic_probes import run_all_probes, probe_runner
from netsleuth.engine.incident_engine import incident_engine
from netsleuth.llm.client import llm_client
from netsleuth.remediation.engine import execute_remediation
from netsleuth.scripts.inject_fault import SCENARIOS, inject_scenario, clear_scenario, clear_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("netsleuth.api")

app = FastAPI(
    title="RCN NetSleuth AI",
    description="Closed-Loop Autonomous Network Troubleshooting & Remediation Copilot",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Mount static web frontend
WEB_DIR = os.path.join(BASE_DIR, "netsleuth", "web")
STATIC_DIR = os.path.join(WEB_DIR, "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def startup_event():
    # Start synthetic probe runner in background
    probe_runner.start()
    logger.info("NetSleuth API started successfully.")

@app.get("/")
def get_index():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "NetSleuth API running. Frontend index.html not found."}

@app.get("/api/topology")
def get_topology():
    return topology.get_topology_data()

@app.get("/api/nodes/{node_id}/evidence")
def get_node_evidence(node_id: str):
    node_id_norm = node_id.upper()
    try:
        ev = get_full_evidence_for_node(node_id_norm)
        # Add config drift status
        drifts = get_config_drift(node_id_norm)
        ev["drift"] = drifts[0] if drifts else {"has_drift": False, "diff_text": ""}
        return ev
    except Exception as e:
        logger.error(f"Error fetching evidence for {node_id}: {e}")
        return {"device": node_id_norm, "error": str(e), "interfaces": {}}

@app.get("/api/path")
def trace_network_path(source: str = Query("H1"), target: str = Query("web-server")):
    return trace_path(source, target)

@app.get("/api/incidents")
def list_incidents(status: Optional[str] = None):
    # Trigger active scan to keep incident view up-to-date
    incident_engine.scan_and_reconcile()
    return get_incidents(status)

@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = get_incident_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc["evidence"] = get_evidence_for_incident(incident_id)
    inc["timeline"] = get_timeline(incident_id)
    return inc

@app.post("/api/incidents/{incident_id}/diagnose")
def trigger_diagnosis(incident_id: str):
    inc = get_incident_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    evidence_items = get_evidence_for_incident(incident_id)
    diag = llm_client.diagnose(inc, evidence_items)

    inc["hypotheses"] = diag.get("hypotheses", [])
    inc["proposed_fix"] = diag.get("proposed_fix", {})
    save_incident(inc)

    return {
        "incident_id": incident_id,
        "summary": diag.get("summary"),
        "hypotheses": inc["hypotheses"],
        "proposed_fix": inc["proposed_fix"]
    }

class RemediationRequest(BaseModel):
    commands: Optional[List[str]] = None
    device: Optional[str] = None
    operator: str = "operator"

@app.post("/api/incidents/{incident_id}/remediate")
def apply_remediation(incident_id: str, req: RemediationRequest):
    res = execute_remediation(
        incident_id=incident_id,
        commands=req.commands,
        device=req.device,
        operator=req.operator
    )
    return res

class ChatRequest(BaseModel):
    message: str
    incident_id: Optional[str] = None
    node: Optional[str] = None

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    ctx = {"incident_id": req.incident_id, "node": req.node}
    if req.incident_id:
        ctx["incident"] = get_incident_by_id(req.incident_id)
    return llm_client.chat(req.message, ctx)

@app.get("/api/probes")
def get_probes(limit: int = 50):
    return get_recent_probes(limit)

@app.post("/api/probes/run")
def trigger_probes():
    return run_all_probes()

@app.get("/api/audit")
def list_audit_logs():
    return get_audit_logs(50)

@app.get("/api/drift")
def list_drift():
    return get_config_drift()

class DemoInjectRequest(BaseModel):
    scenario: str

@app.post("/api/demo/inject")
def api_inject_fault(req: DemoInjectRequest):
    ok = inject_scenario(req.scenario)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to inject scenario {req.scenario}")
    # Allow network to react and scan
    time.sleep(1.0)
    incident_engine.scan_and_reconcile()
    return {"scenario": req.scenario, "status": "injected"}

@app.post("/api/demo/clear")
def api_clear_fault(req: Optional[DemoInjectRequest] = None):
    if req and req.scenario:
        clear_scenario(req.scenario)
    else:
        clear_all()
    time.sleep(1.5)
    incident_engine.scan_and_reconcile()
    return {"status": "cleared"}

@app.get("/api/demo/scenarios")
def list_scenarios():
    return [{"id": k, "title": v["title"], "device": v["device"], "category": v["category"]} for k, v in SCENARIOS.items()]

@app.post("/api/engine/scan")
def trigger_scan():
    incidents = incident_engine.scan_and_reconcile()
    return {"status": "success", "active_incidents": len(incidents)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("netsleuth.api.main:app", host="0.0.0.0", port=8000, reload=False)
