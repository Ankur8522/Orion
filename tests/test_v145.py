from orion.decision.plane import ResearchDecisionPlane, AgentFinding, Uncertainty, DecisionState
from orion.decision.evidence import EvidenceAdjudicator, EvidenceItem
from orion.decision.causal import CausalEngine
from orion.decision.replay import RunManifest, ReplayGuard
from orion.portfolio.risk_gate import PortfolioRiskGate
from hashlib import sha256

H='a'*64

def test_plan_is_bounded_and_deterministic():
    p=ResearchDecisionPlane(max_parallel_agents=4,max_retries=1)
    a=p.plan(security_id='S1',decision_time='2026-09-26T10:00:00Z',required_agents=['bear','fundamental','bear'])
    assert a['agents']==('bear','fundamental') and a['max_parallel_agents']==4

def test_unsupported_evidence_blocks():
    p=ResearchDecisionPlane()
    d=p.adjudicate(security_id='S1',decision_time='2026-09-26T10:00:00Z',findings=[AgentFinding('fundamental','SUPPORT',('e1',))],evidence_ids=('e1',),evidence_state='REVIEW',thesis='x')
    assert d.state==DecisionState.BLOCKED and 'EVIDENCE_NOT_SUPPORTED' in d.unresolved

def test_material_disagreement_escalates():
    p=ResearchDecisionPlane()
    fs=[AgentFinding('bull','SUPPORT',('e1',),('growth',)),AgentFinding('bear','CHALLENGE',('e1',),('risk',))]
    d=p.adjudicate(security_id='S1',decision_time='2026-09-26T10:00:00Z',findings=fs,evidence_ids=('e1',),thesis='x')
    assert d.state==DecisionState.ESCALATE and 'MATERIAL_DISAGREEMENT' in d.unresolved

def test_high_uncertainty_defers():
    p=ResearchDecisionPlane()
    u=Uncertainty(data=.8,evidence=.7,model=.8,causal=.6,valuation=.7,timing=.8,regime=.7,outcome=.8)
    d=p.adjudicate(security_id='S1',decision_time='2026-09-26T10:00:00Z',findings=[AgentFinding('fundamental','SUPPORT',('e1',))],evidence_ids=('e1',),uncertainty=u,thesis='x')
    assert d.state==DecisionState.DEFER

def test_evidence_contradiction_is_explicit():
    a=EvidenceAdjudicator().adjudicate([EvidenceItem('e1','s','growth=10'),EvidenceItem('e2','s','growth=5')])
    assert len(a['contradictions'])==1 and 'CONTRADICTION_REVIEW' in a['review']

def test_causal_counterfactuals():
    c=CausalEngine()
    assert c.counterfactuals(growth_shock=-.2,margin_shock=-.1,multiple_shock=-.15,catalyst_removed=True)==('GROWTH_SHOCK:-0.2000','MARGIN_SHOCK:-0.1000','MULTIPLE_SHOCK:-0.1500','CATALYST_REMOVED')

def test_portfolio_risk_is_independent():
    r=PortfolioRiskGate().evaluate(exposure=.8,sector_overlap=.2)
    assert r.blocked and 'EXPOSURE' in r.risks

def test_replay_manifest_hash_and_guard():
    ih=sha256(b'inputs').hexdigest()
    m=RunManifest(1,'run1','cfg1','prompt1',ih,'2026-09-26T10:00:00Z','RESEARCH')
    h=ReplayGuard().validate(m)
    assert len(h)==64 and h==m.digest()
