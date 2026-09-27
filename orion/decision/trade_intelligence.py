from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Mapping, Sequence

from ..learning.calibration import CalibrationModel, CalibrationPoint, IsotonicCalibrationEngine

from ..data.time import parse_utc


FEATURES = (
    "fundamental_quality",
    "earnings_growth",
    "cashflow_quality",
    "valuation_attractiveness",
    "technical_trend",
    "technical_momentum",
    "volume_confirmation",
    "breakout_quality",
    "historical_setup",
    "catalyst_strength",
    "business_visibility",
    "forensic_quality",
    "regime_fit",
    "risk_quality",
)


def _clip(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, x))))


@dataclass(frozen=True)
class TradeFeatureVector:
    security_id: str
    as_of: str
    values: tuple[tuple[str, float], ...]
    missing: tuple[str, ...]
    source_ids: tuple[str, ...] = ()
    lineage_hash: str = ""

    @property
    def mapping(self) -> dict[str, float]:
        return dict(self.values)

    @property
    def completeness(self) -> float:
        return len(self.values) / len(FEATURES)


@dataclass(frozen=True)
class TradeScore:
    security_id: str
    as_of: str
    probability: float
    score: float
    confidence: float
    action: str
    feature_completeness: float
    expected_return: float | None
    risk_penalty: float
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    model_id: str
    lineage_hash: str


@dataclass(frozen=True)
class TradeTrainingRow:
    security_id: str
    as_of: str
    features: Mapping[str, float]
    outcome: int
    available_time: str
    outcome_available_time: str = ""


@dataclass(frozen=True)
class TradeTrainingReport:
    model_id: str
    rows: int
    train_rows: int
    validation_rows: int
    train_brier: float | None
    validation_brier: float | None
    coefficients: tuple[tuple[str, float], ...]
    intercept: float
    lineage_hash: str


