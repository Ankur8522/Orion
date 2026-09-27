from decimal import Decimal
from orion.financials.extraction import FinancialFactExtractor
from orion.financials.reconcile_facts import FinancialFactReconciler
from orion.financials.statement import FinancialFact

def eid(locator,claim,text): return 'a'*64

def test_text_extraction_is_deterministic_and_typed():
    x=FinancialFactExtractor().extract_text('Revenue: ₹1,234.50 PAT 200.5 CFO: 180',security_id='TCS',period_end='2026-06-30',source_id='nse',available_time='2026-09-26T10:00:00Z',evidence_id_factory=eid)
    assert [(a.fact.metric,a.fact.value) for a in x]==[('revenue',Decimal('1234.50')),('pat',Decimal('200.5')),('cfo',Decimal('180'))]

def test_future_fact_is_blocked():
    f=FinancialFact('TCS','pat','2026-06-30',Decimal('10'),'INR','INR','nse','2026-09-27T00:00:00Z','a'*64)
    try: f.validate('2026-09-26T00:00:00Z'); assert False
    except ValueError as e: assert str(e)=='FUTURE_FINANCIAL_FACT'

def make(v,source): return FinancialFact('TCS','pat','2026-06-30',Decimal(v),'INR','INR',source,'2026-09-26T00:00:00Z','a'*64)

def test_fact_reconciliation_agrees_with_small_spread():
    r=FinancialFactReconciler().reconcile([make('100','nse'),make('100.5','company-ir')])
    assert r.status=='AGREED' and r.selected is not None

def test_fact_reconciliation_routes_material_conflict_to_review():
    r=FinancialFactReconciler().reconcile([make('100','nse'),make('130','company-ir')])
    assert r.status=='REVIEW' and r.selected is None and r.relative_spread>Decimal('.01')

def test_mixed_fact_keys_rejected():
    a=make('100','nse'); b=FinancialFact('TCS','revenue','2026-06-30',Decimal('100'),'INR','INR','nse','2026-09-26T00:00:00Z','a'*64)
    try: FinancialFactReconciler().reconcile([a,b]); assert False
    except ValueError as e: assert str(e)=='MIXED_FINANCIAL_FACT_KEYS'
