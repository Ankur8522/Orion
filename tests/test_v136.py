from datetime import datetime,timezone,timedelta
from decimal import Decimal
from orion.research.sector import SectorMetricEngine
from orion.research.forensics import ForensicEngine
from orion.research.market_signals import analyze
from orion.research.priority import PriorityEngine

def test_sector_and_forensics():
    m=SectorMetricEngine().run('X','it',{'revenue':100,'pat':10,'ebitda':20,'cfo':5,'tcv':120,'utilisation':80,'attrition':12})
    assert m.metrics['net_margin']==Decimal('0.1'); assert any(x.code=='LOW_CFO_PAT' for x in ForensicEngine().inspect(m.metrics))
def test_market_breakout():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[{'event_time':(t+timedelta(days=i)).isoformat().replace('+00:00','Z'),'close':100+i,'volume':1000} for i in range(22)]
    rows[-1]['volume']=2000
    s=analyze('X',rows); assert s.breakout and s.volume_state=='EXPANSION'
def test_priority_market():
    p=PriorityEngine().score('X',market_signal=1,thesis_change=.5); assert p.score>0 and 'MARKET_SIGNAL' in p.reasons
