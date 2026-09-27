from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence

from ..decision.trade_ensemble import SpecialistOutput, TradeIntelligenceEnsemble, EnsembleOutput
from ..learning.specialist_models import ChronologicalLogisticSpecialist, SpecialistPrediction
from ..learning.meta_intelligence import LearnedMetaIntelligence
from .decision_world import DecisionWorld

@dataclass(frozen=True)
class IntelligenceResult:
    status: str
    ensemble: EnsembleOutput | None
    predictions: tuple[SpecialistPrediction, ...]
    blockers: tuple[str, ...]
    lineage_hash: str

class DecisionIntelligenceEngine:
    """Governed inference boundary: DecisionWorld -> trained specialists -> meta intelligence.

    The engine refuses to infer from an unready DecisionWorld and never falls back to
    deterministic domain scores when trained models are required.
    """
    def infer(
        self,
        world: DecisionWorld,
        models: Mapping[str, ChronologicalLogisticSpecialist],
        *,
        meta_model: LearnedMetaIntelligence | None = None,
        required_specialists: Sequence[str] = (),
        evidence_count: int = 0,
        regime: str = 'UNKNOWN',
    ) -> IntelligenceResult:
        blockers=list(world.readiness.blockers)
        if world.readiness.status != 'READY':
            payload={'status':'BLOCKED_DECISION_WORLD','blockers':sorted(set(blockers)),'world':world.lineage_hash}
            return IntelligenceResult('BLOCKED_DECISION_WORLD',None,(),tuple(sorted(set(blockers))),self._hash(payload))
        predictions=[]; outputs=[]
        for name, model in sorted(models.items()):
            pred=model.predict(world.features or {}, regime=regime)
            if pred is None:
                continue
            predictions.append(pred)
            outputs.append(SpecialistOutput(
                name=name,
                probability=pred.probability,
                evidence_count=evidence_count,
                model_id=pred.model_id,
                trained=True,
                out_of_sample_brier=pred.metrics.brier,
                calibration_error=pred.metrics.calibration_error,
                regime_coverage=pred.regime_coverage,
                feature_coverage=pred.feature_coverage,
            ))
        ensemble=TradeIntelligenceEnsemble(meta_model=meta_model, min_specialists=max(1,len(required_specialists) or 2)).combine(
            outputs, required_specialists=required_specialists
        )
        status='READY' if ensemble.status=='READY' else ensemble.status
        payload={'status':status,'world':world.lineage_hash,'specialists':[(x.name,x.model_id,x.probability) for x in outputs],'ensemble':ensemble.lineage_hash}
        return IntelligenceResult(status,ensemble,tuple(predictions),tuple(sorted(set(blockers))),self._hash(payload))

    @staticmethod
    def _hash(obj):
        return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
