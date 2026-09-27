import pytest
from orion.data.coverage_contract import DataCoverageContract, DatasetCoverage, CoverageState
from orion.data.provider_capabilities import ProviderCapability, ProviderCapabilityRegistry, CapabilityState
from orion.research.evidence_graph import EvidenceGraphBuilder, EvidenceNode
from orion.data.world_snapshot import WorldSnapshot
from orion.intelligence.decision_world import DecisionWorldBuilder
from orion.decision.trade_ensemble import SpecialistOutput, TradeIntelligenceEnsemble

def test_coverage_contract_fails_closed_for_critical_missing_domain():
    c=DataCoverageContract().assess(['ohlcv','financials'], {'ohlcv':DatasetCoverage('ohlcv',CoverageState.READY,10)}, critical=['financials'])
    assert not c.usable
    assert 'financials:MISSING' in c.blockers

def test_provider_capability_registry_is_read_only_and_traceable():
    r=ProviderCapabilityRegistry(); r.register(ProviderCapability('zerodha','ohlcv',CapabilityState.NOT_CONFIGURED))
    m=r.matrix(); assert m.state('zerodha','ohlcv')==CapabilityState.NOT_CONFIGURED
    assert m.lineage_hash
    with pytest.raises(ValueError): r.register(ProviderCapability('bad','orders',CapabilityState.READY,read_only=False))

def test_evidence_graph_blocks_future_and_conflicting_claims():
    g=EvidenceGraphBuilder().build([
      EvidenceNode('a','c1','SUPPORTED','2026-01-01T00:00:00Z','s1','h1'),
      EvidenceNode('b','c1','SUPPORTED','2026-01-02T00:00:00Z','s2','h2'),
      EvidenceNode('f','c2','SUPPORTED','2026-02-01T00:00:00Z','s3','h3')], decision_time='2026-01-10T00:00:00Z')
    assert not g.usable
    assert any('CONFLICT' in e[2] for e in g.edges)
    assert 'f:FUTURE' in g.blockers

def test_decision_world_is_single_readiness_boundary():
    s=WorldSnapshot.build('ABC','2026-01-10T00:00:00Z',observations={'ohlcv':[{'available_time':'2026-01-09T00:00:00Z','event_time':'2026-01-09T00:00:00Z','payload_hash':'x'*64}]})
    c=DataCoverageContract().assess(['ohlcv'], {'ohlcv':DatasetCoverage('ohlcv',CoverageState.READY,1)}, critical=['ohlcv'])
    e=EvidenceGraphBuilder().build([EvidenceNode('e','c','SUPPORTED','2026-01-09T00:00:00Z','s','h')],decision_time='2026-01-10T00:00:00Z')
    w=DecisionWorldBuilder().build(s,c,e); assert w.readiness.status=='READY'; assert w.lineage_hash

def test_ensemble_requires_empirical_eligibility_for_probability():
    e=TradeIntelligenceEnsemble(min_specialists=2).combine([
      SpecialistOutput('fundamental',.8,100,'f',True),
      SpecialistOutput('technical',.7,100,'t',True)], required_specialists=['fundamental','technical'])
    assert e.probability is None and e.status=='REQUIRED_SPECIALIST_COVERAGE_MISSING'
    e=TradeIntelligenceEnsemble(min_specialists=2).combine([
      SpecialistOutput('fundamental',.8,100,'f',True,.18,.04,3,.95),
      SpecialistOutput('technical',.7,100,'t',True,.19,.05,3,.95)], required_specialists=['fundamental','technical'])
    assert e.status=='READY' and e.probability is not None
