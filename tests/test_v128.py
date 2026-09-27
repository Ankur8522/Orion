import json, tempfile
from pathlib import Path
from orion.data.store import SQLiteStore
from orion.data.universe import Security, UniverseBuilder
from orion.data.http_provider import PublicHTTPProvider
from orion.data.providers import hash_payload
from orion.ops.replay import write_replay, load_replay
from orion.ops.observability import Metrics
from orion.app.health import check_store, readiness
from orion.research.batch import BatchExecutor
from orion.data.pit import PITStore, Observation
from orion.research.queue import ResearchQueue
from orion.research.pipeline import Pipeline


def test_sqlite_pit_and_backup(tmp_path):
    db=SQLiteStore(tmp_path/'a.db')
    db.insert_observation(security_id='S1',dataset='results',event_time='2026-01-01T00:00:00Z',available_time='2026-01-02T00:00:00Z',source_id='nse',payload_hash=hash_payload(b'x'),payload={'pat':10},captured_at='2026-01-02T01:00:00Z')
    assert len(db.pit('S1','results','2026-01-03T00:00:00Z'))==1
    db.backup(tmp_path/'b.db')
    db.close()
    assert (tmp_path/'b.db').exists()

def test_universe_filters():
    rows=[Security('1','NSE','A','A',5000),Security('2','NSE','B','B',2999),Security('3','NSE','C','C',6000,sme=True),Security('4','NSE','D','D',7000,suspended=True)]
    assert [x.security_id for x in UniverseBuilder().build(rows)]==['1']

def test_public_provider_allowlist():
    p=PublicHTTPProvider({'www.nseindia.com'})
    try: p.fetch('http://www.nseindia.com/x')
    except ValueError as e: assert str(e)=='URL_NOT_ALLOWLISTED'
    else: raise AssertionError('expected scheme block')

def test_replay_roundtrip(tmp_path):
    x={'security_ids':['S1'],'decision_time':'2026-01-03T00:00:00Z'}; f=tmp_path/'r.json'; write_replay(f,x); assert load_replay(f)==x

def test_metrics():
    m=Metrics(); m.inc('jobs'); m.observe_ms('research',10); m.observe_ms('research',20); assert m.snapshot()['counters']['jobs']==1 and m.snapshot()['timings_ms']['research']['avg']==15

def test_health(tmp_path):
    s=SQLiteStore(tmp_path/'h.db'); assert readiness([check_store(s)])['status']=='READY'; s.close()

def test_batch_executor():
    p=PITStore()
    for sid in ['S1','S2','S3']:
        p.append(Observation(sid,'2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',1,'e'))
    r=BatchExecutor(Pipeline(p,ResearchQueue()),batch_size=2).run(['S1','S2','S3'],'2026-01-03T00:00:00Z')
    assert (r.total,r.completed,r.failed)==(3,3,0)
