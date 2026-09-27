from datetime import datetime, timezone, timedelta
from pathlib import Path

from orion.data.universe_contract import InstitutionalUniverseContract, UniverseMembership
from orion.learning.feedback import ForecastLedger
from orion.learning.diagnostics import LearningDiagnosticsEngine
from orion.learning.model_registry import ChampionChallengerRegistry, ModelScore
from orion.learning.outcome_resolver import ObservableOutcome
from orion.institutional.operating_cycle import InstitutionalOperatingCycle
from orion.ops.time_machine import TimeMachine


def test_universe_contract_is_truth_bound():
    c=InstitutionalUniverseContract()
    r=c.coverage([UniverseMembership('A','NIFTY50'), UniverseMembership('A','NIFTY50')])
    assert r.target_size==450
    assert r.duplicate_memberships==1
    assert r.status=='PARTIAL'
    assert r.coverage_pct>0


def test_forecast_diagnostics_can_segment_by_sector_and_regime():
    now=datetime.now(timezone.utc); d=now+timedelta(days=2)
    l=ForecastLedger()
    f1=l.make_forecast(security_id='A',event_key='E1',decision_time=now.isoformat(),horizon_end=d.isoformat(),probability=.8,evidence_ids=('e1',),thesis_fingerprint='t1',sector='BANKING',regime='RISK_ON')
    f2=l.make_forecast(security_id='B',event_key='E2',decision_time=now.isoformat(),horizon_end=d.isoformat(),probability=.2,evidence_ids=('e2',),thesis_fingerprint='t2',sector='IT',regime='RISK_OFF')
    l.issue(f1); l.issue(f2)
    for f,occurred in ((f1,True),(f2,False)):
        l.resolve(__import__('orion.learning.feedback',fromlist=['OutcomeRecord']).OutcomeRecord(f.forecast_id,occurred,d.isoformat(),'src',f.evidence_ids,'a'*64), evaluation_time=(d+timedelta(hours=1)).isoformat())
    dgn=LearningDiagnosticsEngine().analyze(l.forecasts(),l.outcomes())
    assert dgn.by_sector and dgn.by_regime


def test_institutional_cycle_connects_feedback_replay_and_model():
    now=datetime.now(timezone.utc); end=now+timedelta(days=1)
    ledger=ForecastLedger(); f=ledger.make_forecast(security_id='A',event_key='E',decision_time=now.isoformat(),horizon_end=end.isoformat(),probability=.7,evidence_ids=('e',),thesis_fingerprint='t')
    ledger.issue(f)
    obs=[ObservableOutcome('E','A',True,end.isoformat(),'src','b'*64)]
    reg=ChampionChallengerRegistry()
    tm=TimeMachine()
    cycle=InstitutionalOperatingCycle(time_machine=tm)
    report=cycle.run(memberships=[UniverseMembership('A','NIFTY50')],ledger=ledger,observations=obs,evaluation_time=(end+timedelta(hours=1)).isoformat(),model_registry=reg,model_scores=[ModelScore('orion',1,.09,.1,.1)],nav_rows=[('1',100),('2',101)])
    assert report.resolved_forecasts==1
    assert report.performance and report.performance.total_return_pct==1.0
    assert report.replay.deterministic
