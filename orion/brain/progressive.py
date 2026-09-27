from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from math import sqrt


class Regime(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    TRANSITION = "TRANSITION"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class MarketState:
    """Evidence supplied market state. Values are normalized where documented."""
    volatility: float
    breadth: float
    trend: float
    macro_pressure: float = 0.0


@dataclass(frozen=True)
class Belief:
    thesis_id: str
    prior: float
    evidence_support: float
    scenario_support: float
    adversarial_penalty: float = 0.0
    calibration_adjustment: float = 0.0


@dataclass(frozen=True)
class Challenge:
    name: str
    severity: float
    evidence_gap: float = 0.0
    scenario_gap: float = 0.0


@dataclass(frozen=True)
class ProgressiveAssessment:
    thesis_id: str
    regime: Regime
    belief: float
    uncertainty: float
    robustness: float
    fragility: float
    challenge_score: float
    scenario_score: float
    calibration_score: float
    confidence_band: str
    next_checks: tuple[str, ...]
    lineage_hash: str


class ProgressiveDecisionBrain:
    """Auditable second-order reasoning layer for ORION.

    It does not fetch data, invent probabilities, or mutate a model. It combines
    caller-supplied evidence/scenario/calibration signals into a bounded belief,
    explicitly penalizes adversarial challenges, and exposes uncertainty/fragility.
    """

    @staticmethod
    def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))

    @staticmethod
    def classify_regime(state: MarketState) -> Regime:
        for value in (state.volatility, state.breadth, state.trend, state.macro_pressure):
            if not -1 <= value <= 1:
                raise ValueError("MARKET_STATE_VALUES_MUST_BE_BOUNDED")
        risk_score = 0.45 * state.trend + 0.35 * state.breadth - 0.55 * state.volatility - 0.35 * state.macro_pressure
        if state.volatility > 0.7 and risk_score < -0.25:
            return Regime.RISK_OFF
        if risk_score > 0.35:
            return Regime.RISK_ON
        if abs(risk_score) < 0.12 or abs(state.trend) < 0.1:
            return Regime.NEUTRAL
        return Regime.TRANSITION

    def assess(
        self,
        belief: Belief,
        challenges: tuple[Challenge, ...] = (),
        scenario_score: float = 0.5,
        calibration_score: float = 0.5,
        market_state: MarketState | None = None,
    ) -> ProgressiveAssessment:
        if not belief.thesis_id:
            raise ValueError("INVALID_THESIS_ID")
        values = [belief.prior, belief.evidence_support, belief.scenario_support,
                  belief.adversarial_penalty, belief.calibration_adjustment,
                  scenario_score, calibration_score]
        if any(not -1 <= v <= 1 for v in values):
            raise ValueError("BELIEF_SIGNALS_MUST_BE_BOUNDED")
        for c in challenges:
            if not c.name or not 0 <= c.severity <= 1 or not 0 <= c.evidence_gap <= 1 or not 0 <= c.scenario_gap <= 1:
                raise ValueError("INVALID_CHALLENGE")

        challenge_score = sum(c.severity * (1 + 0.5 * c.evidence_gap + 0.5 * c.scenario_gap) for c in challenges)
        challenge_penalty = self._clip(challenge_score / max(1, len(challenges))) if challenges else 0.0
        support = 0.35 * self._clip(belief.evidence_support) + 0.35 * self._clip(belief.scenario_support) + 0.30 * self._clip(calibration_score)
        prior = self._clip(belief.prior)
        adjustment = 0.25 * belief.calibration_adjustment
        raw = 0.45 * prior + 0.55 * support + adjustment - 0.35 * challenge_penalty - 0.15 * self._clip(belief.adversarial_penalty)
        posterior = self._clip(raw)

        scenario = self._clip(scenario_score)
        calibration = self._clip(calibration_score)
        uncertainty = self._clip(1.0 - (0.45 * abs(posterior - 0.5) * 2 + 0.30 * calibration + 0.25 * scenario))
        robustness = self._clip(0.45 * (1 - challenge_penalty) + 0.30 * scenario + 0.25 * calibration)
        fragility = self._clip(1 - robustness)

        band = "HIGH" if posterior >= 0.75 and uncertainty < 0.35 else "MEDIUM" if posterior >= 0.55 and uncertainty < 0.60 else "LOW"
        checks = []
        if challenge_penalty >= 0.35:
            checks.append("resolve_adversarial_challenges")
        if scenario < 0.45:
            checks.append("expand_counterfactual_scenarios")
        if calibration < 0.50:
            checks.append("collect_more_outcome_feedback")
        if not checks:
            checks.append("monitor_thesis_and_retest_on_material_changes")

        regime = self.classify_regime(market_state) if market_state else Regime.NEUTRAL
        payload = {
            "thesis_id": belief.thesis_id,
            "regime": regime.value,
            "posterior": round(posterior, 12),
            "uncertainty": round(uncertainty, 12),
            "robustness": round(robustness, 12),
            "fragility": round(fragility, 12),
            "challenge_score": round(challenge_score, 12),
            "scenario_score": round(scenario, 12),
            "calibration_score": round(calibration, 12),
            "checks": checks,
        }
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return ProgressiveAssessment(
            belief.thesis_id, regime, round(posterior, 12), round(uncertainty, 12),
            round(robustness, 12), round(fragility, 12), round(challenge_score, 12),
            round(scenario, 12), round(calibration, 12), band, tuple(checks), lineage,
        )

    @staticmethod
    def compare(a: ProgressiveAssessment, b: ProgressiveAssessment) -> dict[str, float]:
        """Return explainable deltas between two dated brain states."""
        return {
            "belief_delta": round(b.belief - a.belief, 12),
            "uncertainty_delta": round(b.uncertainty - a.uncertainty, 12),
            "robustness_delta": round(b.robustness - a.robustness, 12),
            "fragility_delta": round(b.fragility - a.fragility, 12),
            "challenge_delta": round(b.challenge_score - a.challenge_score, 12),
        }
