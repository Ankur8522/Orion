from orion.acquisition.universe_batch import UniverseMarketDataPlanner
from orion.data.store import SQLiteStore


def memberships():
    return ([{'index':'NIFTY50','security_id':f'S{i}','active':True} for i in range(50)] +
            [{'index':'NIFTY_MIDCAP150','security_id':f'M{i}','active':True} for i in range(150)] +
            [{'index':'NIFTY_SMALLCAP250','security_id':f'L{i}','active':True} for i in range(250)])


def test_planner_covers_450_slots_and_batches_deterministically():
    ms=memberships(); keys={m['security_id']:f'NSE_EQ|{m["security_id"]}' for m in ms}
    p=UniverseMarketDataPlanner(batch_size=25)
    a=p.plan(ms,keys,decision_time='2026-09-27T03:00:00Z',from_date='2026-01-01',to_date='2026-09-26')
    b=p.plan(ms,keys,decision_time='2026-09-27T03:00:00Z',from_date='2026-01-01',to_date='2026-09-26')
    assert len(a.requests)==450 and len(a.jobs)==450 and len(a.blocked)==0
    assert len(a.batches)==18 and all(len(x)==25 for x in a.batches)
    assert a.manifest_id==b.manifest_id and a.jobs==b.jobs


def test_planner_blocks_missing_instrument_mapping_without_fabrication():
    ms=[{'index':'NIFTY50','security_id':'A','active':True},{'index':'NIFTY50','security_id':'B','active':True}]
    p=UniverseMarketDataPlanner()
    a=p.plan(ms,{'A':'NSE_EQ|A'},decision_time='2026-09-27T03:00:00Z',from_date='2026-01-01',to_date='2026-09-26')
    assert len(a.jobs)==1 and a.blocked==('B:ohlcv:NO_INSTRUMENT_MAPPING',)


def test_coverage_is_pit_bounded_and_persistent(tmp_path):
    s=SQLiteStore(tmp_path/'o.db')
    s.insert_observation(security_id='A',dataset='ohlcv',event_time='2026-09-25T00:00:00Z',available_time='2026-09-26T10:00:00Z',source_id='upstox',payload_hash='h',payload={'x':1},captured_at='2026-09-26T10:01:00Z')
    x=s.acquisition_coverage(['A','B'],decision_time='2026-09-26T12:00:00Z')
    assert x['covered']==1 and x['coverage_pct']==50.0 and x['status']=='PARTIAL'
    y=s.acquisition_coverage(['A'],decision_time='2026-09-26T09:00:00Z')
    assert y['covered']==0 and y['status']=='BLOCKED'
    s.close()
