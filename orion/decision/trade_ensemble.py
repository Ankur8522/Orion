from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence
from ..learning.meta_intelligence import LearnedMetaIntelligence

@dataclass(frozen=True)
class SpecialistOutput:
    name: str
    probability: float | None
    evidence_count: int
    model_id: str
    trained: bool = False
    out_of_sample_brier: float | None = None
    calibration_error: float | None = None
    regime_coverage: int = 1
    feature_coverage: float = 1.0

@dataclass(frozen=True)
class EnsembleOutput:
    probability: float | None
    uncertainty: float
    status: str
    specialists: tuple[SpecialistOutput, ...]
    disagreement: float | None
    lineage_hash: str

class TradeIntelligenceEnsemble:
    """Meta-model boundary for specialist forecasts.

    It refuses to manufacture a probability when no empirically trained specialist
    exists. Static weights are permitted only for diagnostic aggregation, never for
    claiming empirical accuracy.
    """
    def __init__(self, weights: Mapping[str,float] | None = None, min_specialists: int = 2, meta_model: LearnedMetaIntelligence | None = None):
        self.weights={k:float(v) for k,v in (weights or {}).items()}
        self.min_specialists=max(1,int(min_specialists))
        self.meta_model=meta_model

    def combine(self, specialists: Sequence[SpecialistOutput], *, required_specialists: Sequence[str] = (), min_regimes: int = 1, min_feature_coverage: float = 0.80) -> EnsembleOutput:
        rows=tuple(specialists)
        required=set(required_specialists)
        valid=tuple(x for x in rows if x.probability is not None and x.trained and 0<=x.probability<=1 and x.feature_coverage>=min_feature_coverage and x.regime_coverage>=min_regimes and (not required or (x.out_of_sample_brier is not None and 0<=x.out_of_sample_brier<=1)))
        if required and not required.issubset({x.name for x in valid}):
            payload={'status':'REQUIRED_SPECIALIST_COVERAGE_MISSING','required':sorted(required),'valid':[x.name for x in valid]}
            return EnsembleOutput(None,1.0,'REQUIRED_SPECIALIST_COVERAGE_MISSING',rows,None,sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
        if len(valid)<self.min_specialists:
            payload={'status':'INSUFFICIENT_TRAINED_SPECIALISTS','specialists':[(x.name,x.model_id,x.trained,x.probability) for x in rows]}
            return EnsembleOutput(None,1.0,'INSUFFICIENT_TRAINED_SPECIALISTS',rows,None,sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
        meta_used=False
        if self.meta_model is not None and self.meta_model.metrics.trained:
            try:
                meta=self.meta_model.predict({x.name:x.probability for x in valid})
                p=meta.probability
                weights=[max(0.0,float(meta.specialist_weights.get(x.name,0.0))) for x in valid]
                total=sum(weights) or 1.0
                disagreement=math.sqrt(sum(w*(x.probability-p)**2 for w,x in zip(weights,valid))/total)
                uncertainty=min(1.0,0.65*meta.uncertainty+0.35*disagreement)
                meta_used=True
            except (ValueError, RuntimeError):
                meta_used=False
        if not meta_used:
            weights=[max(0.0,self.weights.get(x.name,1.0)) for x in valid]
            total=sum(weights)
            if total<=0: weights=[1.0]*len(valid); total=len(valid)
            p=sum(w*x.probability for w,x in zip(weights,valid))/total
            disagreement=math.sqrt(sum(w*(x.probability-p)**2 for w,x in zip(weights,valid))/total)
            uncertainty=min(1.0, 0.5*disagreement + 0.5*(1.0-sum(1 for x in valid if x.evidence_count>=20)/max(1,len(valid))))
        payload={'status':'READY','probability':round(p,12),'uncertainty':round(uncertainty,12),'meta_used':meta_used,'specialists':[(x.name,x.model_id,x.probability,x.evidence_count,x.out_of_sample_brier,x.calibration_error,x.regime_coverage) for x in valid]}
        return EnsembleOutput(round(p,12),round(uncertainty,12),'READY',rows,round(disagreement,12),sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
