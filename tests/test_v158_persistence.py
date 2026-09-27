from datetime import datetime, timezone, timedelta
from pathlib import Path
from orion.learning.feedback import ForecastLedger
from orion.learning.persistence import PersistentForecastLedger
from orion.learning.model_registry import ChampionChallengerRegistry, ModelScore
from orion.ops.time_machine import TimeMachine

def ts(days=0): return (datetime.now(timezone.utc)+timedelta(days=days)).isoformat()

def test_forecast_ledger_survives_restart(tmp_path):
    p=tmp_path/'f.db'; l=PersistentForecastLedger(p); f=l.make_forecast(security_id='A',event_key='E',decision_time=ts(-2),horizon_end=ts(-1),probability=.6,evidence_ids=('e',),thesis_fingerprint='t'); l.issue(f); l.close()
    l2=PersistentForecastLedger(p); assert len(l2.forecasts())==1

def test_model_registry_survives_restart(tmp_path):
    p=tmp_path/'m.db'; r=ChampionChallengerRegistry('a',p); r.update([ModelScore('b',10,.1,.2,.1)]); r.close(); r2=ChampionChallengerRegistry('a',p); assert r2.champion=='b'

def test_time_machine_survives_restart(tmp_path):
    p=tmp_path/'tm.jsonl'; t=TimeMachine(p); t.record('1','t',{'x':1}); t.record('2','t2',{'x':2}); r=TimeMachine(p).replay(); assert r.final_state=={'x':2}
