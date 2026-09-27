from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable

from orion.brain.progressive import Belief, Challenge, MarketState, ProgressiveAssessment, ProgressiveDecisionBrain
from orion.learning.feedback import FeedbackReport


class ReasoningPhase(str, Enum):
    OBSERVE = "OBSERVE"
    HYPOTHESIZE = "HYPOTHESIZE"
    CHALLENGE = "CHALLENGE"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    RISK = "RISK"
    DECIDE = "DECIDE"
    MONITOR = "MONITOR"
    REOPEN = "REOPEN"


@dataclass(frozen=True)
class ProgressiveMemoryState:
    thesis_id: str
    cycle_id: str
    phase: ReasoningPhase
    assessment: ProgressiveAssessment
    belief_delta: float
    uncertainty_delta: float
    robustness_delta: float
    fragility_delta: float
    evidence_delta: float
    scenario_delta: float
    challenge_delta: float
    feedback_quality: float
    next_actions: tuple[str, ...]
    lineage_hash: str


class ProgressiveMemory:
    """Append-only working memory for thesis evolution.

    Memory records what ORION believed at each cycle; it never silently rewrites
    prior states. This makes progressive reasoning replayable and auditable.
    """

    def __init__(self):
        self._states: dict[str, list[ProgressiveMemoryState]] = {}

    def append(self, state: ProgressiveMemoryState) -> ProgressiveMemoryState:
        self._states.setdefault(state.thesis_id, []).append(state)
        return state

    def history(self, thesis_id: str) -> tuple[ProgressiveMemoryState, ...]:
        return tuple(self._states.get(thesis_id, ()))

    def last(self, thesis_id: str) -> ProgressiveMemoryState | None:
        rows = self._states.get(thesis_id, ())
        return rows[-1] if rows else None

    def size(self, thesis_id: str | None = None) -> int:
        if thesis_id is None:
            return sum(len(x) for x in self._states.values())
        return len(self._states.get(thesis_id, ()))


class ProgressiveLearningPolicy:
    """Turns observed feedback into bounded reasoning adjustments.

    The policy is deliberately conservative: calibration can improve confidence,
    but poor calibration can only reduce it. It never invents outcome data.
    """

    @staticmethod
    def feedback_quality(report: FeedbackReport | None) -> float:
        if report is None or report.resolved == 0:
            return 0.5
        calibration = 1.0 - float(report.calibration_error or 0.0)
        brier_quality = 1.0 - min(1.0, float(report.brier or 0.0))
        return max(0.0, min(1.0, 0.65 * calibration + 0.35 * brier_quality))

    @staticmethod
    def effective_calibration(base: float, report: FeedbackReport | None) -> float:
        if report is None or report.resolved == 0:
            return max(0.0, min(1.0, float(base)))
        return max(0.0, min(1.0, 0.35 * float(base) + 0.65 * ProgressiveLearningPolicy.feedback_quality(report)))

    @staticmethod
    def phase(assessment: ProgressiveAssessment, *, has_delta: bool, material_change: bool) -> ReasoningPhase:
        if material_change:
            return ReasoningPhase.REOPEN
        if assessment.challenge_score >= 0.45:
            return ReasoningPhase.CHALLENGE
        if assessment.scenario_score < 0.50:
            return ReasoningPhase.COUNTERFACTUAL
        if assessment.fragility >= 0.60:
            return ReasoningPhase.RISK
        if assessment.uncertainty >= 0.60:
            return ReasoningPhase.HYPOTHESIZE
        if not has_delta and assessment.confidence_band == "HIGH":
            return ReasoningPhase.MONITOR
        return ReasoningPhase.DECIDE

    @staticmethod
    def actions(assessment: ProgressiveAssessment, phase: ReasoningPhase, *, material_change: bool) -> tuple[str, ...]:
        actions = list(assessment.next_checks)
        if phase is ReasoningPhase.REOPEN:
            actions.insert(0, "reopen_thesis_after_material_change")
        elif phase is ReasoningPhase.CHALLENGE:
            actions.insert(0, "run_bear_case_and_evidence_falsification")
        elif phase is ReasoningPhase.COUNTERFACTUAL:
            actions.insert(0, "stress_key_causal_edges_and_second_order_effects")
        elif phase is ReasoningPhase.RISK:
            actions.insert(0, "tighten_risk_budget_and_monitor_failure_thresholds")
        elif phase is ReasoningPhase.HYPOTHESIZE:
            actions.insert(0, "collect_discriminating_evidence")
        elif phase is ReasoningPhase.MONITOR:
            actions.insert(0, "monitor_only_until_next_material_change")
        if material_change and "reopen_thesis_after_material_change" not in actions:
            actions.append("reopen_thesis_after_material_change")
        return tuple(dict.fromkeys(actions))


