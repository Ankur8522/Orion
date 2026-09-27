from datetime import datetime, timezone, timedelta

from orion.data.universe_contract import InstitutionalUniverseContract, UniverseMembership
from orion.research.operating import ResearchOperatingCoordinator
from orion.validation.empirical import EmpiricalValidationLab
from orion.learning.feedback import ForecastLedger, OutcomeRecord
from orion.quant.safe_backtest import PITBacktest


def test_historical_universe_membership_is_point_in_time_safe():
    c = InstitutionalUniverseContract()
    memberships = [
        UniverseMembership('A','NIFTY50',effective_from='2026-09-01T00:00:00Z',available_time='2026-09-01T01:00:00Z'),
        UniverseMembership('B','NIFTY50',effective_from='2026-10-01T00:00:00Z',available_time='2026-10-01T01:00:00Z'),
    ]
    before = c.coverage(memberships, as_of='2026-09-15T00:00:00Z')
    after = c.coverage(memberships, as_of='2026-10-15T00:00:00Z')
    assert before.supplied_counts['NIFTY50'] == 1
    assert after.supplied_counts['NIFTY50'] == 2


def test_research_operating_plan_derives_information_value_priority():
    c = ResearchOperatingCoordinator()
    datasets = {
        'LOW': {},
        'HIGH': {'thesis_change': 1.0, 'event_urgency': 1.0, 'market_signal': 1.0},
    }
    plan = c.plan(['LOW','HIGH'], as_of='2026-09-27T00:00:00Z', datasets=datasets)
    assert plan.plans[0].security_id == 'HIGH'
    assert plan.plans[0].priority > plan.plans[1].priority


def test_empirical_validation_rejects_future_backtest_observations():
    lab = EmpiricalValidationLab(PITBacktest())
    report = lab.run(
        backtest_rows=[
            {'available_time':'2026-09-28T00:00:00Z','return':0.1},
            {'available_time':'2026-09-26T00:00:00Z','return':0.05},
        ],
        decision_time='2026-09-27T00:00:00Z',
    )
    assert report.backtest.rejected_lookahead == 1
    assert report.backtest.observations_used == 1
    assert report.status == 'READY'
