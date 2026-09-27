from orion.research.factory import ResearchFactory, REQUIRED_DATASETS
from orion.portfolio.risk_engine import PortfolioRiskEngine
from orion.learning.diagnostics import LearningDiagnosticsEngine
from orion.learning.feedback import ForecastLedger, OutcomeRecord
from orion.runtime.operating_metrics import OperatingScorecard
from datetime import datetime, timezone, timedelta
from hashlib import sha256


def test_research_factory_blocks_missing_sources():
    r=ResearchFactory().readiness('ABC','2026-09-27T00:00:00Z',{})
    assert not r.ready and r.coverage_pct==0
    assert len(r.requirements)==len(REQUIRED_DATASETS)


def test_research_factory_ready_only_with_sources():
    d={k:{'available':True,'source_ids':[k+'-src']} for k in REQUIRED_DATASETS}
    r=ResearchFactory().plan('ABC','2026-09-27T00:00:00Z',d,1.0)
    assert r.readiness.ready and 'BUILD_RESEARCH_DOSSIER' in r.next_actions


def test_risk_engine_is_deterministic():
    x=PortfolioRiskEngine().assess([0.01,-0.02,0.015,-0.01],{'A':0.6,'B':0.4}, {'A':'BANK','B':'IT'})
    assert x.var95>=0 and 0<=x.concentration_hhi<=1 and len(x.lineage_hash)==64


def test_learning_diagnostics_flags_bias():
    ledger=ForecastLedger(); now=datetime.now(timezone.utc)
    for i in range(4):
        f=ledger.make_forecast(security_id='A',event_key=str(i),decision_time=now.isoformat().replace('+00:00','Z'),horizon_end=(now+timedelta(days=2)).isoformat().replace('+00:00','Z'),probability=.9,evidence_ids=(f'e{i}',),thesis_fingerprint='t')
        ledger.issue(f)
        o=OutcomeRecord(f.forecast_id,False,(now+timedelta(days=3)).isoformat().replace('+00:00','Z'),'src',(f'e{i}',),sha256(str(i).encode()).hexdigest())
        ledger.resolve(o,evaluation_time=(now+timedelta(days=4)).isoformat().replace('+00:00','Z'))
    d=LearningDiagnosticsEngine().analyze(ledger.forecasts(),ledger.outcomes())
    assert d.false_positive_rate==1.0 and 'HIGH_FALSE_POSITIVE_RATE' in d.recurring_failure_flags


def test_operating_scorecard_penalizes_blockers():
    s=OperatingScorecard().score(data_readiness=80,brain_readiness=90,portfolio_readiness=80,ui_readiness=90,blockers={'REAL_DATA_PROVIDER':True})
    assert s.architecture==85 and s.overall==82
