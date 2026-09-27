from orion.brain.kernel import IntelligenceCase, InvestmentIntelligenceKernel
from orion.brain.progressive import Belief, Challenge
from orion.brain.progressive_loop import ProgressiveMemory, ProgressiveReasoningLoop, ReasoningPhase
from orion.learning.feedback import CalibrationBin, FeedbackReport
from orion.decision.plane import AgentFinding


def test_progressive_brain_reopens_and_tracks_deltas():
    k = InvestmentIntelligenceKernel()
    base = dict(
        security_id="ABC", decision_time="2026-09-27T00:00:00Z", thesis="growth thesis",
        evidence_ids=("e1",), findings=(AgentFinding("fundamental", "SUPPORT", ("e1",), ("growth",)),),
        belief=Belief("t1", 0.60, 0.80, 0.80, 0.05, 0.10), priority_score=70,
    )
    first = k.run(IntelligenceCase(**base, cycle_id="c1"))
    changed = dict(base)
    changed.update({"cycle_id": "c2", "material_change": True, "evidence_delta": -0.5, "scenario_delta": -0.4,
                    "challenges": (Challenge("margin_break", 0.8, 0.7, 0.5),),
                    "belief": Belief("t1", 0.60, 0.55, 0.35, 0.20, -0.10)})
    second = k.run(IntelligenceCase(**changed))
    assert first.progressive_cycle.phase in set(ReasoningPhase)
    assert second.progressive_cycle.phase == ReasoningPhase.REOPEN
    assert second.progressive_cycle.fragility_delta >= 0 or second.progressive_cycle.belief_delta <= 0
    assert len(k.progressive_memory.history("t1")) == 2
    assert first.progressive_cycle.lineage_hash != second.progressive_cycle.lineage_hash


def test_feedback_changes_effective_calibration_without_inventing_outcomes():
    loop = ProgressiveReasoningLoop()
    poor = FeedbackReport(10, 0, 0.36, 0.72, 0.40, (CalibrationBin(0, 1, 10, 0.7, 0.3, 0.4),))
    good = FeedbackReport(10, 0, 0.04, 0.06, 0.05, (CalibrationBin(0, 1, 10, 0.7, 0.7, 0.0),))
    belief = Belief("t2", 0.6, 0.8, 0.8, 0.0, 0.0)
    a = loop.run_cycle(cycle_id="poor", belief=belief, feedback_report=poor)
    b = loop.run_cycle(cycle_id="good", belief=belief, feedback_report=good)
    assert b.feedback_quality > a.feedback_quality
    assert b.assessment.calibration_score > a.assessment.calibration_score


def test_challenge_phase_has_discriminating_actions():
    loop = ProgressiveReasoningLoop()
    state = loop.run_cycle(
        cycle_id="challenge", belief=Belief("t3", 0.65, 0.75, 0.75),
        challenges=(Challenge("bear_case", 0.9, 0.8, 0.8),),
    )
    assert state.phase == ReasoningPhase.CHALLENGE
    assert "run_bear_case_and_evidence_falsification" in state.next_actions


def test_progressive_cycle_is_lineage_bound():
    loop = ProgressiveReasoningLoop()
    a = loop.run_cycle(cycle_id="x", belief=Belief("t4", 0.5, 0.6, 0.6))
    b = loop.run_cycle(cycle_id="y", belief=Belief("t4", 0.5, 0.6, 0.6), evidence_delta=0.2)
    assert a.lineage_hash != b.lineage_hash
