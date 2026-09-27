from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class MarketSignal:
    security_id: str
    trend: str
    momentum: str
    volume_state: str
    breakout: bool
    score: Decimal
    warnings: tuple[str, ...]

def _d(v): return Decimal(str(v))

def analyze(security_id: str, rows) -> MarketSignal:
    """PIT-safe technical snapshot. Rows must already be constrained to decision time."""
    xs=sorted(rows,key=lambda r:r.get('event_time',''))
    warnings=[]
    if not xs: return MarketSignal(security_id,'UNKNOWN','UNKNOWN','UNKNOWN',False,Decimal('0'),('NO_PRICE_DATA',))
    closes=[_d(r['close']) for r in xs if r.get('close') is not None]
    vols=[_d(r['volume']) for r in xs if r.get('volume') is not None]
    if len(closes)<2: warnings.append('INSUFFICIENT_PRICE_HISTORY')
    last=closes[-1] if closes else Decimal('0')
    prev=closes[-2] if len(closes)>1 else last
    ret=(last/prev-1) if prev else Decimal('0')
    trend='UP' if len(closes)>=2 and last>prev else ('DOWN' if len(closes)>=2 and last<prev else 'FLAT')
    momentum='POSITIVE' if ret>Decimal('0.02') else ('NEGATIVE' if ret<Decimal('-0.02') else 'NEUTRAL')
    volume_state='NORMAL'
    if vols and len(vols)>=6:
        avg=sum(vols[:-1],Decimal('0'))/Decimal(len(vols[:-1]))
        if avg>0:
            ratio=vols[-1]/avg
            volume_state='EXPANSION' if ratio>=Decimal('1.5') else ('LOW' if ratio<=Decimal('0.6') else 'NORMAL')
    breakout=False
    if len(closes)>=21:
        prior_max=max(closes[-21:-1]); breakout=last>prior_max
    score=(Decimal('35') if trend=='UP' else Decimal('0'))+(Decimal('30') if momentum=='POSITIVE' else Decimal('0'))+(Decimal('20') if volume_state=='EXPANSION' else Decimal('0'))+(Decimal('15') if breakout else Decimal('0'))
    return MarketSignal(security_id,trend,momentum,volume_state,breakout,score,tuple(warnings))
