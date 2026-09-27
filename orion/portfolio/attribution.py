from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

@dataclass(frozen=True)
class PositionAttribution:
    security_id: str
    weight: float
    return_pct: float
    contribution_pct: float

@dataclass(frozen=True)
class PortfolioAttribution:
    total_return_pct: float
    positive_contributors: tuple[str,...]
    negative_contributors: tuple[str,...]
    positions: tuple[PositionAttribution,...]
    residual_pct: float
    lineage_hash: str

class PortfolioAttributionEngine:
    """Simple transparent contribution engine; supplied returns only, no invented prices."""
    def attribute(self, rows: Iterable[tuple[str,float,float]], *, portfolio_return: float|None=None) -> PortfolioAttribution:
        items=[]
        for sid,w,r in rows:
            if not sid or w < 0: raise ValueError('INVALID_ATTRIBUTION_ROW')
            items.append(PositionAttribution(sid,float(w),float(r),float(w)*float(r)))
        total=sum(x.contribution_pct for x in items)
        target=total if portfolio_return is None else float(portfolio_return)
        residual=target-total
        pos=tuple(x.security_id for x in sorted(items,key=lambda x:x.contribution_pct,reverse=True) if x.contribution_pct>0)
        neg=tuple(x.security_id for x in sorted(items,key=lambda x:x.contribution_pct) if x.contribution_pct<0)
        payload={'rows':[x.__dict__ for x in items],'target':target}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return PortfolioAttribution(round(target,12),pos,neg,tuple(items),round(residual,12),lineage)
