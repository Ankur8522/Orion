from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
from typing import Iterable
from .feedback import ForecastRecord, OutcomeRecord

@dataclass(frozen=True)
class SegmentDiagnostic:
    key: str
    count: int
    hit_rate: float
    brier: float
    mean_probability: float
    observed_rate: float

@dataclass(frozen=True)
class CalibrationDrift:
    early_count: int
    late_count: int
    early_gap: float | None
    late_gap: float | None
    drift: float | None
    status: str

@dataclass(frozen=True)
class AdvancedDiagnostics:
    by_model: tuple[SegmentDiagnostic,...]
    by_sector: tuple[SegmentDiagnostic,...]
    by_regime: tuple[SegmentDiagnostic,...]
    by_horizon: tuple[SegmentDiagnostic,...]
    calibration_drift: CalibrationDrift
    minimum_sample_flags: tuple[str,...]

def _bucket(f: ForecastRecord):
    days=(datetime.fromisoformat(f.horizon_end.replace('Z','+00:00'))-datetime.fromisoformat(f.decision_time.replace('Z','+00:00'))).total_seconds()/86400
    return 'SHORT_0_7D' if days<=7 else ('MEDIUM_8_30D' if days<=30 else 'LONG_31D_PLUS')

def _segments(rows, keyfn):
    groups=defaultdict(list)
    for f,o in rows:
        groups[keyfn(f)].append((f,o))
    out=[]
    for k,items in sorted(groups.items()):
        n=len(items); hit=sum((f.probability>=.5)==bool(o.occurred) for f,o in items)/n
        b=sum((f.probability-int(o.occurred))**2 for f,o in items)/n
        mp=sum(f.probability for f,o in items)/n; ar=sum(int(o.occurred) for f,o in items)/n
        out.append(SegmentDiagnostic(str(k),n,round(hit,8),round(b,8),round(mp,8),round(ar,8)))
    return tuple(out)

class AdvancedDiagnosticsEngine:
    def analyze(self, forecasts: Iterable[ForecastRecord], outcomes: Iterable[OutcomeRecord], *, min_sample: int=10) -> AdvancedDiagnostics:
        fs={f.forecast_id:f for f in forecasts}; rows=[(fs[o.forecast_id],o) for o in outcomes if o.forecast_id in fs]
        model=_segments(rows,lambda f:f.model_id); sector=_segments(rows,lambda f:f.sector or 'UNSPECIFIED'); regime=_segments(rows,lambda f:f.regime or 'UNSPECIFIED'); horizon=_segments(rows,_bucket)
        ordered=sorted(rows,key=lambda x:x[0].decision_time); mid=len(ordered)//2
        def gap(xs):
            if not xs:return None
            return abs(sum(f.probability for f,o in xs)/len(xs)-sum(int(o.occurred) for f,o in xs)/len(xs))
        early=ordered[:mid]; late=ordered[mid:]
        eg,lg=gap(early),gap(late); drift=None if eg is None or lg is None else abs(lg-eg)
        flags=tuple(sorted({f'LOW_SAMPLE:{x.key}' for x in model+sector+regime+horizon if x.count<min_sample}))
        status='INSUFFICIENT_SAMPLE' if len(rows)<min_sample*2 else ('DRIFT_DETECTED' if drift is not None and drift>=.10 else 'STABLE_OR_UNDETERMINED')
        return AdvancedDiagnostics(model,sector,regime,horizon,CalibrationDrift(len(early),len(late),eg,lg,drift,status),flags)
