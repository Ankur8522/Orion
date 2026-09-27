from decimal import Decimal
from orion.research.sector import SectorMetricEngine
from orion.research.forensics import ForensicEngine

def test_generic_metrics():
    s=SectorMetricEngine().run('X','generic',{'revenue':100,'pat':10,'ebitda':20,'cfo':8,'debt':40,'cash':10})
    assert s.metrics['net_margin']==Decimal('0.1')
    assert s.metrics['cfo_pat']==Decimal('0.8')
    assert s.metrics['debt_ebitda']==Decimal('2')

def test_sector_missing_flags():
    s=SectorMetricEngine().run('X','it',{'revenue':100})
    assert 'MISSING_TCV' in s.warnings and 'MISSING_EBITDA' in s.warnings

def test_forensic_flags():
    f=ForensicEngine().inspect({'cfo_pat':'0.5','receivables_to_revenue':'0.3','debt_ebitda':'5'})
    assert {x.code for x in f}=={'LOW_CFO_PAT','RECEIVABLE_INTENSITY','HIGH_LEVERAGE'}
