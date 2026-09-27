from datetime import datetime, timezone, timedelta
from pathlib import Path
from orion.runtime.control_plane import OrionControlPlane
from orion.runtime.data_plane import DataPlaneRegistry
from orion.data.providers import ProviderObservation, hash_payload
from orion.ops.time_machine import TimeMachine
from orion.execution.persistent import PersistentPaperExecutionBook
from orion.research.operating import ResearchOperatingCoordinator


def ts(days=0):
    return (datetime.now(timezone.utc)+timedelta(days=days)).isoformat().replace('+00:00','Z')


def test_provider_ingest_enforces_authorization_and_pit():
    r=DataPlaneRegistry(); r.register('p',configured=True,authenticated=True,capabilities=('market_price',),reason='READY')
    o=ProviderObservation('p','market_price','ABC',ts(-1),ts(-1),hash_payload(b'x'),False)
    assert r.ingest(o,decision_time=ts())['accepted'] is True
    future=ProviderObservation('p','market_price','ABC',ts(1),ts(1),hash_payload(b'y'),False)
    try: r.ingest(future,decision_time=ts())
    except ValueError as e: assert str(e)=='FUTURE_INFORMATION'
    else: assert False


def test_control_plane_persists_forecasts_models_and_replay(tmp_path):
    root=tmp_path/'state'; root.mkdir()
    cp=OrionControlPlane(state_path=root/'brain.sqlite',journal_path=root/'journal.jsonl',paper_path=root/'paper.sqlite')
    from orion.learning.feedback import ForecastLedger
    f=ForecastLedger.make_forecast(security_id='ABC',event_key='E',decision_time=ts(-3),horizon_end=ts(-2),probability=.7,evidence_ids=('e1',),thesis_fingerprint='t')
    cp.issue_forecast(f); cp.close()
    cp2=OrionControlPlane(state_path=root/'brain.sqlite',journal_path=root/'journal.jsonl',paper_path=root/'paper.sqlite')
    assert len(cp2.service.kernel.forecast_ledger.forecasts())==1
    assert cp2.service.kernel.model_registry.champion=='orion'
    cp2.close()


def test_paper_nav_persists(tmp_path):
    p=tmp_path/'paper.sqlite'; b=PersistentPaperExecutionBook(p)
    o=b.stage(security_id='ABC',target_weight=.1,current_weight=0,allowed=True,reason='TEST',lineage_hash='a'*64)
    b.fill(o.order_id,quantity=10,price=100,side='BUY',timestamp=ts())
    b.mark('ABC',110); row=b.record_nav(ts(),cash=1000); b.close()
    b2=PersistentPaperExecutionBook(p); assert b2.nav_history()[-1]['nav']==2100; b2.close()


def test_research_operating_plan_blocks_missing_sources():
    c=ResearchOperatingCoordinator(); p=c.plan(('ABC',),as_of=ts(),datasets={'ABC':{}})
    assert p.blocked_count==1 and p.ready_count==0 and p.coverage_pct==0


def test_time_machine_rejects_duplicate_cycle():
    t=TimeMachine(); t.record('c1',ts(),{'x':1})
    try: t.record('c1',ts(),{'x':2})
    except ValueError as e: assert str(e)=='DUPLICATE_CYCLE_ID'
    else: assert False

def test_ui_target_surfaces_and_explorer_endpoints():
    from orion.app.gateway import RuntimeGateway
    g=RuntimeGateway()
    plan=g.research_readiness('ABC',ts(),{})
    assert plan.readiness.coverage_pct==0 and not plan.readiness.ready
