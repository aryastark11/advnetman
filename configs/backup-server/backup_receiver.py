#!/usr/bin/env python3
import socket
import os
import sys
import json
import time
import shutil
import sqlite3
import threading
from datetime import datetime, timedelta

BACKUP_DIR = "/opt/backup/datalake"
PORT = 9999
RETENTION_DAYS = 7

def enforce_retention_policy():
    while True:
        try:
            now = datetime.utcnow()
            cutoff_date = now - timedelta(days=RETENTION_DAYS)
            cutoff_ts = cutoff_date.isoformat()
            
            deleted_files = []
            for root, dirs, files in os.walk(BACKUP_DIR):
                for f in files:
                    filepath = os.path.join(root, f)
                    if f.endswith(".log") or f.endswith(".db") or f.endswith(".db-journal"):
                        continue
                    try:
                        mtime = datetime.utcfromtimestamp(os.path.getmtime(filepath))
                        if mtime < cutoff_date:
                            os.remove(filepath)
                            deleted_files.append(filepath)
                    except Exception:
                        pass
            
            db_path = os.path.join(BACKUP_DIR, "datalake_backup.db")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    for table in ["snmp_metrics", "snmp_traps", "syslog_events", "telemetry_streams", "netconf_states"]:
                        cur.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_ts,))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

            with open(os.path.join(BACKUP_DIR, "retention_backup.log"), "a") as rf:
                rf.write(f"[{datetime.utcnow().isoformat()}] Backup Retention check completed. Deleted {len(deleted_files)} files older than {RETENTION_DAYS} days.\n")
                for df in deleted_files:
                    rf.write(f"  - Purged: {df}\n")

        except Exception:
            pass
        time.sleep(300)

def handle_client(conn, addr):
    client_ip = addr[0]
    if client_ip not in ["10.99.99.1", "172.20.20.100", "127.0.0.1"]:
        conn.close()
        return
    try:
        data_buffer = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data_buffer += chunk

        if data_buffer:
            msg = json.loads(data_buffer.decode("utf-8"))
            action = msg.get("action")
            
            if action == "sync_file":
                rel_path = msg.get("rel_path")
                content = msg.get("content")
                dest_path = os.path.join(BACKUP_DIR, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(content)
                response = {"status": "ok", "msg": f"Synced {rel_path}"}
            
            elif action == "sync_db_dump":
                sql_dump = msg.get("sql_dump")
                db_path = os.path.join(BACKUP_DIR, "datalake_backup.db")
                conn_db = sqlite3.connect(db_path)
                conn_db.executescript(sql_dump)
                conn_db.close()
                response = {"status": "ok", "msg": "Database synced successfully"}
            
            elif action == "status":
                total_files = sum(len(f) for _, _, f in os.walk(BACKUP_DIR))
                response = {
                    "status": "ok",
                    "backup_dir": BACKUP_DIR,
                    "total_files": total_files,
                    "server_time": datetime.utcnow().isoformat()
                }
            else:
                response = {"status": "error", "msg": "Unknown action"}
                
            conn.sendall(json.dumps(response).encode("utf-8"))
    except Exception as e:
        pass
    finally:
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(10)
    print(f"Backup receiver listening on port {PORT}...")
    
    threading.Thread(target=enforce_retention_policy, daemon=True).start()
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