class TradeIntelligenceEngine:
    """Evidence-fused trade-ranking brain.

    The engine is deliberately input-bound: it never fetches or invents market data.
    Features must already be PIT-safe and normalized to [0, 1]. Training only accepts
    rows whose observation availability is no later than the row's decision timestamp.
    """

    DEFAULT_WEIGHTS = {
        "fundamental_quality": 0.11,
        "earnings_growth": 0.09,
        "cashflow_quality": 0.08,
        "valuation_attractiveness": 0.09,
        "technical_trend": 0.08,
        "technical_momentum": 0.07,
        "volume_confirmation": 0.05,
        "breakout_quality": 0.06,
        "historical_setup": 0.09,
        "catalyst_strength": 0.06,
        "business_visibility": 0.06,
        "forensic_quality": 0.06,
        "regime_fit": 0.06,
        "risk_quality": 0.04,
    }

    def __init__(self, *, model_id: str = "orion-trade-fusion-v1", coefficients: Mapping[str, float] | None = None, intercept: float = 0.0, calibration: CalibrationModel | None = None):
        self.model_id = model_id
        self.coefficients = {k: float(v) for k, v in (coefficients or self.DEFAULT_WEIGHTS).items() if k in FEATURES}
        for feature in FEATURES:
            self.coefficients.setdefault(feature, 0.0)
        self.intercept = float(intercept)
        self.calibration = calibration

    @staticmethod
    def build_features(
        security_id: str,
        as_of: str,
        *,
        fundamental: Mapping[str, float] | None = None,
        technical: Mapping[str, float] | None = None,
        historical: Mapping[str, float] | None = None,
        context: Mapping[str, float] | None = None,
        source_ids: Sequence[str] = (),
    ) -> TradeFeatureVector:
        merged: dict[str, float] = {}
        for group in (fundamental or {}, technical or {}, historical or {}, context or {}):
            for key, value in group.items():
                if key in FEATURES:
                    if not math.isfinite(float(value)):
                        raise ValueError("NON_FINITE_TRADE_FEATURE")
                    merged[key] = _clip(float(value))
        missing = tuple(k for k in FEATURES if k not in merged)
        payload = {"security_id": security_id, "as_of": as_of, "values": sorted(merged.items()), "missing": missing, "source_ids": sorted(set(source_ids))}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return TradeFeatureVector(security_id, as_of, tuple(sorted(merged.items())), missing, tuple(sorted(set(source_ids))), lineage)

    def score(self, vector: TradeFeatureVector, *, expected_return: float | None = None, minimum_completeness: float = 0.70) -> TradeScore:
        if not 0 <= minimum_completeness <= 1:
            raise ValueError("INVALID_MINIMUM_COMPLETENESS")
        x = vector.mapping
        blockers: list[str] = []
        if vector.completeness < minimum_completeness:
            blockers.append("INSUFFICIENT_FEATURE_COMPLETENESS")
        if "forensic_quality" in x and x["forensic_quality"] < 0.35:
            blockers.append("FORENSIC_RISK")
        if "risk_quality" in x and x["risk_quality"] < 0.35:
            blockers.append("RISK_QUALITY_LOW")
        if "regime_fit" in x and x["regime_fit"] < 0.30:
            blockers.append("REGIME_MISMATCH")

        usable = {k: v for k, v in x.items() if k in self.coefficients}
        weight_total = sum(abs(self.coefficients[k]) for k in usable) or 1.0
        weighted = sum(self.coefficients[k] * usable[k] for k in usable) / weight_total
        raw_probability = _sigmoid((weighted - 0.5) * 6.0 + self.intercept)
        probability = self.calibration.transform(raw_probability) if self.calibration is not None else raw_probability
        risk_penalty = 1.0 - _clip((x.get("risk_quality", 0.5) + x.get("forensic_quality", 0.5)) / 2.0)
        score = _clip(probability * (1.0 - 0.35 * risk_penalty)) * 100.0
        confidence = _clip(vector.completeness * (1.0 - 0.45 * risk_penalty))
        reasons = tuple(sorted(k.upper() for k, v in usable.items() if v >= 0.70))
        if blockers:
            action = "BLOCKED"
        elif probability >= 0.72:
            action = "STRONG_CANDIDATE"
        elif probability >= 0.60:
            action = "CANDIDATE"
        elif probability >= 0.50:
            action = "WATCH"
        else:
            action = "NO_ACTION"
        payload = {"security_id": vector.security_id, "as_of": vector.as_of, "probability": round(probability, 12), "score": round(score, 12), "confidence": round(confidence, 12), "action": action, "feature_lineage": vector.lineage_hash, "model_id": self.model_id}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return TradeScore(vector.security_id, vector.as_of, round(probability, 12), round(score, 12), round(confidence, 12), action, round(vector.completeness, 12), expected_return, round(risk_penalty, 12), reasons, tuple(sorted(set(blockers))), self.model_id, lineage)

    def calibrate(self, points: Sequence[CalibrationPoint], *, min_observations: int = 20) -> CalibrationModel:
        self.calibration = IsotonicCalibrationEngine().fit(points, min_observations=min_observations)
        return self.calibration

    def build_from_raw(
        self,
        security_id: str,
        as_of: str,
        *,
        fundamental_latest: Mapping[str, object] = (),
        fundamental_history: Sequence[Mapping[str, object]] = (),
        market_rows: Sequence[Mapping[str, object]] = (),
        historical_features: Mapping[str, float] | None = None,
        context_features: Mapping[str, float] | None = None,
        source_ids: Sequence[str] = (),
    ) -> TradeFeatureVector:
        from .fundamental_features import FundamentalFeatureEngine
        from .technical_features import TechnicalFeatureEngine
        fundamental = FundamentalFeatureEngine().build(
            security_id, as_of=as_of, latest=dict(fundamental_latest), history=fundamental_history, source_ids=source_ids
        )
        technical = TechnicalFeatureEngine().build(
            security_id, market_rows, as_of=as_of, source_ids=source_ids
        )
        merged_sources = tuple(sorted(set(source_ids) | set(fundamental.source_ids) | set(technical.source_ids)))
        return self.build_features(
            security_id, as_of,
            fundamental=fundamental.mapping,
            technical=technical.mapping,
            historical=historical_features or {},
            context=context_features or {},
            source_ids=merged_sources,
        )

    def rank(self, vectors: Sequence[TradeFeatureVector], *, minimum_completeness: float = 0.70) -> tuple[TradeScore, ...]:
        ids = [v.security_id for v in vectors]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_SECURITY_ID")
        scored = [self.score(v, minimum_completeness=minimum_completeness) for v in vectors]
        return tuple(sorted(scored, key=lambda s: (-s.score, -s.confidence, s.security_id)))

    def fit(self, rows: Sequence[TradeTrainingRow], *, learning_rate: float = 0.08, epochs: int = 250, l2: float = 0.10, validation_fraction: float = 0.25, training_cutoff: str | None = None, allow_missing_features: bool = False) -> TradeTrainingReport:
        if len(rows) < 8:
            raise ValueError("INSUFFICIENT_TRAINING_ROWS")
        if not 0 < learning_rate <= 1 or epochs < 1 or l2 < 0 or not 0 < validation_fraction < 0.5:
            raise ValueError("INVALID_TRAINING_PARAMETERS")
        ordered = sorted(rows, key=lambda r: (r.as_of, r.security_id))
        for row in ordered:
            if row.outcome not in (0, 1):
                raise ValueError("INVALID_TRAINING_OUTCOME")
            if parse_utc(row.available_time) > parse_utc(row.as_of):
                raise ValueError("FUTURE_TRAINING_OBSERVATION")
            if training_cutoff is not None and row.outcome_available_time and parse_utc(row.outcome_available_time) > parse_utc(training_cutoff):
                raise ValueError("UNRESOLVED_TRAINING_OUTCOME")
            unknown = set(row.features) - set(FEATURES)
            if unknown:
                raise ValueError("INVALID_TRAINING_FEATURE")
            if not allow_missing_features and set(row.features) != set(FEATURES):
                raise ValueError("MISSING_TRAINING_FEATURE")
            for key, value in row.features.items():
                if not math.isfinite(float(value)):
                    raise ValueError("INVALID_TRAINING_FEATURE")
        split = max(4, int(len(ordered) * (1.0 - validation_fraction)))
        split = min(split, len(ordered) - 2)
        train, validation = ordered[:split], ordered[split:]
        weights = dict(self.coefficients)
        intercept = self.intercept
        for _ in range(epochs):
            grad = {k: 0.0 for k in FEATURES}
            gi = 0.0
            for row in train:
                z = intercept + sum(weights[k] * _clip(row.features[k]) for k in FEATURES) if not allow_missing_features else intercept + sum(weights[k] * _clip(row.features.get(k, 0.5)) for k in FEATURES)
                p = _sigmoid(z)
                err = p - row.outcome
                gi += err
                for k in FEATURES:
                    grad[k] += err * _clip(row.features.get(k, 0.5))
            n = float(len(train))
            intercept -= learning_rate * gi / n
            for k in FEATURES:
                grad[k] = grad[k] / n + l2 * weights[k]
                weights[k] -= learning_rate * grad[k]
        self.coefficients = weights
        self.intercept = intercept
        train_brier = self._brier(train, weights, intercept, allow_missing_features=allow_missing_features)
        val_brier = self._brier(validation, weights, intercept, allow_missing_features=allow_missing_features)
        payload = {"model_id": self.model_id, "train_rows": len(train), "validation_rows": len(validation), "coefficients": sorted(weights.items()), "intercept": round(intercept, 12), "train_brier": train_brier, "validation_brier": val_brier, "as_of": [ordered[0].as_of, ordered[-1].as_of]}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return TradeTrainingReport(self.model_id, len(ordered), len(train), len(validation), train_brier, val_brier, tuple(sorted((k, round(v, 12)) for k, v in weights.items())), round(intercept, 12), lineage)

    @staticmethod
    def _brier(rows: Sequence[TradeTrainingRow], weights: Mapping[str, float], intercept: float, *, allow_missing_features: bool = False) -> float | None:
        if not rows:
            return None
        total = 0.0
        for row in rows:
            z = intercept + sum(weights[k] * _clip(row.features[k]) for k in FEATURES) if not allow_missing_features else intercept + sum(weights[k] * _clip(row.features.get(k, 0.5)) for k in FEATURES)
            p = _sigmoid(z)
            total += (p - row.outcome) ** 2
        return round(total / len(rows), 12)
