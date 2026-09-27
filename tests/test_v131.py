import pytest
from orion.agents.research_society import EvidenceAuditor, opinion, AdversarialReview
from orion.model.world import WorldModel
from orion.quant.safe_backtest import PITBacktest
from orion.research.priority import PriorityEngine
from orion.research.orchestrator import ResearchOrchestrator
from orion.brain.state import EvidenceState
from orion.portfolio.health import assess

def ev(eid='e1', available='2026-01-02T00:00:00Z', confidence=.9):
    return {'evidence_id':eid,'available_time':available,'confidence':confidence,'content_hash':'a'*64}

def test_evidence_audit_filters_future_and_bad_confidence():
    r=EvidenceAuditor().audit([ev(),ev('future','2026-02-01T00:00:00Z'),ev('bad',confidence=2)],'2026-01-10T00:00:00Z')
    assert r.accepted==('e1',) and set(r.rejected)=={'bad','future'}

def test_adversarial_review_preserves_disagreement():
    a=opinion('bull','S1','growth',["e1"]); b=opinion('bear','S1','risk',["e1"])
    r=AdversarialReview().review([a,b],EvidenceAuditor().audit([ev()],'2026-01-10T00:00:00Z'))
    assert r['status']=='REVIEW' and 'THESIS_DISAGREEMENT' in r['disagreements']

def test_world_model_second_order_path():
    w=WorldModel(); w.add('CRUDE','cost','INPUT'); w.add('INPUT','margin_pressure','COMPANY'); assert len(w.shock_path('CRUDE',2))==2

def test_backtest_rejects_lookahead_and_costs():
    rows=[{'available_time':'2026-01-01T00:00:00Z','return':.10},{'available_time':'2026-02-01T00:00:00Z','return':.20}]
    r=PITBacktest(10,5).run(rows,'2026-01-15T00:00:00Z'); assert r.rejected_lookahead==1 and r.net_return<r.gross_return

def test_priority_bounded():
    r=PriorityEngine().score('S1',data_gap=1,thesis_change=1,event_urgency=1,portfolio_exposure=1,evidence_risk=1); assert r.score==100

def test_orchestrator_blocks_missing_evidence():
    r=ResearchOrchestrator().run('S1','2026-01-10T00:00:00Z',[],[opinion('a','S1','x',[])])
    assert r.thesis_state.state==EvidenceState.UNCERTAIN

def test_orchestrator_supported_with_audited_evidence():
    r=ResearchOrchestrator().run('S1','2026-01-10T00:00:00Z',[ev()],[opinion('a','S1','x',['e1'])])
    assert r.thesis_state.state==EvidenceState.SUPPORTED

def test_health():
    from orion.brain.state import BrainStateBuilder
    s=BrainStateBuilder().build('S1','2026-01-10T00:00:00Z',['x'],['e1'])
    assert assess('S1',s,1).status=='GREEN'
