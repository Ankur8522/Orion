from datetime import datetime, timezone
from pathlib import Path
from orion.data.store import SQLiteStore
from orion.acquisition.scheduler import AcquisitionScheduler
from orion.acquisition.market_executor import MarketBatchExecutor
from orion.acquisition.universe_batch import UniverseMarketDataPlanner

class StubAcquirer:
    def acquire(self, job):
        from orion.acquisition.market_data import MarketDataJobResult
        return MarketDataJobResult(job.job_id, job.security_id, 'BLOCKED', 0, None, 'NO_PROVIDER')

def manifest(tmp_path):
    p=UniverseMarketDataPlanner(batch_size=2)
    return p.plan([{'index':'NIFTY50','security_id':f'S{i}'} for i in range(5)], {f'S{i}':f'KEY{i}' for i in range(5)}, decision_time='2026-01-01T00:00:00Z', from_date='2025-01-01', to_date='2025-01-05')

def test_scheduler_checkpoints_batches(tmp_path):
    st=SQLiteStore(tmp_path/'db.sqlite'); m=manifest(tmp_path)
    ex=MarketBatchExecutor(StubAcquirer(),st,clock=lambda:'2026-01-01T00:00:00Z')
    sch=AcquisitionScheduler(ex,st,clock=lambda:'2026-01-01T00:00:00Z')
    r=sch.run(m,max_batches=1)
    assert r.batches_completed==1 and r.batches_remaining==2
    assert st.market_schedule_state(m.manifest_id)['next_batch']==1
    r2=sch.run(m)
    assert r2.batches_completed==3 and r2.batches_remaining==0
    st.close()

def test_scheduler_rejects_invalid_limit(tmp_path):
    st=SQLiteStore(tmp_path/'db.sqlite'); m=manifest(tmp_path)
    ex=MarketBatchExecutor(StubAcquirer(),st); sch=AcquisitionScheduler(ex,st)
    try: sch.run(m,max_batches=0)
    except ValueError as e: assert str(e)=='INVALID_MAX_BATCHES'
    else: assert False
    st.close()
