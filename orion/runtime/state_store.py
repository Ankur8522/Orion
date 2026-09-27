from __future__ import annotations
import json, sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

class RuntimeStateStore:
    """Durable operating-state store for jobs, runtime cycles, alerts and UI-safe state."""
    def __init__(self, path=':memory:'):
        self.path=str(path); self._lock=RLock(); self._db=sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory=sqlite3.Row
        self._db.executescript('''
        CREATE TABLE IF NOT EXISTS runtime_cycles(
          cycle_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
          status TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runtime_alerts(
          alert_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          severity TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL,
          acknowledged INTEGER NOT NULL DEFAULT 0, payload_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_jobs(
          job_key TEXT PRIMARY KEY, status TEXT NOT NULL, security_ids_json TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, error TEXT, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ui_events(
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          kind TEXT NOT NULL, payload_json TEXT NOT NULL);
        '''); self._db.commit()
    def _json(self,x): return json.dumps(x,sort_keys=True,separators=(',',':'),default=str)
    def cycle_start(self, cycle_id, started_at, payload=None):
        with self._lock:
            self._db.execute('INSERT OR REPLACE INTO runtime_cycles(cycle_id,started_at,finished_at,status,payload_json) VALUES(?,?,?,?,?)',(cycle_id,started_at,None,'RUNNING',self._json(payload or {}))); self._db.commit()
    def cycle_finish(self, cycle_id, finished_at, status, payload=None):
        with self._lock:
            self._db.execute('UPDATE runtime_cycles SET finished_at=?,status=?,payload_json=? WHERE cycle_id=?',(finished_at,status,self._json(payload or {}),cycle_id)); self._db.commit()
    def cycles(self, limit=100):
        rows=self._db.execute('SELECT * FROM runtime_cycles ORDER BY started_at DESC LIMIT ?', (int(limit),)).fetchall(); return [dict(r) for r in rows]
    def add_alert(self, created_at, severity, code, message, payload=None):
        with self._lock:
            cur=self._db.execute('INSERT INTO runtime_alerts(created_at,severity,code,message,payload_json) VALUES(?,?,?,?,?)',(created_at,severity,code,message,self._json(payload or {}))); self._db.commit(); return int(cur.lastrowid)
    def alerts(self, include_ack=False, limit=100):
        q='SELECT * FROM runtime_alerts'+('' if include_ack else ' WHERE acknowledged=0')+' ORDER BY alert_id DESC LIMIT ?'
        return [dict(r) for r in self._db.execute(q,(int(limit),))]
    def acknowledge(self, alert_id):
        with self._lock: self._db.execute('UPDATE runtime_alerts SET acknowledged=1 WHERE alert_id=?',(int(alert_id),)); self._db.commit()
    def event(self, created_at, kind, payload):
        with self._lock: self._db.execute('INSERT INTO ui_events(created_at,kind,payload_json) VALUES(?,?,?)',(created_at,kind,self._json(payload))); self._db.commit()
    def events(self, limit=100): return [dict(r) for r in self._db.execute('SELECT * FROM ui_events ORDER BY event_id DESC LIMIT ?',(int(limit),))]
    def close(self): self._db.close()
