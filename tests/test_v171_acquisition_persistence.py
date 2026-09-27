from orion.acquisition.universe_batch import UniverseMarketDataPlanner
from orion.data.store import SQLiteStore


def test_market_batch_manifest_and_jobs_persist(tmp_path):
    ms=[{'index':'NIFTY50','security_id':f'S{i}','active':True} for i in range(3)]
    keys={f'S{i}':f'NSE_EQ|S{i}' for i in range(3)}
    m=UniverseMarketDataPlanner(batch_size=2).plan(ms,keys,decision_time='2026-09-27T03:00:00Z',from_date='2026-01-01',to_date='2026-09-26')
    s=SQLiteStore(tmp_path/'a.db'); s.market_batch_manifest(m,'2026-09-27T03:01:00Z'); s.close()
    s=SQLiteStore(tmp_path/'a.db'); rows=s.market_batch_jobs(m.manifest_id)
    assert len(rows)==3 and {r['state'] for r in rows}=={'PLANNED'}
    s.close()
