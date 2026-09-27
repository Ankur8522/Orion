from __future__ import annotations
import json, sqlite3, shutil
from pathlib import Path
from .time import parse_utc

SCHEMA='''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS observations(
 id INTEGER PRIMARY KEY AUTOINCREMENT, security_id TEXT NOT NULL, dataset TEXT NOT NULL,
 event_time TEXT NOT NULL, available_time TEXT NOT NULL, source_id TEXT NOT NULL,
 payload_hash TEXT NOT NULL, payload_json TEXT NOT NULL, captured_at TEXT NOT NULL,
 UNIQUE(security_id,dataset,event_time,available_time,source_id,payload_hash));
CREATE INDEX IF NOT EXISTS ix_obs_pit ON observations(security_id,dataset,event_time,available_time);
CREATE TABLE IF NOT EXISTS universe_snapshots(snapshot_id TEXT PRIMARY KEY,as_of TEXT NOT NULL,universe_name TEXT NOT NULL,security_id TEXT NOT NULL,metadata_json TEXT NOT NULL,UNIQUE(universe_name,as_of,security_id));
CREATE INDEX IF NOT EXISTS ix_universe ON universe_snapshots(universe_name,as_of);
CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,security_id TEXT NOT NULL,source_id TEXT NOT NULL,document_id TEXT NOT NULL,locator TEXT NOT NULL,claim TEXT NOT NULL,extracted_value_json TEXT,confidence REAL NOT NULL,available_time TEXT NOT NULL,content_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_evidence ON evidence(security_id,available_time);
CREATE TABLE IF NOT EXISTS jobs(job_key TEXT PRIMARY KEY,status TEXT NOT NULL,security_ids_json TEXT NOT NULL,cursor INTEGER NOT NULL DEFAULT 0,attempts INTEGER NOT NULL DEFAULT 0,error TEXT,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_captures(capture_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,url TEXT NOT NULL,payload_hash TEXT NOT NULL,captured_at TEXT NOT NULL,content_type TEXT NOT NULL,byte_size INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS normalized_financials(id INTEGER PRIMARY KEY AUTOINCREMENT,security_id TEXT NOT NULL,metric TEXT NOT NULL,period_end TEXT NOT NULL,value_text TEXT NOT NULL,unit TEXT NOT NULL,currency TEXT NOT NULL,source_id TEXT NOT NULL,available_time TEXT NOT NULL,UNIQUE(security_id,metric,period_end,source_id,available_time));
CREATE TABLE IF NOT EXISTS thesis_states(fingerprint TEXT PRIMARY KEY,security_id TEXT NOT NULL,decision_time TEXT NOT NULL,state TEXT NOT NULL,claims_json TEXT NOT NULL,evidence_ids_json TEXT NOT NULL,blockers_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS forecasts(
 forecast_id TEXT PRIMARY KEY, security_id TEXT NOT NULL, event_key TEXT NOT NULL,
 decision_time TEXT NOT NULL, horizon_end TEXT NOT NULL, probability REAL NOT NULL,
 evidence_ids_json TEXT NOT NULL, thesis_fingerprint TEXT NOT NULL, model_id TEXT NOT NULL, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_forecasts_security ON forecasts(security_id,decision_time);
CREATE TABLE IF NOT EXISTS forecast_outcomes(
 forecast_id TEXT PRIMARY KEY, occurred INTEGER NOT NULL, available_time TEXT NOT NULL,
 source_id TEXT NOT NULL, evidence_ids_json TEXT NOT NULL, content_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,object_id TEXT NOT NULL,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acquisition_manifests(manifest_id TEXT PRIMARY KEY,decision_time TEXT NOT NULL,universe_name TEXT NOT NULL,security_ids_json TEXT NOT NULL,blocked_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acquisition_jobs(job_id TEXT PRIMARY KEY,manifest_id TEXT NOT NULL,security_id TEXT NOT NULL,source_id TEXT NOT NULL,dataset TEXT NOT NULL,url TEXT NOT NULL,event_time TEXT NOT NULL,available_time TEXT NOT NULL,decision_time TEXT NOT NULL,state TEXT NOT NULL,error TEXT,updated_at TEXT NOT NULL,UNIQUE(manifest_id,security_id,source_id,dataset));
CREATE INDEX IF NOT EXISTS ix_acq_jobs_manifest ON acquisition_jobs(manifest_id,state);
CREATE TABLE IF NOT EXISTS market_batch_manifests(manifest_id TEXT PRIMARY KEY,decision_time TEXT NOT NULL,universe_names_json TEXT NOT NULL,blocked_json TEXT NOT NULL,batch_count INTEGER NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS market_batch_jobs(job_id TEXT PRIMARY KEY,manifest_id TEXT NOT NULL,security_id TEXT NOT NULL,instrument_key TEXT NOT NULL,unit TEXT NOT NULL,interval INTEGER NOT NULL,to_date TEXT NOT NULL,from_date TEXT NOT NULL,decision_time TEXT NOT NULL,state TEXT NOT NULL,error TEXT,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_market_batch_jobs_manifest ON market_batch_jobs(manifest_id,state);
CREATE TABLE IF NOT EXISTS dataset_coverage_ledger(manifest_id TEXT NOT NULL,security_id TEXT NOT NULL,dataset TEXT NOT NULL,status TEXT NOT NULL,observations INTEGER NOT NULL,latest_available TEXT,checked_at TEXT NOT NULL,error TEXT,PRIMARY KEY(manifest_id,security_id,dataset));
CREATE INDEX IF NOT EXISTS ix_dataset_coverage_manifest ON dataset_coverage_ledger(manifest_id,dataset,status);
CREATE TABLE IF NOT EXISTS market_schedule(manifest_id TEXT PRIMARY KEY,next_batch INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'PLANNED',updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS instrument_mappings(security_id TEXT NOT NULL,provider TEXT NOT NULL,instrument_key TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT,available_time TEXT NOT NULL,source_id TEXT NOT NULL,content_hash TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(security_id,provider,effective_from));
CREATE INDEX IF NOT EXISTS ix_instrument_mapping_pit ON instrument_mappings(security_id,provider,effective_from,available_time,status);
'''
class SQLiteStore:
    def __init__(self,path='orion.db'):
        self.path=str(path); self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row; self.db.executescript(SCHEMA); self.db.commit()
    def close(self): self.db.close()
    def insert_observation(self,*,security_id,dataset,event_time,available_time,source_id,payload_hash,payload,captured_at):
        parse_utc(event_time); parse_utc(available_time); parse_utc(captured_at)
        if parse_utc(available_time)<parse_utc(event_time): raise ValueError('INVALID_TEMPORAL_ORDER')
        cur=self.db.execute('''INSERT OR IGNORE INTO observations(security_id,dataset,event_time,available_time,source_id,payload_hash,payload_json,captured_at) VALUES(?,?,?,?,?,?,?,?)''',(security_id,dataset,event_time,available_time,source_id,payload_hash,json.dumps(payload,sort_keys=True,separators=(',',':')),captured_at)); self.db.commit(); return cur.lastrowid
    def pit(self,security_id,dataset,decision_time):
        parse_utc(decision_time)
        return [dict(r) for r in self.db.execute('''SELECT * FROM observations WHERE security_id=? AND dataset=? AND available_time<=? ORDER BY event_time,available_time,id''',(security_id,dataset,decision_time))]
    def evidence_for(self,security_id,decision_time):
        parse_utc(decision_time); return [dict(r) for r in self.db.execute('SELECT * FROM evidence WHERE security_id=? AND available_time<=? ORDER BY available_time,evidence_id',(security_id,decision_time))]
    def upsert_universe(self,snapshot_id,as_of,universe_name,security_id,metadata):
        parse_utc(as_of); self.db.execute('INSERT OR REPLACE INTO universe_snapshots VALUES(?,?,?,?,?)',(snapshot_id,as_of,universe_name,security_id,json.dumps(metadata,sort_keys=True))); self.db.commit()
    def universe(self,universe_name,as_of): return self.db.execute('SELECT security_id,metadata_json FROM universe_snapshots WHERE universe_name=? AND as_of=? ORDER BY security_id',(universe_name,as_of)).fetchall()
    def evidence(self,evidence_id,security_id,source_id,document_id,locator,claim,extracted_value,confidence,available_time,content_hash):
        parse_utc(available_time)
        if not 0<=confidence<=1: raise ValueError('INVALID_CONFIDENCE')
        self.db.execute('INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)',(evidence_id,security_id,source_id,document_id,locator,claim,json.dumps(extracted_value,sort_keys=True),confidence,available_time,content_hash)); self.db.commit()
    def source_capture(self,capture_id,source_id,url,payload_hash,captured_at,content_type,byte_size):
        parse_utc(captured_at)
        self.db.execute('INSERT OR IGNORE INTO source_captures VALUES(?,?,?,?,?,?,?)',(capture_id,source_id,url,payload_hash,captured_at,content_type,byte_size)); self.db.commit()

    def normalized_financial(self,row):
        from decimal import Decimal
        parse_utc(row['available_time'])
        self.db.execute('INSERT OR IGNORE INTO normalized_financials(security_id,metric,period_end,value_text,unit,currency,source_id,available_time) VALUES(?,?,?,?,?,?,?,?)',(row['security_id'],row['metric'],row['period_end'],str(Decimal(str(row['value']))),row['unit'],row['currency'],row['source_id'],row['available_time'])); self.db.commit()

    def thesis_state(self,state):
        self.db.execute('INSERT OR REPLACE INTO thesis_states VALUES(?,?,?,?,?,?,?)',(state.fingerprint,state.security_id,state.decision_time,state.state.value,json.dumps(list(state.claims)),json.dumps(list(state.evidence_ids)),json.dumps(list(state.blockers)))); self.db.commit()


    def forecast(self, forecast):
        from ..learning.feedback import ForecastRecord
        if not isinstance(forecast, ForecastRecord): raise TypeError('INVALID_FORECAST')
        self.db.execute('''INSERT OR IGNORE INTO forecasts
            (forecast_id,security_id,event_key,decision_time,horizon_end,probability,evidence_ids_json,thesis_fingerprint,model_id,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)''',
            (forecast.forecast_id,forecast.security_id,forecast.event_key,forecast.decision_time,
             forecast.horizon_end,forecast.probability,json.dumps(list(forecast.evidence_ids)),
             forecast.thesis_fingerprint,forecast.model_id,forecast.created_at))
        self.db.commit()

    def forecast_outcome(self, outcome):
        from ..learning.feedback import OutcomeRecord
        if not isinstance(outcome, OutcomeRecord): raise TypeError('INVALID_OUTCOME')
        self.db.execute('''INSERT OR REPLACE INTO forecast_outcomes
            (forecast_id,occurred,available_time,source_id,evidence_ids_json,content_hash)
            VALUES(?,?,?,?,?,?)''',
            (outcome.forecast_id,int(outcome.occurred),outcome.available_time,outcome.source_id,
             json.dumps(list(outcome.evidence_ids)),outcome.content_hash))
        self.db.commit()

    def forecasts_for(self, security_id, decision_time=None):
        q='SELECT * FROM forecasts WHERE security_id=?'; args=[security_id]
        if decision_time is not None:
            parse_utc(decision_time); q += ' AND decision_time<=?'; args.append(decision_time)
        q += ' ORDER BY decision_time,forecast_id'
        return [dict(r) for r in self.db.execute(q,args)]

    def forecasts_for_all(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM forecasts ORDER BY decision_time,forecast_id')]

    def forecast_outcomes_for_all(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM forecast_outcomes ORDER BY forecast_id')]

    def forecast_outcomes_for(self, forecast_ids=()):
        ids=tuple(forecast_ids)
        if not ids: return []
        marks=','.join('?' for _ in ids)
        return [dict(r) for r in self.db.execute(f'SELECT * FROM forecast_outcomes WHERE forecast_id IN ({marks}) ORDER BY forecast_id',ids)]

    def audit(self,ts,actor,action,object_id,details):
        parse_utc(ts); self.db.execute('INSERT INTO audit_log(ts,actor,action,object_id,details_json) VALUES(?,?,?,?,?)',(ts,actor,action,object_id,json.dumps(details,sort_keys=True))); self.db.commit()
    def job_upsert(self,key,status,security_ids,cursor=0,attempts=0,error=None,updated_at='1970-01-01T00:00:00Z'):
        parse_utc(updated_at); self.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?) ON CONFLICT(job_key) DO UPDATE SET status=excluded.status,security_ids_json=excluded.security_ids_json,cursor=excluded.cursor,attempts=excluded.attempts,error=excluded.error,updated_at=excluded.updated_at',(key,status,json.dumps(list(security_ids)),cursor,attempts,error,updated_at)); self.db.commit()
    def job(self,key):
        r=self.db.execute('SELECT * FROM jobs WHERE job_key=?',(key,)).fetchone(); return dict(r) if r else None
    def acquisition_manifest(self,manifest,created_at):
        parse_utc(created_at)
        self.db.execute('INSERT OR REPLACE INTO acquisition_manifests VALUES(?,?,?,?,?,?)',(manifest.manifest_id,manifest.decision_time,manifest.universe_name,json.dumps(list(manifest.security_ids)),json.dumps(list(manifest.blocked)),created_at))
        for j in manifest.jobs:
            self.db.execute('INSERT OR REPLACE INTO acquisition_jobs(job_id,manifest_id,security_id,source_id,dataset,url,event_time,available_time,decision_time,state,error,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(j.job_id,manifest.manifest_id,j.security_id,j.source_id,j.dataset,j.url,j.event_time,j.available_time,j.decision_time,'PLANNED',None,created_at))
        self.db.commit()
    def acquisition_jobs(self,manifest_id):
        return [dict(r) for r in self.db.execute('SELECT * FROM acquisition_jobs WHERE manifest_id=? ORDER BY security_id,dataset,source_id',(manifest_id,))]
    def acquisition_job_state(self,job_id,state,updated_at,error=None):
        parse_utc(updated_at); self.db.execute('UPDATE acquisition_jobs SET state=?,error=?,updated_at=? WHERE job_id=?',(state,error,updated_at,job_id)); self.db.commit()

    def acquisition_coverage(self, security_ids, *, dataset='ohlcv', decision_time=None):
        ids=tuple(dict.fromkeys(str(x) for x in security_ids if str(x)))
        if not ids: return {'requested':0,'covered':0,'missing':[],'coverage_pct':0.0,'status':'NO_REQUESTS'}
        if decision_time is not None: parse_utc(decision_time)
        marks=','.join('?' for _ in ids)
        args=[dataset,*ids]
        q=f'SELECT security_id, MAX(available_time) AS latest_available, COUNT(*) AS observations FROM observations WHERE dataset=? AND security_id IN ({marks})'
        if decision_time is not None: q += ' AND available_time<=?'; args.append(decision_time)
        q += ' GROUP BY security_id'
        rows={r['security_id']:dict(r) for r in self.db.execute(q,args)}
        missing=sorted(set(ids)-set(rows))
        covered=len(ids)-len(missing); pct=round(covered/len(ids)*100.0,4)
        return {'requested':len(ids),'covered':covered,'missing':missing,'coverage_pct':pct,'status':'READY' if not missing else ('PARTIAL' if covered else 'BLOCKED'),'latest_available':max((r['latest_available'] for r in rows.values()),default=None)}

    def acquisition_coverage_for_manifest(self, manifest_id, *, decision_time=None):
        jobs=self.acquisition_jobs(manifest_id)
        return self.acquisition_coverage([j['security_id'] for j in jobs], dataset='ohlcv', decision_time=decision_time)


    def market_batch_manifest(self, manifest, created_at):
        parse_utc(created_at)
        self.db.execute('INSERT OR IGNORE INTO market_batch_manifests VALUES(?,?,?,?,?,?)',(
            manifest.manifest_id,manifest.decision_time,json.dumps(list(manifest.universe_names)),json.dumps(list(manifest.blocked)),len(manifest.batches),created_at))
        for j in manifest.jobs:
            self.db.execute('INSERT OR IGNORE INTO market_batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(
                j.job_id,manifest.manifest_id,j.security_id,j.instrument_key,j.unit,j.interval,j.to_date,j.from_date,j.decision_time,'PLANNED',None,created_at))
        self.db.commit()

    def market_batch_jobs(self, manifest_id):
        return [dict(r) for r in self.db.execute('SELECT * FROM market_batch_jobs WHERE manifest_id=? ORDER BY security_id',(manifest_id,))]

    def market_batch_state(self, job_id, state, updated_at, error=None):
        parse_utc(updated_at)
        self.db.execute('UPDATE market_batch_jobs SET state=?,error=?,updated_at=? WHERE job_id=?',(state,error,updated_at,job_id)); self.db.commit()
    def market_batch_coverage(self, manifest_id, *, decision_time=None, dataset='ohlcv', checked_at=None):
        if decision_time is not None: parse_utc(decision_time)
        checked_at = checked_at or __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00','Z')
        parse_utc(checked_at)
        jobs=self.market_batch_jobs(manifest_id)
        ids=tuple(dict.fromkeys(j['security_id'] for j in jobs))
        if not ids:
            return {'manifest_id':manifest_id,'dataset':dataset,'requested':0,'covered':0,'coverage_pct':0.0,'status':'NO_REQUESTS','checked_at':checked_at,'missing':[]}
        marks=','.join('?' for _ in ids)
        rows={}
        if ids:
            args=[dataset,*ids]
            q=f'SELECT security_id,COUNT(*) observations,MAX(available_time) latest_available FROM observations WHERE dataset=? AND security_id IN ({marks})'
            if decision_time is not None: q += ' AND available_time<=?'; args.append(decision_time)
            q += ' GROUP BY security_id'
            rows={r['security_id']:dict(r) for r in self.db.execute(q,args)}
        for sid in ids:
            r=rows.get(sid)
            state='READY' if r else 'NO_OBSERVATION'
            self.db.execute('INSERT OR REPLACE INTO dataset_coverage_ledger VALUES(?,?,?,?,?,?,?,?)',(manifest_id,sid,dataset,state,int(r['observations']) if r else 0,r['latest_available'] if r else None,checked_at,None))
        self.db.commit()
        covered=sum(1 for sid in ids if sid in rows); total=len(ids)
        return {'manifest_id':manifest_id,'dataset':dataset,'requested':total,'covered':covered,'coverage_pct':round(covered/total*100,4) if total else 0.0,'status':'READY' if covered==total and total else ('PARTIAL' if covered else 'BLOCKED'),'checked_at':checked_at,'missing':sorted(set(ids)-set(rows))}

    def dataset_coverage_ledger(self, manifest_id, *, dataset='ohlcv'):
        return [dict(r) for r in self.db.execute('SELECT * FROM dataset_coverage_ledger WHERE manifest_id=? AND dataset=? ORDER BY security_id',(manifest_id,dataset))]

    def market_schedule_register(self, manifest, updated_at):
        parse_utc(updated_at); self.db.execute('INSERT OR IGNORE INTO market_schedule(manifest_id,next_batch,status,updated_at) VALUES(?,?,?,?)',(manifest.manifest_id,0,'PLANNED',updated_at)); self.db.commit()

    def market_schedule_state(self, manifest_id):
        r=self.db.execute('SELECT * FROM market_schedule WHERE manifest_id=?',(manifest_id,)).fetchone(); return dict(r) if r else None

    def market_schedule_checkpoint(self, manifest_id, next_batch, updated_at):
        parse_utc(updated_at); self.db.execute('UPDATE market_schedule SET next_batch=?,status=?,updated_at=? WHERE manifest_id=?',(int(next_batch),'RUNNING',updated_at,manifest_id)); self.db.commit()

    def instrument_mapping(self, mapping):
        parse_utc(mapping.effective_from); parse_utc(mapping.available_time)
        if mapping.effective_to is not None: parse_utc(mapping.effective_to)
        self.db.execute('''INSERT OR REPLACE INTO instrument_mappings
            (security_id,provider,instrument_key,effective_from,effective_to,available_time,source_id,content_hash,status)
            VALUES(?,?,?,?,?,?,?,?,?)''', (mapping.security_id,mapping.provider,mapping.instrument_key,mapping.effective_from,mapping.effective_to,mapping.available_time,mapping.source_id,mapping.content_hash,mapping.status))
        self.db.commit()

    def instrument_mapping_resolve(self, security_id, *, provider, as_of):
        parse_utc(as_of)
        row=self.db.execute('''SELECT * FROM instrument_mappings
            WHERE security_id=? AND provider=? AND status='VERIFIED'
              AND available_time<=? AND effective_from<=?
              AND (effective_to IS NULL OR effective_to>?)
            ORDER BY effective_from DESC, available_time DESC LIMIT 1''', (security_id,provider,as_of,as_of,as_of)).fetchone()
        if not row: return None
        from ..acquisition.instrument_registry import InstrumentMapping
        return InstrumentMapping(**dict(row))

    def instrument_mappings(self, *, provider=None):
        if provider is None: rows=self.db.execute('SELECT * FROM instrument_mappings ORDER BY provider,security_id,effective_from')
        else: rows=self.db.execute('SELECT * FROM instrument_mappings WHERE provider=? ORDER BY security_id,effective_from',(provider,))
        return [dict(r) for r in rows]

    def backup(self,destination):
        dest=sqlite3.connect(str(destination)); self.db.backup(dest); dest.close()
