from decimal import Decimal
from orion.company.model import CompanyPeriod, build_company_model
from orion.company.valuation import derive_valuation
from orion.company.snapshot import build_research_snapshot

def test_company_model_history_and_derived_metrics():
    m=build_company_model('X',[
        CompanyPeriod('2025-03-31',revenue=100,ebitda=20,pat=10,cfo=12,capex=5,debt=40,cash=10,equity=50,invested_capital=80),
        CompanyPeriod('2026-03-31',revenue=120,ebitda=27,pat=13,cfo=11,capex=6,debt=36,cash=12,equity=60,invested_capital=90),
    ])
    x=m.derived['2026-03-31']
    assert x['revenue_growth']==Decimal('0.2')
    assert x['ebitda_margin']==Decimal('0.225')
    assert x['fcf']==Decimal('5')
    assert x['cfo_pat']==Decimal('0.8461538461538461538461538462')
    assert x['net_debt']==Decimal('24')

def test_valuation_bridge():
    v=derive_valuation('X',price=100,shares=10,pat=20,equity=150,ebitda=40,fcf=15,debt=50,cash=10)
    assert v.market_cap==Decimal('1000')
    assert v.pe==Decimal('50')
    assert v.pb==Decimal('6.666666666666666666666666667')
    assert v.ev_ebitda==Decimal('26')
    assert v.fcf_yield==Decimal('0.015')

def test_snapshot_flags_are_transparent():
    m=build_company_model('X',[CompanyPeriod('2026-03-31',revenue=100,pat=10,cfo=5,capex=20,debt=30,cash=0,ebitda=10,equity=50)])
    s=build_research_snapshot(m)
    assert 'CASH_CONVERSION_WEAK' in s.quality_flags
    assert 'FCF_NEGATIVE' in s.quality_flags
    assert 'LEVERAGE_ELEVATED' not in s.quality_flags
