from orion.portfolio.decision_gate import PortfolioDecisionGate
from orion.portfolio.allocation import DynamicCapitalAllocationBrain, AllocationCandidate
from orion.portfolio.risk_gate import PortfolioRiskGate
from orion.execution.paper import PaperExecutionBook

def test_portfolio_decision_gate_blocks_risky_or_unready_paper_decision():
    a=DynamicCapitalAllocationBrain().assess((AllocationCandidate('A',.1,uncertainty=.2),))
    r=PortfolioRiskGate().evaluate(exposure=.8)
    d=PortfolioDecisionGate().evaluate(a,r,research_ready=True,data_ready=True)
    assert d.blocked and d.status=='BLOCKED'

def test_portfolio_decision_gate_allows_only_paper_when_safe():
    a=DynamicCapitalAllocationBrain().assess((AllocationCandidate('A',.1,uncertainty=.2),))
    r=PortfolioRiskGate().evaluate()
    d=PortfolioDecisionGate().evaluate(a,r,research_ready=True,data_ready=True)
    assert not d.blocked and d.status=='APPROVED_FOR_PAPER_ONLY'

def test_paper_book_tracks_cash_and_fees():
    b=PaperExecutionBook(); o=b.stage(security_id='A',target_weight=.5,current_weight=0,allowed=True,reason='x',lineage_hash='a'*64)
    b.fill(o.order_id,quantity=10,price=100,side='BUY',timestamp='2026-09-27T00:00:00Z',total_cost=2.5)
    assert b.snapshot()['cash']==-1002.5 and b.snapshot()['fees']==2.5
