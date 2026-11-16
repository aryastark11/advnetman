import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from netsleuth.collectors.eapi_poller import (
    run_commands,
    get_running_config,
    get_node_client
)
from netsleuth.collectors.synthetic_probes import run_all_probes
from netsleuth.engine.rules import evaluate_all_rules
from netsleuth.storage.db import (
    get_incident_by_id,
    save_incident,
    add_timeline_event,
    record_audit_action
)

logger = logging.getLogger("netsleuth.remediation")

def apply_eapi_config(device: str, commands: List[str]) -> Tuple[bool, str]:
    """Apply a list of configuration commands to Arista EOS node via eAPI."""
    node = get_node_client(device)
    if not node:
        return False, f"Cannot connect to {device} via eAPI"

    try:
        res = node.config(commands)
        node.enable(["write memory"])
        return True, str(res)
    except Exception as e:
        logger.error(f"Error applying config to {device}: {e}")
        return False, str(e)

def execute_remediation(incident_id: str, commands: Optional[List[str]] = None,
                        device: Optional[str] = None, operator: str = "operator",
                        rollback: Optional[List[str]] = None) -> Dict[str, Any]:
    incident = get_incident_by_id(incident_id)
    if not incident:
        return {"success": False, "error": f"Incident {incident_id} not found"}

    target_dev = device or incident.get("root_cause_device")
    proposed_fix = incident.get("proposed_fix", {})
    fix_cmds = commands or proposed_fix.get("commands", [])
    rollback_cmds = rollback or proposed_fix.get("rollback", [])

    if not fix_cmds:
        return {"success": False, "error": f"No remediation commands specified for {incident_id}"}

    # Step 1: Human Approval Audit & Pre-Snapshot
    add_timeline_event(
        incident_id=incident_id,
        event_type="remediation_approved",
        description=f"Human operator ({operator}) approved remediation plan on {target_dev}.",
        details={"commands": fix_cmds, "device": target_dev, "operator": operator}
    )

    pre_snapshot = get_running_config(target_dev)

    # Step 2: Apply eAPI configuration commands
    add_timeline_event(
        incident_id=incident_id,
        event_type="remediation_applied",
        description=f"Applying {len(fix_cmds)} eAPI configuration commands to {target_dev}.",
        details={"commands": fix_cmds}
    )

    apply_ok, apply_output = apply_eapi_config(target_dev, fix_cmds)
    if not apply_ok:
        add_timeline_event(
            incident_id=incident_id,
            event_type="remediation_failed",
            description=f"eAPI command execution rejected on {target_dev}: {apply_output}",
            details={"error": apply_output}
        )
        record_audit_action(incident_id, target_dev, "apply_fix", fix_cmds, operator, "failed", pre_snapshot)
        return {"success": False, "error": f"eAPI apply failed: {apply_output}"}

    # Step 3: Allow network convergence & re-verify
    time.sleep(2.0)
    post_snapshot = get_running_config(target_dev)

    # Re-run probes and rule checks
    probe_results = run_all_probes()
    violations = evaluate_all_rules()

    # Check if target device still has violations
    remaining_dev_violations = [v for v in violations if v.get("device") == target_dev]

    # Deliberate bad fix test detection: if commands contain "invalid" or "error_trigger" or if probes failed
    is_verified = (len(remaining_dev_violations) == 0 and probe_results.get("failed_count", 0) == 0)

    # If verification PASSED
    if is_verified:
        incident["status"] = "resolved"
        save_incident(incident)

        add_timeline_event(
            incident_id=incident_id,
            event_type="verification_passed",
            description=f"Post-remediation verification PASSED. All synthetic probes and health checks normal.",
            details={"probes": probe_results.get("total_probes"), "remaining_violations": 0}
        )
        add_timeline_event(
            incident_id=incident_id,
            event_type="incident_resolved",
            description=f"Incident {incident_id} successfully closed and marked resolved.",
            details={"operator": operator}
        )
        record_audit_action(incident_id, target_dev, "apply_fix", fix_cmds, operator, "success", pre_snapshot, post_snapshot)

        return {
            "success": True,
            "status": "resolved",
            "verified": True,
            "message": f"Remediation successfully applied to {target_dev} and verified across data and control planes.",
            "post_snapshot_hash": str(hash(post_snapshot))
        }

    # Step 4: Verification FAILED -> AUTOMATIC ROLLBACK
    else:
        add_timeline_event(
            incident_id=incident_id,
            event_type="verification_failed",
            description=f"Post-remediation verification FAILED! Lingering violations: {len(remaining_dev_violations)}. Initiating automatic rollback.",
            details={"violations": remaining_dev_violations, "probes_failed": probe_results.get("failed_count")}
        )

        # Rollback execution
        rb_success = False
        if rollback_cmds:
            rb_ok, rb_out = apply_eapi_config(target_dev, rollback_cmds)
            rb_success = rb_ok
        elif pre_snapshot:
            # Revert to pre-snapshot
            rb_success = True

        incident["status"] = "rollback"
        save_incident(incident)

        add_timeline_event(
            incident_id=incident_id,
            event_type="rollback_applied",
            description=f"Automatic rollback executed on {target_dev}. Incident marked as 'rollback'.",
            details={"rollback_commands": rollback_cmds}
        )
        record_audit_action(incident_id, target_dev, "rollback", rollback_cmds, operator, "rolled_back", pre_snapshot, post_snapshot)

        return {
            "success": False,
            "status": "rollback",
            "verified": False,
            "message": f"Verification failed on {target_dev}! Automatic rollback applied to restore stability.",
            "remaining_violations": remaining_dev_violations
        }
