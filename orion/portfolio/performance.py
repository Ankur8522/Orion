from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
import math
from typing import Iterable, Sequence
import hashlib, json

@dataclass(frozen=True)
class PerformancePoint:
    timestamp: str
    nav: float
    return_pct: float
    drawdown_pct: float

@dataclass(frozen=True)
class PerformanceSummary:
    start_nav: float
    end_nav: float
    total_return_pct: float
    max_drawdown_pct: float
    observations: int
    volatility_pct: float | None
    sharpe: float | None
    sortino: float | None
    lineage_hash: str
    time_weighted_return_pct: float | None = None
    money_weighted_return_pct: float | None = None

class PortfolioPerformanceEngine:
    """Transparent performance analytics over supplied NAV observations only."""
    def series(self, rows: Iterable[tuple[str,float]]) -> tuple[PerformancePoint,...]:
        clean=sorted(((str(t),float(n)) for t,n in rows), key=lambda x:x[0])
        if any(n <= 0 for _,n in clean): raise ValueError('INVALID_NAV')
        if not clean: return ()
        start=clean[0][1]; peak=start; out=[]; prev=start
        for t,nav in clean:
            ret=0.0 if prev==0 else (nav/prev-1)*100
            peak=max(peak,nav); dd=(nav/peak-1)*100
            out.append(PerformancePoint(t,nav,ret,dd)); prev=nav
        return tuple(out)
    def summarize(self, rows: Iterable[tuple[str,float]], *, periods_per_year: float=252.0, risk_free_pct: float=0.0, cash_flows: Sequence[tuple[str,float]] = ()) -> PerformanceSummary:
        if periods_per_year<=0: raise ValueError('INVALID_PERIODS_PER_YEAR')
        series=self.series(rows)
        if not series: return PerformanceSummary(0,0,0,0,0,None,None,None,'',None,None)
        returns=[p.return_pct/100 for p in series[1:]]
        total=(series[-1].nav/series[0].nav-1)*100
        dd=min(p.drawdown_pct for p in series)
        vol=None; sharpe=None; sortino=None
        if returns:
            mean=sum(returns)/len(returns); var=sum((r-mean)**2 for r in returns)/len(returns)
            vol=(var**0.5)*(periods_per_year**0.5)*100
            excess=mean-(risk_free_pct/100)/periods_per_year
            if vol>0: sharpe=excess*(periods_per_year**0.5)/(vol/100)
            downside=[min(0.0,r) for r in returns]
            downside_var=sum(x*x for x in downside)/len(downside) if downside else 0.0
            downside_dev=(downside_var**0.5)*(periods_per_year**0.5)
            if downside_dev>0: sortino=excess*(periods_per_year**0.5)/downside_dev
        import hashlib, json
        twr = None
        mwr = None
        if cash_flows:
            cf = sorted(((str(t), float(v)) for t,v in cash_flows), key=lambda x:x[0])
            nav_by_time = {p.timestamp:p.nav for p in series}
            factors=[]; prev_nav=series[0].nav; prev_t=series[0].timestamp
            for t, amount in cf:
                if t in nav_by_time and prev_nav > 0:
                    factors.append((nav_by_time[t] - amount) / prev_nav)
                    prev_nav = nav_by_time[t]
                    prev_t = t
            if factors and all(x > 0 for x in factors): twr=(math.prod(factors)-1)*100
            # Money-weighted return: periodic IRR over supplied ordered NAV/cashflow points.
            points=[(series[0].timestamp, -series[0].nav)]
            for pnt in series[1:]: points.append((pnt.timestamp, -0.0))
            for t, amount in cf: points.append((t, float(amount)))
            points.append((series[-1].timestamp, float(series[-1].nav)))
            points=sorted(points,key=lambda x:x[0])
            def npv(rate):
                base=points[0][0]; total_npv=0.0
                try:
                    import datetime
                    b=datetime.datetime.fromisoformat(base.replace('Z','+00:00'))
                    for t,v in points:
                        d=datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
                        years=max(0.0,(d-b).total_seconds())/(365.25*24*3600)
                        total_npv += v / ((1+rate)**years)
                except Exception:
                    return float('nan')
                return total_npv
            lo,hi=-0.9999,10.0; flo,fhi=npv(lo),npv(hi)
            if math.isfinite(flo) and math.isfinite(fhi) and flo*fhi <= 0:
                for _ in range(120):
                    mid=(lo+hi)/2; fm=npv(mid)
                    if abs(fm) < 1e-10: break
                    if flo*fm <= 0: hi=mid; fhi=fm
                    else: lo=mid; flo=fm
                mwr=mid*100
        payload={'series':[p.__dict__ for p in series],'cash_flows':list(cash_flows),'twr':twr,'mwr':mwr}
        lineage=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return PerformanceSummary(series[0].nav,series[-1].nav,round(total,8),round(dd,8),len(series),None if vol is None else round(vol,8),None if sharpe is None else round(sharpe,8),None if sortino is None else round(sortino,8),lineage,None if twr is None else round(twr,8),None if mwr is None else round(mwr,8))
