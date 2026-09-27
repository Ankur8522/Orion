from decimal import Decimal
from orion.data.corporate_actions import CorporateActionLedger
from orion.research.scenarios import ResearchScenarioEngine
from orion.portfolio.correlation import CorrelationEngine
from orion.learning.outcome_resolver import ForecastOutcomeResolver, ObservableOutcome
from orion.learning.feedback import ForecastLedger

def test_corporate_action_is_pit_safe_and_adjustment_is_explicit():
    a=CorporateActionLedger().normalize({'security_id':'X','action_id':'a1','action_type':'SPLIT','effective_time':'2026-01-05T00:00:00Z','available_time':'2026-01-05T12:00:00Z','ratio':'2','source_id':'src','content_hash':'a'*64})
    l=CorporateActionLedger(); assert l.adjustment_factor([a],'2026-01-03T00:00:00Z')==Decimal('1'); assert l.adjustment_factor([a],'2026-01-06T00:00:00Z')==Decimal('2')

def test_corporate_action_rejects_future_available_data():
    a=CorporateActionLedger().normalize({'security_id':'X','action_id':'a1','action_type':'DIVIDEND','effective_time':'2026-01-05T00:00:00Z','available_time':'2026-01-06T00:00:00Z','source_id':'src','content_hash':'b'*64})
    assert CorporateActionLedger().as_of([a],'2026-01-05T12:00:00Z')==()

def test_scenario_engine_requires_evidence_and_counter_thesis():
    r=ResearchScenarioEngine().build(catalysts=['growth'],headwinds=['valuation'],evidence_ids=['e1'],counter_thesis=['demand'],causal_chains=[('demand','revenue','cashflow')])
    assert r.research_ready and len(r.lineage_hash)==64

def test_correlation_engine_is_deterministic():
    r=CorrelationEngine().calculate({'A':[1,2,3,4],'B':[2,4,6,8],'C':[4,3,2,1]})
    assert r.matrix[0][1] > .99 and r.matrix[0][2] < -.99
    assert len(r.lineage_hash)==64 and r.high_correlation_pairs

def test_outcome_resolver_rejects_future_and_pre_horizon_observation():
    f=ForecastLedger.make_forecast(security_id='X',event_key='K',decision_time='2026-01-01T00:00:00Z',horizon_end='2026-01-02T00:00:00Z',probability=.6,evidence_ids=('e',),thesis_fingerprint='t')
    l=ForecastLedger(); l.issue(f)
    o=ObservableOutcome('K','X',True,'2026-01-01T12:00:00Z','s','a'*64)
    r=ForecastOutcomeResolver().resolve(l,[o],evaluation_time='2026-01-03T00:00:00Z')
    assert r.resolved==0 and r.skipped==1
