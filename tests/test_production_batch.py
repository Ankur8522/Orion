from orion.company.model import CompanyPeriod, build_company_model
from orion.research.production_batch import ProductionResearchBatch, report_json

def m(sid):
    return build_company_model(sid,[
        CompanyPeriod('2025-03-31',revenue=100,ebitda=20,pat=10,cfo=11,capex=4,debt=10,cash=3,receivables=15,equity=50,invested_capital=60),
        CompanyPeriod('2026-03-31',revenue=120,ebitda=27,pat=14,cfo=15,capex=5,debt=12,cash=4,receivables=16,equity=58,invested_capital=65)])

def test_500_manifest_is_deterministic_and_blocks_missing_data():
    ids=[f'S{i:04d}' for i in range(500)]
    r=ProductionResearchBatch().run(ids,as_of='2026-09-26')
    assert r.total==500 and r.blocked==500 and r.failed==0
    assert all(x.reason=='NO_COMPANY_MODEL' for x in r.results)

def test_batch_completes_bound_company_and_blocks_missing_evidence():
    contexts={'AAA':{'model':m('AAA'),'evidence_ids':['e1'],'evidence_states':['EVIDENCE_SUPPORTED']},
              'BBB':{'model':m('BBB')}}
    r=ProductionResearchBatch().run(['AAA','BBB'],as_of='2026-09-26',contexts=contexts)
    assert r.complete==1 and r.blocked==1
    assert r.results[0].dossier is not None
    assert r.results[1].reason=='NO_EVIDENCE_LINKED'

def test_report_is_json_serializable():
    r=ProductionResearchBatch().run(['AAA'],as_of='2026-09-26')
    payload=report_json(r)
    assert 'AAA' in payload and 'NO_COMPANY_MODEL' in payload
