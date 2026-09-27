import pytest
from orion.data.pit import PITStore,Observation
from orion.data.store import SQLiteStore
from orion.data.quality import DataQualityGate
from orion.research.pipeline import Pipeline
from orion.research.queue import ResearchQueue
from orion.research.batch import BatchExecutor
from orion.data.providers import hash_payload

def test_pit_rejects_bad_time_and_orders():
    p=PITStore()
    with pytest.raises(ValueError): p.append(Observation('S','2026-01-01','2026-01-02',1,'x'))
    p.append(Observation('S','2026-01-01T00:00:00Z','2026-01-03T00:00:00Z',1,'x'))
    assert len(p.as_of('S','2026-01-04T00:00:00Z'))==1

def test_sqlite_dedup_and_quality(tmp_path):
    s=SQLiteStore(tmp_path/'a.db'); kw=dict(security_id='S',dataset='results',event_time='2026-01-01T00:00:00Z',available_time='2026-01-02T00:00:00Z',source_id='nse',payload_hash=hash_payload(b'x'),payload={'pat':1},captured_at='2026-01-02T01:00:00Z')
    s.insert_observation(**kw); s.insert_observation(**kw); assert len(s.pit('S','results','2026-01-03T00:00:00Z'))==1
    assert DataQualityGate(s).check('S','2026-01-03T00:00:00Z').status=='PASS'

def test_batch_checkpoint(tmp_path):
    p=PITStore()
    for sid in ['S1','S2','S3']: p.append(Observation(sid,'2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',1,'e','results'))
    s=SQLiteStore(tmp_path/'j.db'); b=BatchExecutor(Pipeline(p,ResearchQueue()),2,s)
    r=b.run(['S1','S2','S3'],'2026-01-03T00:00:00Z','job1'); assert r.checkpoint==3 and s.job('job1')['status']=='COMPLETE'
