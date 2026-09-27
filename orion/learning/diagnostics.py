from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable
from .feedback import ForecastRecord, OutcomeRecord

@dataclass(frozen=True)
class LearningDiagnostics:
    resolved: int
    hit_rate: float | None
    false_positive_rate: float | None
    false_negative_rate: float | None
    overconfidence_gap: float | None
    brier: float | None
    log_loss: float | None
    calibration_error: float | None
    by_model: tuple[tuple[str,int,float], ...]
    by_sector: tuple[tuple[str,int,float], ...]
    by_regime: tuple[tuple[str,int,float], ...]
    by_horizon: tuple[tuple[str,int,float], ...]
    recurring_failure_flags: tuple[str, ...]

class LearningDiagnosticsEngine:
    def analyze(self, forecasts: Iterable[ForecastRecord], outcomes: Iterable[OutcomeRecord]) -> LearningDiagnostics:
        fs={f.forecast_id:f for f in forecasts}; rows=[]
        for o in outcomes:
            f=fs.get(o.forecast_id)
            if f: rows.append((f,float(f.probability),int(o.occurred)))
        if not rows: return LearningDiagnostics(0,None,None,None,None,None,None,None,(),(),(),(),('INSUFFICIENT_OUTCOMES',))
        hits=sum((p>=0.5)==bool(y) for _,p,y in rows)
        fp=sum(p>=0.5 and y==0 for _,p,y in rows); neg=sum(p<0.5 and y==1 for _,p,y in rows)
        actual=sum(y for _,_,y in rows)/len(rows); pred=sum(p for _,p,_ in rows)/len(rows)
        by=defaultdict(list); by_sector=defaultdict(list); by_regime=defaultdict(list); by_horizon=defaultdict(list)
        for f,p,y in rows:
            item=((p>=0.5)==bool(y),abs(p-y))
            by[f.model_id].append(item)
            if f.sector: by_sector[f.sector].append(item)
            if f.regime: by_regime[f.regime].append(item)
            from datetime import datetime
            days=(datetime.fromisoformat(f.horizon_end.replace('Z','+00:00'))-datetime.fromisoformat(f.decision_time.replace('Z','+00:00'))).total_seconds()/86400
            bucket='SHORT_0_7D' if days <= 7 else ('MEDIUM_8_30D' if days <= 30 else 'LONG_31D_PLUS')
            by_horizon[bucket].append(item)
        brier=sum((p-y)**2 for _,p,y in rows)/len(rows)
        import math
        log_loss=sum(-(y*math.log(min(max(p,1e-15),1-1e-15))+(1-y)*math.log(min(max(1-p,1e-15),1-1e-15))) for _,p,y in rows)/len(rows)
        # Weighted absolute probability gap is a transparent calibration proxy.
        calibration_error=abs(pred-actual)
        model_rows=tuple(sorted((m,len(v),round(sum(x[0] for x in v)/len(v),6)) for m,v in by.items()))
        sector_rows=tuple(sorted((m,len(v),round(sum(x[0] for x in v)/len(v),6)) for m,v in by_sector.items()))
        regime_rows=tuple(sorted((m,len(v),round(sum(x[0] for x in v)/len(v),6)) for m,v in by_regime.items()))
        horizon_rows=tuple(sorted((m,len(v),round(sum(x[0] for x in v)/len(v),6)) for m,v in by_horizon.items()))
        flags=[]
        if fp/len(rows)>0.25: flags.append('HIGH_FALSE_POSITIVE_RATE')
        if neg/len(rows)>0.25: flags.append('HIGH_FALSE_NEGATIVE_RATE')
        if abs(pred-actual)>0.15: flags.append('SYSTEMATIC_CALIBRATION_BIAS')
        return LearningDiagnostics(len(rows),round(hits/len(rows),6),round(fp/len(rows),6),round(neg/len(rows),6),round(abs(pred-actual),6),round(brier,8),round(log_loss,8),round(calibration_error,8),model_rows,sector_rows,regime_rows,horizon_rows,tuple(flags))
