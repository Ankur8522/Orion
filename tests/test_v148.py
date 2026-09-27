from pathlib import Path
import tempfile
import pytest
from orion.learning.feedback import ForecastLedger, OutcomeRecord
H='a'*64

def make():
    return ForecastLedger.make_forecast(security_id='NSE_EQ|X',event_key='RETURN_POSITIVE_30D',
        decision_time='2026-09-01T10:00:00Z',horizon_end='2026-10-01T10:00:00Z',
        probability=.75,evidence_ids=('e1',),thesis_fingerprint='t1')

def test_forecast_requires_valid_probability_and_evidence():
    with pytest.raises(ValueError): ForecastLedger.make_forecast(security_id='X',event_key='E',
        decision_time='2026-09-01T00:00:00Z',horizon_end='2026-10-01T00:00:00Z',
        probability=1.1,evidence_ids=('e1',),thesis_fingerprint='t')
    with pytest.raises(ValueError): ForecastLedger.make_forecast(security_id='X',event_key='E',
        decision_time='2026-09-01T00:00:00Z',horizon_end='2026-10-01T00:00:00Z',
        probability=.5,evidence_ids=(),thesis_fingerprint='t')

def test_outcome_before_horizon_is_blocked():
    l=ForecastLedger(); f=make(); l.issue(f)
    o=OutcomeRecord(f.forecast_id,True,'2026-09-20T00:00:00Z','nse',('e2',),H)
    with pytest.raises(ValueError,match='OUTCOME_BEFORE_HORIZON'): l.resolve(o,evaluation_time='2026-10-02T00:00:00Z')

def test_future_outcome_is_blocked():
    l=ForecastLedger(); f=make(); l.issue(f)
    o=OutcomeRecord(f.forecast_id,True,'2026-10-03T00:00:00Z','nse',('e2',),H)
    with pytest.raises(ValueError,match='FUTURE_OUTCOME'): l.resolve(o,evaluation_time='2026-10-02T00:00:00Z')

def test_scoring_and_calibration_are_deterministic():
    l=ForecastLedger(); f1=make()
    f2=ForecastLedger.make_forecast(security_id='NSE_EQ|Y',event_key='E',
        decision_time='2026-09-01T10:00:00Z',horizon_end='2026-10-01T10:00:00Z',
        probability=.25,evidence_ids=('e2',),thesis_fingerprint='t2')
    l.issue(f1); l.issue(f2)
    l.resolve(OutcomeRecord(f1.forecast_id,True,'2026-10-01T10:01:00Z','nse',('o1',),H),evaluation_time='2026-10-02T00:00:00Z')
    l.resolve(OutcomeRecord(f2.forecast_id,False,'2026-10-01T10:02:00Z','nse',('o2',),H),evaluation_time='2026-10-02T00:00:00Z')
    r=l.report()
    assert r.resolved==2 and r.brier==0.0625 and r.log_loss < .30 and r.calibration_error==.25

def test_execution_persists_feedback():
    from orion.data.store import SQLiteStore
    from orion.execution.vertical_slice import ResearchExecution
    with tempfile.TemporaryDirectory() as d:
        s=SQLiteStore(str(Path(d)/'o.db')); e=ResearchExecution(s)
        f=make(); e.record_forecast(f)
        e.resolve_forecast(OutcomeRecord(f.forecast_id,False,'2026-10-01T10:01:00Z','nse',('o',),H),evaluation_time='2026-10-02T00:00:00Z')
        assert len(s.forecasts_for('NSE_EQ|X'))==1 and len(s.forecast_outcomes_for((f.forecast_id,)))==1

def test_feedback_survives_runtime_restart():
    from orion.data.store import SQLiteStore
    from orion.execution.vertical_slice import ResearchExecution
    with tempfile.TemporaryDirectory() as d:
        db=str(Path(d)/'o.db')
        s1=SQLiteStore(db); e1=ResearchExecution(s1)
        f=make(); e1.record_forecast(f)
        e1.resolve_forecast(OutcomeRecord(f.forecast_id,True,'2026-10-01T10:01:00Z','nse',('o',),H),evaluation_time='2026-10-02T00:00:00Z')
        s1.close()
        s2=SQLiteStore(db); e2=ResearchExecution(s2)
        assert e2.feedback.report().resolved==1 and e2.feedback.report().brier==.0625
