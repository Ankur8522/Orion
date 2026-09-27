import pytest
from orion.brain.progressive import (
    Belief, Challenge, MarketState, ProgressiveDecisionBrain, Regime
)


def test_regime_classification_is_bounded_and_deterministic():
    brain = ProgressiveDecisionBrain()
    assert brain.classify_regime(MarketState(.1, .8, .8)) == Regime.RISK_ON
    assert brain.classify_regime(MarketState(.9, -.7, -.7, .5)) == Regime.RISK_OFF
    assert brain.classify_regime(MarketState(.4, .0, .02)) == Regime.NEUTRAL


def test_adversarial_challenge_reduces_robustness():
    brain = ProgressiveDecisionBrain()
    base = brain.assess(Belief("t1", .7, .8, .8), scenario_score=.8, calibration_score=.8)
    challenged = brain.assess(
        Belief("t1", .7, .8, .8),
        (Challenge("margin pressure", .9, .8, .7),),
        scenario_score=.8, calibration_score=.8,
    )
    assert challenged.robustness < base.robustness
    assert challenged.fragility > base.fragility
    assert "resolve_adversarial_challenges" in challenged.next_checks


def test_low_calibration_drives_learning_loop():
    brain = ProgressiveDecisionBrain()
    a = brain.assess(Belief("t1", .6, .7, .7), scenario_score=.7, calibration_score=.8)
    b = brain.assess(Belief("t1", .6, .7, .7), scenario_score=.7, calibration_score=.2)
    assert b.robustness < a.robustness
    assert "collect_more_outcome_feedback" in b.next_checks


def test_compare_is_explainable():
    brain = ProgressiveDecisionBrain()
    a = brain.assess(Belief("t1", .5, .5, .5))
    b = brain.assess(Belief("t1", .8, .8, .8), scenario_score=.9, calibration_score=.9)
    d = brain.compare(a, b)
    assert d["belief_delta"] > 0
    assert d["robustness_delta"] > 0


def test_invalid_signals_are_rejected():
    with pytest.raises(ValueError, match="BOUNDED"):
        ProgressiveDecisionBrain().assess(Belief("t1", 2, .5, .5))


def test_api_exposes_progressive_brain():
    from orion.app.api import API, RequestContext
    api = API(rate_limit=100)
    ctx = RequestContext("u1", "r1", "analyst")
    result = api.progressive_assessment(ctx, Belief("t1", .6, .7, .8))
    assert result.thesis_id == "t1"
    assert len(result.lineage_hash) == 64
