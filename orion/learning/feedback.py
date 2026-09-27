from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json, math
from typing import Iterable, Sequence

def _utc(value: str) -> datetime:
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("NAIVE_TIMESTAMP")
    return dt.astimezone(timezone.utc)

def _id(payload: object) -> str:
    return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

@dataclass(frozen=True)
class ForecastRecord:
    forecast_id:str; security_id:str; event_key:str; decision_time:str; horizon_end:str
    probability:float; evidence_ids:tuple[str,...]; thesis_fingerprint:str
    model_id:str="orion"; created_at:str|None=None; sector:str|None=None; regime:str|None=None
    expected_return:float|None=None; horizon_days:int|None=None
    def __post_init__(self):
        if not self.security_id or not self.event_key: raise ValueError("INVALID_FORECAST_CONTEXT")
        if not 0<=float(self.probability)<=1: raise ValueError("INVALID_FORECAST_PROBABILITY")
        if _utc(self.horizon_end)<=_utc(self.decision_time): raise ValueError("INVALID_FORECAST_HORIZON")
        if not self.evidence_ids: raise ValueError("FORECAST_REQUIRES_EVIDENCE")
        if len(set(self.evidence_ids))!=len(self.evidence_ids): raise ValueError("DUPLICATE_EVIDENCE_IDS")
        if self.expected_return is not None and not math.isfinite(float(self.expected_return)): raise ValueError("INVALID_EXPECTED_RETURN")
        if self.horizon_days is not None and int(self.horizon_days) < 1: raise ValueError("INVALID_HORIZON_DAYS")

@dataclass(frozen=True)
class OutcomeRecord:
    forecast_id:str; occurred:bool; available_time:str; source_id:str
    evidence_ids:tuple[str,...]; content_hash:str
    return_pct:float|None=None; max_drawdown:float|None=None; mae:float|None=None; mfe:float|None=None; time_to_target_days:float|None=None
    def __post_init__(self):
        _utc(self.available_time)
        if not self.source_id or len(self.content_hash)!=64: raise ValueError("INVALID_OUTCOME_LINEAGE")
        if any(c not in "0123456789abcdefABCDEF" for c in self.content_hash): raise ValueError("INVALID_OUTCOME_HASH")
        for name in ('return_pct','max_drawdown','mae','mfe','time_to_target_days'):
            value=getattr(self,name)
            if value is not None and not math.isfinite(float(value)): raise ValueError(f'INVALID_{name.upper()}')
        if self.max_drawdown is not None and float(self.max_drawdown) > 0: raise ValueError('INVALID_MAX_DRAWDOWN')
        if self.mfe is not None and float(self.mfe) < 0: raise ValueError('INVALID_MFE')

@dataclass(frozen=True)
class ForecastScore:
    forecast_id:str; probability:float; outcome:int; brier:float; log_loss:float; resolved_at:str

@dataclass(frozen=True)
class CalibrationBin:
    lower:float; upper:float; count:int; mean_probability:float; observed_rate:float; absolute_gap:float

@dataclass(frozen=True)
class FeedbackReport:
    resolved:int; unresolved:int; brier:float|None; log_loss:float|None
    calibration_error:float|None; bins:tuple[CalibrationBin,...]

class ForecastLedger:
    """Append-only forecast/outcome ledger. Measures calibration; never self-modifies a model."""
    def __init__(self): self._forecasts={}; self._outcomes={}
    @staticmethod
    def make_forecast(*,security_id,event_key,decision_time,horizon_end,probability,evidence_ids,thesis_fingerprint,model_id="orion",forecast_id=None,created_at=None,sector=None,regime=None,expected_return=None,horizon_days=None):
        payload={"security_id":security_id,"event_key":event_key,"decision_time":decision_time,"horizon_end":horizon_end,"probability":float(probability),"evidence_ids":tuple(evidence_ids),"thesis_fingerprint":thesis_fingerprint,"model_id":model_id,"sector":sector,"regime":regime,"expected_return":expected_return,"horizon_days":horizon_days}
        return ForecastRecord(forecast_id or _id(payload),**payload,created_at=created_at)
    def issue(self,forecast):
        old=self._forecasts.get(forecast.forecast_id)
        if old is not None and old!=forecast: raise ValueError("FORECAST_ID_COLLISION")
        self._forecasts[forecast.forecast_id]=forecast; return forecast
    def resolve(self,outcome,*,evaluation_time):
        forecast=self._forecasts.get(outcome.forecast_id)
        if forecast is None: raise KeyError("FORECAST_NOT_FOUND")
        old=self._outcomes.get(outcome.forecast_id)
        if old is not None and old!=outcome: raise ValueError("OUTCOME_ID_COLLISION")
        if _utc(outcome.available_time)>_utc(evaluation_time): raise ValueError("FUTURE_OUTCOME")
        if _utc(outcome.available_time)<_utc(forecast.horizon_end): raise ValueError("OUTCOME_BEFORE_HORIZON")
        self._outcomes[outcome.forecast_id]=outcome
        p=float(forecast.probability); y=int(outcome.occurred); q=min(max(p,1e-15),1-1e-15)
        return ForecastScore(forecast.forecast_id,p,y,(p-y)**2,-(y*math.log(q)+(1-y)*math.log(1-q)),outcome.available_time)
    def load(self, forecasts: Iterable[ForecastRecord], outcomes: Iterable[OutcomeRecord]):
        for f in forecasts: self.issue(f)
        for o in outcomes:
            f=self._forecasts.get(o.forecast_id)
            if f is None: raise KeyError("FORECAST_NOT_FOUND")
            if _utc(o.available_time) < _utc(f.horizon_end): raise ValueError("OUTCOME_BEFORE_HORIZON")
            self._outcomes[o.forecast_id]=o
        return self

    def forecasts(self): return tuple(self._forecasts[k] for k in sorted(self._forecasts))
    def outcomes(self): return tuple(self._outcomes[k] for k in sorted(self._outcomes))
    def report(self,bins=10):
        if not 1<=bins<=20: raise ValueError("INVALID_CALIBRATION_BINS")
        rows=[]
        for fid,o in self._outcomes.items():
            p=float(self._forecasts[fid].probability); y=int(o.occurred); q=min(max(p,1e-15),1-1e-15)
            rows.append((p,y,(p-y)**2,-(y*math.log(q)+(1-y)*math.log(1-q))))
        n=len(rows)
        if not n: return FeedbackReport(0,len(self._forecasts),None,None,None,())
        width=1/bins; out=[]
        for i in range(bins):
            lo,hi=i*width,(i+1)*width
            m=[r for r in rows if (lo<=r[0]<hi) or (i==bins-1 and r[0]<=hi)]
            if m:
                mp=sum(r[0] for r in m)/len(m); rate=sum(r[1] for r in m)/len(m)
                out.append(CalibrationBin(lo,hi,len(m),mp,rate,abs(mp-rate)))
        cal=sum(x.count*x.absolute_gap for x in out)/n
        return FeedbackReport(n,len(self._forecasts)-n,sum(r[2] for r in rows)/n,sum(r[3] for r in rows)/n,cal,tuple(out))

class CalibrationEngine:
    def score(self,forecasts:Iterable[ForecastRecord],outcomes:Iterable[OutcomeRecord],*,evaluation_time:str):
        ledger=ForecastLedger()
        for f in forecasts: ledger.issue(f)
        for o in outcomes: ledger.resolve(o,evaluation_time=evaluation_time)
        return ledger.report()
