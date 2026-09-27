from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .feedback import ForecastLedger, ForecastRecord, OutcomeRecord

class PersistentForecastLedger(ForecastLedger):
    """SQLite-backed forecast/outcome ledger for restart-safe closed-loop learning."""
    def __init__(self, path=':memory:'):
        super().__init__(); self.path=str(path); self._db=sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute('CREATE TABLE IF NOT EXISTS forecasts (forecast_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS outcomes (forecast_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.commit(); self._hydrate()
    @staticmethod
    def _f(f): return f.__dict__ | {'evidence_ids':list(f.evidence_ids)}
    @staticmethod
    def _o(o): return o.__dict__ | {'evidence_ids':list(o.evidence_ids)}
    def _hydrate(self):
        for (p,) in self._db.execute('SELECT payload FROM forecasts ORDER BY forecast_id'):
            x=json.loads(p); x['evidence_ids']=tuple(x['evidence_ids']); super().issue(ForecastRecord(**x))
        for (p,) in self._db.execute('SELECT payload FROM outcomes ORDER BY forecast_id'):
            x=json.loads(p); x['evidence_ids']=tuple(x['evidence_ids']); self._outcomes[x['forecast_id']]=OutcomeRecord(**x)
    def issue(self, forecast):
        result=super().issue(forecast); self._db.execute('INSERT OR REPLACE INTO forecasts VALUES(?,?)',(forecast.forecast_id,json.dumps(self._f(forecast),sort_keys=True))); self._db.commit(); return result
    def resolve(self, outcome, *, evaluation_time):
        result=super().resolve(outcome,evaluation_time=evaluation_time); self._db.execute('INSERT OR REPLACE INTO outcomes VALUES(?,?)',(outcome.forecast_id,json.dumps(self._o(outcome),sort_keys=True))); self._db.commit(); return result
    def close(self): self._db.close()
