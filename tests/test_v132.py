from decimal import Decimal
import pytest
from orion.analytics.calculations import derive
from orion.data.freshness import assess
from orion.portfolio.impact import assess as impact

def test_derived_metric_has_traceable_lineage():
    r=derive('S1','margin','ebitda/revenue',{'ebitda':Decimal('20'),'revenue':Decimal('100')},'ratio')
    assert r.value==Decimal('0.200000') and len(r.lineage_hash)==64 and r.source_ids==('ebitda','revenue')

def test_derived_metric_rejects_empty_inputs():
    with pytest.raises(ValueError): derive('S1','x','a/b',{})

def test_freshness():
    r=assess('2026-01-01T00:00:00Z','2026-01-02T00:00:00Z','nse',24,48); assert r.status=='FRESH'
    with pytest.raises(ValueError): assess('2026-01-03T00:00:00Z','2026-01-02T00:00:00Z','nse')

def test_portfolio_impact():
    assert impact('S1',.2,'RED',10).action=='REVIEW_NOW'
    assert impact('S1',.2,'GREEN',80).action=='RESEARCH_PRIORITY'
