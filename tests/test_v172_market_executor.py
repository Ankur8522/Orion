from pathlib import Path
from orion.acquisition.market_executor import MarketBatchExecutor
from orion.acquisition.universe_batch import UniverseMarketDataPlanner
from orion.acquisition.market_data import UpstoxMarketDataAcquirer
from orion.data.store import SQLiteStore
from orion.providers.upstox_readonly import UpstoxReadOnlyClient

def test_coverage_ledger_and_resume(tmp_path):
    store=SQLiteStore(tmp_path/'a.sqlite')
    planner=UniverseMarketDataPlanner(batch_size=2)
    manifest=planner.plan([{'index':'NIFTY50','security_id':'AAA'}], {'AAA':'NSE_EQ|AAA'}, decision_time='2026-01-10T00:00:00Z', from_date='2026-01-01', to_date='2026-01-09')
    class FakeAcq:
        def __init__(self): self.calls=0
        def acquire(self, job):
            self.calls+=1
            return type('R',(),{'state':'PROMOTED','error':None,'job_id':job.job_id,'security_id':job.security_id,'rows':1,'payload_hash':'x'})()
    acq=FakeAcq(); ex=MarketBatchExecutor(acq,store,clock=lambda:'2026-01-10T00:00:00Z')
    r1=ex.execute(manifest); r2=ex.execute(manifest)
    assert r1.attempted==1 and r2.skipped==1 and acq.calls==1
    assert r1.coverage['status']=='BLOCKED'
    assert store.dataset_coverage_ledger(manifest.manifest_id)[0]['status']=='NO_OBSERVATION'

def test_manifest_coverage_endpoint_surface():
    from orion.app.gateway import RuntimeGateway
    from orion.data.store import SQLiteStore
    import os
    from pathlib import Path
    # Surface is read-only and returns a deterministic missing-manifest shape.
    g=RuntimeGateway()
    out=g.acquisition_manifest_coverage('does-not-exist')
    assert out['coverage']['status']=='NO_REQUESTS'