class ProgressiveReasoningLoop:
    """Stateful progressive brain sitting above ORION's existing decision engines."""

    def __init__(self, brain: ProgressiveDecisionBrain | None = None, memory: ProgressiveMemory | None = None):
        self.brain = brain or ProgressiveDecisionBrain()
        self.memory = memory or ProgressiveMemory()
        self.policy = ProgressiveLearningPolicy()

    @staticmethod
    def _hash(payload: object) -> str:
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    def run_cycle(
        self,
        *,
        cycle_id: str,
        belief: Belief,
        challenges: tuple[Challenge, ...] = (),
        scenario_score: float = 0.5,
        calibration_score: float = 0.5,
        market_state: MarketState | None = None,
        feedback_report: FeedbackReport | None = None,
        evidence_delta: float = 0.0,
        scenario_delta: float = 0.0,
        material_change: bool = False,
    ) -> ProgressiveMemoryState:
        if not cycle_id:
            raise ValueError("INVALID_CYCLE_ID")
        for value in (evidence_delta, scenario_delta):
            if not -1 <= float(value) <= 1:
                raise ValueError("DELTA_MUST_BE_BOUNDED")

        previous = self.memory.last(belief.thesis_id)
        effective_calibration = self.policy.effective_calibration(calibration_score, feedback_report)
        assessment = self.brain.assess(
            belief,
            challenges,
            scenario_score=scenario_score,
            calibration_score=effective_calibration,
            market_state=market_state,
        )

        if previous is None:
            deltas = {"belief": 0.0, "uncertainty": 0.0, "robustness": 0.0, "fragility": 0.0, "challenge": 0.0}
            has_delta = False
        else:
            deltas = {
                "belief": assessment.belief - previous.assessment.belief,
                "uncertainty": assessment.uncertainty - previous.assessment.uncertainty,
                "robustness": assessment.robustness - previous.assessment.robustness,
                "fragility": assessment.fragility - previous.assessment.fragility,
                "challenge": assessment.challenge_score - previous.assessment.challenge_score,
            }
            has_delta = any(abs(x) >= 0.05 for x in deltas.values()) or material_change

        phase = self.policy.phase(assessment, has_delta=has_delta, material_change=material_change)
        actions = self.policy.actions(assessment, phase, material_change=material_change)
        feedback_quality = self.policy.feedback_quality(feedback_report)
        payload = {
            "thesis_id": belief.thesis_id,
            "cycle_id": cycle_id,
            "phase": phase.value,
            "assessment": assessment.lineage_hash,
            "deltas": deltas,
            "evidence_delta": round(float(evidence_delta), 12),
            "scenario_delta": round(float(scenario_delta), 12),
            "feedback_quality": round(feedback_quality, 12),
            "actions": actions,
        }
        state = ProgressiveMemoryState(
            thesis_id=belief.thesis_id,
            cycle_id=cycle_id,
            phase=phase,
            assessment=assessment,
            belief_delta=round(deltas["belief"], 12),
            uncertainty_delta=round(deltas["uncertainty"], 12),
            robustness_delta=round(deltas["robustness"], 12),
            fragility_delta=round(deltas["fragility"], 12),
            evidence_delta=round(float(evidence_delta), 12),
            scenario_delta=round(float(scenario_delta), 12),
            challenge_delta=round(deltas["challenge"], 12),
            feedback_quality=round(feedback_quality, 12),
            next_actions=actions,
            lineage_hash=self._hash(payload),
        )
        return self.memory.append(state)
