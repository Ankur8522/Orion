import pytest
from orion.execution.persistent import PersistentPaperExecutionBook
from orion.ops.replay import write_replay, load_replay, _hash
from orion.ops.time_machine import TimeMachine
from orion.portfolio.allocation import DynamicCapitalAllocationBrain, AllocationCandidate
from orion.portfolio.performance import PortfolioPerformanceEngine
from orion.portfolio.risk_engine import PortfolioRiskEngine
from orion.research.factory import ResearchFactory

def test_paper_accounting_survives_restart(tmp_path):
    p=tmp_path/'paper.sqlite'; b=PersistentPaperExecutionBook(p)
    o=b.stage(security_id='A',target_weight=.5,current_weight=0,allowed=True,reason='x',lineage_hash='a'*64)
    b.fill(o.order_id,quantity=10,price=100,side='BUY',timestamp='2026-09-27T00:00:00Z',total_cost=2)
    b.mark('A',110); b.record_nav('2026-09-27T01:00:00Z'); b.close()
    b2=PersistentPaperExecutionBook(p)
    snap=b2.snapshot()
    assert snap['cash']==-1002 and snap['fees']==2 and snap['nav']==98
    b2.close()

def test_paper_short_rejection_is_atomic():
    b=PersistentPaperExecutionBook()
    o=b.stage(security_id='A',target_weight=.5,current_weight=0,allowed=True,reason='x',lineage_hash='a'*64)
    before=b.snapshot()
    with pytest.raises(ValueError): b.fill(o.order_id,quantity=1,price=100,side='SELL',timestamp='2026-09-27T00:00:00Z',total_cost=3)
    assert b.snapshot()==before

def test_replay_v3_binds_config_prompt_and_output(tmp_path):
    p=tmp_path/'r.json'; req={'decision_time':'2026-09-27T00:00:00Z','inputs':{'x':1},'config':{'v':2},'prompt':'p','output_hash':_hash({'ok':True})}
    write_replay(p,req); out=load_replay(p,expected_config_hash=_hash({'v':2}),expected_prompt_hash=_hash('p'),expected_output={'ok':True})
    assert out['inputs']=={'x':1}

def test_time_machine_chain_and_monotonicity(tmp_path):
    p=tmp_path/'tm.jsonl'; t=TimeMachine(p); t.record('1','2026-09-27T00:00:00Z',{'x':1}); t.record('2','2026-09-27T01:00:00Z',{'x':2})
    assert all(x.chain_hash for x in t.snapshots()) and t.replay().deterministic
    with pytest.raises(ValueError): t.record('3','2026-09-26T23:00:00Z',{'x':3})

def test_allocation_rejects_duplicate_ids_and_exposes_cash():
    b=DynamicCapitalAllocationBrain()
    with pytest.raises(ValueError): b.assess((AllocationCandidate('A',.1),AllocationCandidate('A',.2)))
    a=b.assess((AllocationCandidate('A',.1),),max_weight=.25)
    assert a.cash_weight >= .75

def test_risk_rejects_return_below_minus_one():
    with pytest.raises(ValueError): PortfolioRiskEngine().assess([-1.01],{'A':1})

def test_research_readiness_blocks_future_stale_and_contradicted():
    f=ResearchFactory()
    ds={k:{'available':True,'source_ids':['s']} for k in __import__('orion.research.factory',fromlist=['REQUIRED_DATASETS']).REQUIRED_DATASETS}
    ds['market_price']['available_time']='2026-09-28T00:00:00Z'
    ds['ohlcv']['evidence_state']='CONTRADICTED'
    r=f.readiness('A','2026-09-27T00:00:00Z',ds)
    assert not r.ready and any('FUTURE_AVAILABLE_TIME' in x for x in r.blockers) and any('EVIDENCE_CONTRADICTED' in x for x in r.blockers)

def test_performance_cashflow_metrics_are_optional():
    s=PortfolioPerformanceEngine().summarize([('2026-01-01T00:00:00Z',100),('2026-02-01T00:00:00Z',110)],cash_flows=[])
    assert s.time_weighted_return_pct is None and s.money_weighted_return_pct is None
