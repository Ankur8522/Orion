from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from hashlib import sha256
import json, math
from statistics import mean
from typing import Sequence

@dataclass(frozen=True)
class ForecastDistribution:
    horizon_days: int
    observations: int
    mean_return: float
    median_return: float
    p_positive: float
    p10: float
    p25: float
    p75: float
    p90: float
    downside_p10: float
    uncertainty: float
    status: str
    lineage_hash: str

class EmpiricalForecastDistribution:
    """Builds return distributions only from verified historical outcomes."""

    def build_from_ledger(self, forecasts: Iterable[object], outcomes: Iterable[object], *, horizon_days: int) -> ForecastDistribution:
        """Build a return distribution only from resolved, explicitly observed outcomes."""
        outcome_by_id={getattr(o, 'forecast_id', None): o for o in outcomes}
        returns=[]
        for f in forecasts:
            if getattr(f, 'horizon_days', None) not in (None, horizon_days):
                continue
            o=outcome_by_id.get(getattr(f, 'forecast_id', None))
            value=getattr(o, 'return_pct', None) if o is not None else None
            if value is not None:
                returns.append(float(value))
        return self.build(returns, horizon_days=horizon_days)

    def build(self, returns: Sequence[float], *, horizon_days: int) -> ForecastDistribution:
        if horizon_days <= 0: raise ValueError('INVALID_HORIZON')
        vals=[]
        for x in returns:
            x=float(x)
            if not math.isfinite(x): raise ValueError('INVALID_RETURN')
            vals.append(x)
        vals.sort(); n=len(vals)
        if n < 8:
            return ForecastDistribution(horizon_days,n,0,0,0,0,0,0,0,0,1.0,'INSUFFICIENT_EVIDENCE',self._hash({'horizon':horizon_days,'n':n}))
        def q(p):
            pos=(n-1)*p; lo=int(pos); hi=min(n-1,lo+1); frac=pos-lo
            return vals[lo]*(1-frac)+vals[hi]*frac
        positive=sum(v>0 for v in vals)/n
        spread=q(.75)-q(.25)
        uncertainty=min(1.0, max(0.0, spread/(abs(q(.9)-q(.1))+1e-12)))
        payload={'horizon':horizon_days,'returns':vals}
        return ForecastDistribution(horizon_days,n,mean(vals),q(.5),positive,q(.1),q(.25),q(.75),q(.9),q(.1),uncertainty,'READY',self._hash(payload))
    @staticmethod
    def _hash(obj): return sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
