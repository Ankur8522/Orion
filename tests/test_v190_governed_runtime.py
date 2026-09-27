from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from orion.data.coverage_contract import CoverageAssessment
from orion.data.world_snapshot import WorldSnapshot
from orion.intelligence.decision_world import DecisionWorldBuilder
from orion.intelligence.decision_pipeline import DecisionIntelligenceEngine
from orion.institutional.operating_cycle import InstitutionalOperatingCycle
from orion.learning.feedback import ForecastLedger
from orion.learning.model_registry import ChampionChallengerRegistry, ModelLifecycle, ModelScore
from orion.learning.outcome_resolver import ObservableOutcome
from orion.learning.specialist_models import ChronologicalLogisticSpecialist, TrainingExample
from orion.learning.forecast_distribution import EmpiricalForecastDistribution
from orion.research.evidence_graph import EvidenceGraph
from orion.ops.time_machine import TimeMachine
from orion.data.universe_contract import UniverseMembership


def test_decision_world_seals_feature_mapping():
    world = DecisionWorldBuilder().build(
        WorldSnapshot('ABC', '2024-01-01T00:00:00Z', True, (), 'ws'),
        CoverageAssessment(('x',), 1, 1.0, (), 'cov'),
        EvidenceGraph((), (), (), 'ev'),
        features={'quality': 0.8},
    )
    with pytest.raises(TypeError):
        world.features['quality'] = 0.9


def test_model_lifecycle_is_persistent_and_governed(tmp_path: Path):
    db = tmp_path / 'models.sqlite'
    r = ChampionChallengerRegistry(path=db)
    r.register('m1')
    r.transition('m1', ModelLifecycle.VALIDATION, reason='VALIDATED')
    r.transition('m1', ModelLifecycle.CHALLENGER, reason='SHADOW_PASS')
    r.transition('m1', ModelLifecycle.CHAMPION, reason='SELECTION_GATE')
    assert r.lifecycle('m1').state is ModelLifecycle.CHAMPION
    r.close()
    r2 = ChampionChallengerRegistry(path=db)
    assert r2.lifecycle('m1').state is ModelLifecycle.CHAMPION
    r2.close()


def test_model_lifecycle_rejects_invalid_transition():
    r = ChampionChallengerRegistry()
    r.register('m1')
    with pytest.raises(ValueError, match='INVALID_MODEL_TRANSITION'):
        r.transition('m1', ModelLifecycle.CHAMPION, reason='SKIP_GATES')
    r.close()


def test_operating_cycle_executes_decisionworld_intelligence(tmp_path: Path):
    ws = WorldSnapshot('ABC', '2024-02-01T00:00:00Z', True, (), 'ws')
    cov = CoverageAssessment(('x',), 1, 1.0, (), 'cov')
    ev = EvidenceGraph((), (), (), 'ev')
    world = DecisionWorldBuilder().build(ws, cov, ev, features={'quality': 0.8})
    rows = [TrainingExample((datetime(2024,1,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat().replace('+00:00','Z'), {'quality': i/19}, int(i > 9), 'BULL') for i in range(20)]
    model = ChronologicalLogisticSpecialist('fundamental', ('quality',), epochs=100)
    model.fit(rows)
    ledger = ForecastLedger()
    registry = ChampionChallengerRegistry(path=tmp_path/'m.sqlite')
    member = UniverseMembership('ABC', 'NIFTY50', '2024-01-01T00:00:00Z', '2024-12-31T00:00:00Z')
    report = InstitutionalOperatingCycle(time_machine=TimeMachine()).run(
        memberships=[member], ledger=ledger, observations=[], evaluation_time='2024-02-01T00:00:00Z',
        model_registry=registry, decision_world=world, specialist_models={'fundamental': model},
    )
    assert report.intelligence is not None
    assert report.intelligence.status in {'READY', 'INSUFFICIENT_TRAINED_SPECIALISTS'}
    assert report.replay.deterministic
    registry.close()


def test_outcome_metrics_survive_resolution():
    ledger = ForecastLedger()
    f = ledger.make_forecast(
        security_id='ABC', event_key='20D', decision_time='2024-01-01T00:00:00Z',
        horizon_end='2024-01-21T00:00:00Z', probability=.7, evidence_ids=('e1',),
        thesis_fingerprint='t', expected_return=.08, horizon_days=20,
    )
    ledger.issue(f)
    o = ObservableOutcome('20D', 'ABC', True, '2024-01-22T00:00:00Z', 'prices', 'a'*64,
                          return_pct=.11, max_drawdown=-.04, mae=-.02, mfe=.13, time_to_target_days=16)
    from orion.learning.outcome_resolver import ForecastOutcomeResolver
    report = ForecastOutcomeResolver().resolve(ledger, [o], evaluation_time='2024-01-23T00:00:00Z')
    assert report.resolved == 1
    stored = ledger.outcomes()[0]
    assert stored.return_pct == .11 and stored.max_drawdown == -.04 and stored.mfe == .13


def test_empirical_distribution_can_consume_only_observed_ledger_returns():
    ledger = ForecastLedger()
    f1 = ledger.make_forecast(security_id='A', event_key='20D', decision_time='2024-01-01T00:00:00Z', horizon_end='2024-01-21T00:00:00Z', probability=.6, evidence_ids=('e1',), thesis_fingerprint='t', horizon_days=20)
    f2 = ledger.make_forecast(security_id='B', event_key='20D', decision_time='2024-01-01T00:00:00Z', horizon_end='2024-01-21T00:00:00Z', probability=.4, evidence_ids=('e2',), thesis_fingerprint='t', horizon_days=20)
    ledger.issue(f1); ledger.issue(f2)
    from orion.learning.feedback import OutcomeRecord
    ledger.resolve(OutcomeRecord(f1.forecast_id, True, '2024-01-22T00:00:00Z', 'p', ('e1',), 'a'*64, return_pct=.10), evaluation_time='2024-01-23T00:00:00Z')
    d=EmpiricalForecastDistribution().build_from_ledger(ledger.forecasts(), ledger.outcomes(), horizon_days=20)
    assert d.status == 'INSUFFICIENT_EVIDENCE'
    assert d.observations == 1
