from datetime import datetime, timezone, timedelta
from orion.learning.feedback import ForecastLedger
from orion.learning.outcome_resolver import ForecastOutcomeResolver, ObservableOutcome
from orion.learning.model_registry import ChampionChallengerRegistry, ModelScore
from orion.portfolio.attribution import PortfolioAttributionEngine
from orion.ops.time_machine import TimeMachine
from orion.runtime.autonomous import AutonomousRuntime

def ts(days=0): return (datetime.now(timezone.utc)+timedelta(days=days)).isoformat()

def test_outcome_resolution_respects_horizon():
    l=ForecastLedger(); f=l.make_forecast(security_id='A',event_key='E',decision_time=ts(),horizon_end=ts(1),probability=.7,evidence_ids=('e1',),thesis_fingerprint='t')
    l.issue(f); r=ForecastOutcomeResolver().resolve(l,[ObservableOutcome('E','A',True,ts(2),'src','a'*64)],evaluation_time=ts(2))
    assert r.resolved==1 and l.report().resolved==1

def test_champion_challenger_is_bounded():
    r=ChampionChallengerRegistry('a'); d=r.update([ModelScore('a',10,.30,.5,.2),ModelScore('b',10,.20,.4,.1)])
    assert d.champion=='b'

def test_attribution_reconciles():
    a=PortfolioAttributionEngine().attribute([('A',.6,.10),('B',.4,-.05)])
    assert abs(a.total_return_pct-.04)<1e-9 and a.residual_pct==0

def test_time_machine_integrity_and_replay():
    tm=TimeMachine(); tm.record('1','t1',{'x':1}); tm.record('2','t2',{'x':2}); r=tm.replay(); assert r.final_state=={'x':2} and r.deterministic

def test_autonomous_runtime_closes_loop():
    l=ForecastLedger(); f=l.make_forecast(security_id='A',event_key='E',decision_time=ts(-2),horizon_end=ts(-1),probability=.5,evidence_ids=('e',),thesis_fingerprint='t'); l.issue(f)
    rt=AutonomousRuntime(); out=rt.cycle(ledger=l,observations=[ObservableOutcome('E','A',True,ts(-1),'s','b'*64)],evaluation_time=ts(),model_scores=[ModelScore('orion',5,.2,.3,.1)],attribution_rows=[('A',1,.03)],state={'regime':'NEUTRAL'})
    assert out.resolved_forecasts==1 and out.model_decision.champion=='orion' and out.replay.final_state['regime']=='NEUTRAL'

def test_universe_chunking():
    rt=AutonomousRuntime(); keys=rt.enqueue_universe([f'S{i}' for i in range(105)],chunk_size=50); assert len(keys)==3
