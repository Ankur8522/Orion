from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class ForecastEvidence:
    evidence_id: str
    signal: float
    reliability: float = 1.0
    direction: float = 1.0

@dataclass(frozen=True)
class ProbabilisticForecast:
    probability: float
    uncertainty: float
    base_rate: float
    evidence_count: int
    effective_signal: float
    model_id: str
    thesis_fingerprint: str
    lineage_hash: str

class ProbabilisticForecastEngine:
    """Bounded forecast generator over caller-supplied evidence only.

    It produces a model output, not a claimed empirical accuracy estimate. Base rate,
    signals and reliability must be supplied; missing evidence never becomes a neutral
    synthetic observation.
    """
    def generate(self, *, base_rate: float, evidence: Sequence[ForecastEvidence],
                 model_id: str = 'orion-bounded-logistic', temperature: float = 1.0,
                 prior_strength: float = 1.0) -> ProbabilisticForecast:
        p0=float(base_rate)
        if not 0.0 < p0 < 1.0: raise ValueError('INVALID_BASE_RATE')
        if temperature <= 0 or prior_strength < 0: raise ValueError('INVALID_FORECAST_PARAMETER')
        rows=tuple(evidence)
        if not rows: raise ValueError('FORECAST_REQUIRES_EVIDENCE')
        if any(not e.evidence_id or not -1 <= float(e.signal) <= 1 or not 0 <= float(e.reliability) <= 1 or float(e.direction) not in (-1.0,1.0) for e in rows):
            raise ValueError('INVALID_FORECAST_EVIDENCE')
        weighted=sum(float(e.signal)*float(e.reliability)*float(e.direction) for e in rows)
        denom=prior_strength+sum(float(e.reliability) for e in rows)
        effective=weighted/denom if denom else 0.0
        logit=math.log(p0/(1-p0)) + effective/float(temperature)
        p=1.0/(1.0+math.exp(-max(min(logit,40),-40)))
        uncertainty=min(1.0, 1.0/(1.0+sum(float(e.reliability) for e in rows)))
        fingerprint=sha256(json.dumps({'model':model_id,'base_rate':p0,'evidence':[(e.evidence_id,e.signal,e.reliability,e.direction) for e in rows]}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        lineage=sha256(json.dumps({'model':model_id,'base_rate':p0,'effective_signal':effective,'probability':p,'uncertainty':uncertainty,'fingerprint':fingerprint},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return ProbabilisticForecast(round(p,12),round(uncertainty,12),round(p0,12),len(rows),round(effective,12),model_id,fingerprint,lineage)
