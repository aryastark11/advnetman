import sqlite3
import json
import os
import time
from typing import Dict, List, Any, Optional

DB_PATH = os.environ.get("NETSLEUTH_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netsleuth.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        severity TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL,
        root_cause_device TEXT,
        blast_radius_hosts TEXT DEFAULT '[]',
        blast_radius_services TEXT DEFAULT '[]',
        hypotheses TEXT DEFAULT '[]',
        proposed_fix TEXT DEFAULT '{}',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        id TEXT PRIMARY KEY,
        incident_id TEXT,
        device TEXT NOT NULL,
        evidence_type TEXT NOT NULL,
        source TEXT NOT NULL,
        summary TEXT NOT NULL,
        raw_data TEXT DEFAULT '{}',
        timestamp REAL NOT NULL,
        FOREIGN KEY (incident_id) REFERENCES incidents(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        details TEXT DEFAULT '{}',
        FOREIGN KEY (incident_id) REFERENCES incidents(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS probes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_host TEXT NOT NULL,
        target_name TEXT NOT NULL,
        target_ip TEXT NOT NULL,
        probe_type TEXT NOT NULL,
        success INTEGER NOT NULL,
        rtt_ms REAL,
        http_status INTEGER,
        error_msg TEXT,
        timestamp REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS node_health (
        node_name TEXT PRIMARY KEY,
        health TEXT NOT NULL,
        details TEXT DEFAULT '{}',
        last_seen REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT,
        device TEXT NOT NULL,
        action TEXT NOT NULL,
        commands TEXT DEFAULT '[]',
        operator TEXT NOT NULL,
        result TEXT NOT NULL,
        pre_snapshot TEXT,
        post_snapshot TEXT,
        timestamp REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config_drift (
        device TEXT PRIMARY KEY,
        has_drift INTEGER NOT NULL,
        diff_text TEXT,
        golden_version TEXT,
        running_hash TEXT,
        timestamp REAL NOT NULL
    );
    """)

    conn.commit()
    conn.close()

# Helper queries
def save_incident(incident: Dict[str, Any]) -> str:
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    inc_id = incident.get("id") or f"INC-{int(now * 1000) % 1000000}"
    
    c.execute("""
    INSERT INTO incidents (id, title, severity, category, status, root_cause_device, blast_radius_hosts, blast_radius_services, hypotheses, proposed_fix, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        title=excluded.title,
        severity=excluded.severity,
        category=excluded.category,
        status=excluded.status,
        root_cause_device=excluded.root_cause_device,
        blast_radius_hosts=excluded.blast_radius_hosts,
        blast_radius_services=excluded.blast_radius_services,
        hypotheses=excluded.hypotheses,
        proposed_fix=excluded.proposed_fix,
        updated_at=excluded.updated_at
    """, (
        inc_id,
        incident.get("title", "Untitled Incident"),
        incident.get("severity", "medium"),
        incident.get("category", "General"),
        incident.get("status", "open"),
        incident.get("root_cause_device", ""),
        json.dumps(incident.get("blast_radius_hosts", [])),
        json.dumps(incident.get("blast_radius_services", [])),
        json.dumps(incident.get("hypotheses", [])),
        json.dumps(incident.get("proposed_fix", {})),
        incident.get("created_at", now),
        now
    ))
    conn.commit()
    conn.close()
    return inc_id

def get_incidents(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        c.execute("SELECT * FROM incidents ORDER BY created_at DESC")
    rows = c.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["blast_radius_hosts"] = json.loads(d["blast_radius_hosts"] or "[]")
        d["blast_radius_services"] = json.loads(d["blast_radius_services"] or "[]")
        d["hypotheses"] = json.loads(d["hypotheses"] or "[]")
        d["proposed_fix"] = json.loads(d["proposed_fix"] or "{}")
        results.append(d)
    conn.close()
    return results

def get_incident_by_id(incident_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    d["blast_radius_hosts"] = json.loads(d["blast_radius_hosts"] or "[]")
    d["blast_radius_services"] = json.loads(d["blast_radius_services"] or "[]")
    d["hypotheses"] = json.loads(d["hypotheses"] or "[]")
    d["proposed_fix"] = json.loads(d["proposed_fix"] or "{}")
    conn.close()
    return d

def add_evidence(ev: Dict[str, Any]) -> str:
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    ev_id = ev.get("id") or f"EVID-{int(now * 10000) % 10000000}"
    c.execute("""
    INSERT INTO evidence (id, incident_id, device, evidence_type, source, summary, raw_data, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        summary=excluded.summary,
        raw_data=excluded.raw_data
    """, (
        ev_id,
        ev.get("incident_id"),
        ev.get("device", ""),
        ev.get("evidence_type", "unknown"),
        ev.get("source", "eapi"),
        ev.get("summary", ""),
        json.dumps(ev.get("raw_data", {})),
        ev.get("timestamp", now)
    ))
    conn.commit()
    conn.close()
    return ev_id

def get_evidence_for_incident(incident_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE incident_id = ? ORDER BY timestamp ASC", (incident_id,))
    rows = c.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["raw_data"] = json.loads(d["raw_data"] or "{}")
        results.append(d)
    conn.close()
    return results

def get_evidence_by_device(device: str) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE device = ? ORDER BY timestamp DESC LIMIT 50", (device,))
    rows = c.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["raw_data"] = json.loads(d["raw_data"] or "{}")
        results.append(d)
    conn.close()
    return results

def add_timeline_event(incident_id: str, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    c.execute("""
    INSERT INTO timeline (incident_id, timestamp, event_type, description, details)
    VALUES (?, ?, ?, ?, ?)
    """, (
        incident_id,
        now,
        event_type,
        description,
        json.dumps(details or {})
    ))
    conn.commit()
    conn.close()

def get_timeline(incident_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM timeline WHERE incident_id = ? ORDER BY timestamp ASC", (incident_id,))
    rows = c.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details"] or "{}")
        results.append(d)
    conn.close()
    return results

def record_probe(source_host: str, target_name: str, target_ip: str, probe_type: str,
                 success: bool, rtt_ms: Optional[float] = None, http_status: Optional[int] = None,
                 error_msg: Optional[str] = None):
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    c.execute("""
    INSERT INTO probes (source_host, target_name, target_ip, probe_type, success, rtt_ms, http_status, error_msg, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source_host, target_name, target_ip, probe_type,
        1 if success else 0, rtt_ms, http_status, error_msg, now
    ))
    conn.commit()
    conn.close()

def get_recent_probes(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM probes ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def update_node_health(node_name: str, health: str, details: Optional[Dict[str, Any]] = None):
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    c.execute("""
    INSERT INTO node_health (node_name, health, details, last_seen)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(node_name) DO UPDATE SET
        health=excluded.health,
        details=excluded.details,
        last_seen=excluded.last_seen
    """, (node_name, health, json.dumps(details or {}), now))
    conn.commit()
    conn.close()

def get_all_node_health() -> Dict[str, Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM node_health")
    rows = c.fetchall()
    results = {}
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details"] or "{}")
        results[d["node_name"]] = d
    conn.close()
    return results

def record_audit_action(incident_id: Optional[str], device: str, action: str,
                        commands: List[str], operator: str, result: str,
                        pre_snapshot: Optional[str] = None, post_snapshot: Optional[str] = None):
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    c.execute("""
    INSERT INTO audit_log (incident_id, device, action, commands, operator, result, pre_snapshot, post_snapshot, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_id, device, action, json.dumps(commands), operator, result, pre_snapshot, post_snapshot, now
    ))
    conn.commit()
    conn.close()

def get_audit_logs(incident_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    if isinstance(incident_id, int):
        limit = incident_id
        incident_id = None

    if incident_id:
        c.execute("SELECT * FROM audit_log WHERE incident_id = ? ORDER BY timestamp DESC LIMIT ?", (incident_id, limit))
    else:
        c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["commands"] = json.loads(d["commands"] or "[]")
        results.append(d)
    conn.close()
    return results

def save_config_drift(device: str, has_drift: bool, diff_text: str = "", golden_version: str = "", running_hash: str = ""):
    conn = get_db()
    c = conn.cursor()
    now = time.time()
    c.execute("""
    INSERT INTO config_drift (device, has_drift, diff_text, golden_version, running_hash, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(device) DO UPDATE SET
        has_drift=excluded.has_drift,
        diff_text=excluded.diff_text,
        golden_version=excluded.golden_version,
        running_hash=excluded.running_hash,
        timestamp=excluded.timestamp
    """, (device, 1 if has_drift else 0, diff_text, golden_version, running_hash, now))
    conn.commit()
    conn.close()

def get_config_drift(device: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    if device:
        c.execute("SELECT * FROM config_drift WHERE device = ?", (device,))
    else:
        c.execute("SELECT * FROM config_drift ORDER BY device ASC")
    rows = c.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results
