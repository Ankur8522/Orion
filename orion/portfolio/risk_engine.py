from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class RiskAssessment:
    volatility: float
    var95: float
    expected_shortfall95: float
    max_drawdown: float
    concentration_hhi: float
    sector_concentration: float
    liquidity_score: float
    risk_score: float
    actions: tuple[str, ...]
    lineage_hash: str

class PortfolioRiskEngine:
    """Deterministic portfolio risk analytics over supplied observations only."""
    def assess(self, returns: Sequence[float], weights: Mapping[str,float], sectors: Mapping[str,str] | None=None,
               liquidity: Mapping[str,float] | None=None) -> RiskAssessment:
        rs=[float(x) for x in returns]
        if any(not math.isfinite(x) or x <= -1 for x in rs): raise ValueError('INVALID_RETURN')
        ws={str(k):float(v) for k,v in weights.items()}
        if not ws or any(v<0 for v in ws.values()) or sum(ws.values())<=0: raise ValueError('INVALID_WEIGHTS')
        total=sum(ws.values()); norm={k:v/total for k,v in ws.items()}
        hhi=sum(v*v for v in norm.values())
        mean=sum(rs)/len(rs) if rs else 0.0
        vol=(sum((x-mean)**2 for x in rs)/len(rs))**0.5*(252**0.5) if rs else 0.0
        sorted_r=sorted(rs)
        idx=max(0,min(len(sorted_r)-1,math.ceil(0.05*len(sorted_r))-1)) if sorted_r else 0
        var95=-(sorted_r[idx] if sorted_r else 0.0)
        tail=[x for x in rs if x <= -var95] if rs else []
        es95=-(sum(tail)/len(tail)) if tail else var95
        nav=1.0; peak=1.0; mdd=0.0
        for r in rs:
            nav*=1+r; peak=max(peak,nav); mdd=min(mdd,nav/peak-1)
        sector_hhi=0.0
        if sectors:
            sw={}
            for sid,w in norm.items(): sw[sectors.get(sid,'UNKNOWN')]=sw.get(sectors.get(sid,'UNKNOWN'),0)+w
            sector_hhi=sum(v*v for v in sw.values())
        if liquidity is not None and any(not math.isfinite(float(v)) or not 0 <= float(v) <= 1 for v in liquidity.values()): raise ValueError('INVALID_LIQUIDITY')
        liq=sum(norm.get(k,0)*float(v) for k,v in (liquidity or {}).items()) if liquidity else 0.0
        risk_score=max(0,min(1,0.35*min(vol/0.5,1)+0.25*min(abs(mdd)/0.3,1)+0.20*min(hhi/0.3,1)+0.20*min(sector_hhi/0.4,1)))
        actions=[]
        if hhi>0.25: actions.append('REDUCE_POSITION_CONCENTRATION')
        if sector_hhi>0.30: actions.append('REVIEW_SECTOR_CONCENTRATION')
        if abs(mdd)>0.15: actions.append('DRAW_DOWN_BUDGET_REVIEW')
        if var95>0.04: actions.append('TAIL_RISK_REVIEW')
        if not actions: actions.append('MONITOR_RISK_STATE')
        payload={'returns':rs,'weights':norm,'sectors':sectors or {},'liquidity':liquidity or {}}
        h=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return RiskAssessment(round(vol,8),round(var95,8),round(es95,8),round(mdd,8),round(hhi,8),round(sector_hhi,8),round(liq,8),round(risk_score,8),tuple(actions),h)
