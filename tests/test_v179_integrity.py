from orion.data.reconcile import Reconciler
from orion.data.providers import ProviderObservation, hash_payload
from orion.evidence.ledger import EvidenceRecord
from orion.evidence.adjudication import EvidenceAdjudicator
from orion.financials.reconcile_facts import FinancialFactReconciler
from orion.financials.statement import FinancialFact
from orion.ops.replay import write_replay, load_replay
from decimal import Decimal

def obs(provider, payload, priority):
    return ProviderObservation(provider,'ohlcv','ABC','2026-09-27T00:00:00Z','2026-09-27T01:00:00Z',payload,False,source_priority=priority)

def test_reconciler_uses_deterministic_source_precedence_when_payloads_agree():
    r=Reconciler().reconcile([obs('z','a'*64,20),obs('a','a'*64,10)])
    assert r.status=='AGREED' and r.selected_provider=='a'

def test_reconciler_filters_future_observation():
    r=Reconciler().reconcile([obs('a','a'*64,1), ProviderObservation('b','ohlcv','ABC','2026-09-27T00:00:00Z','2026-09-28T00:00:00Z','a'*64,False,source_priority=2)], as_of='2026-09-27T12:00:00Z')
    assert len(r.observations)==1 and r.selected_provider=='a'

def fact(source,value):
    return FinancialFact('ABC','pat','2026-06-30',Decimal(value),'INR','INR',source,'2026-09-27T00:00:00Z','a'*64)

def test_financial_reconciliation_source_precedence_is_configurable():
    r=FinancialFactReconciler(source_precedence=('company-ir','nse')).reconcile([fact('nse','100'),fact('company-ir','100.1')])
    assert r.status=='AGREED' and r.selected.source_id=='company-ir'

def ev(eid,value):
    return EvidenceRecord(eid,'ABC','src',eid,'p1','PAT',value,.8,'2026-09-27T00:00:00Z','a'*64)

def test_evidence_adjudication_detects_contradiction():
    r=EvidenceAdjudicator().adjudicate([ev('e1',100),ev('e2',120)])
    assert r[0].status=='CONTRADICTED' and len(r[0].lineage_hash)==64

def test_replay_v2_binds_input_hash(tmp_path):
    p=tmp_path/'r.json'; write_replay(p, {'decision_time':'2026-09-27T00:00:00Z','inputs':{'x':1}})
    assert load_replay(p)['inputs']=={'x':1}
