from pathlib import Path
from orion import __version__
from orion.data.store import SQLiteStore
from orion.data.historical_universe import HistoricalUniverseRegistry
from orion.data.universe_contract import UniverseMembership
from orion.learning.feedback import ForecastLedger
from orion.learning.outcome_resolver import ObservableOutcome
from orion.learning.advanced_diagnostics import AdvancedDiagnosticsEngine
from orion.portfolio.stress import PortfolioStressEngine
from orion.ops.release_audit import ReleaseAuditEngine
from orion.app.gateway import RuntimeGateway
from orion.app.server import OrionHTTPRequestHandler


def test_release_identity():
    assert __version__ == '190.0.0'
    assert 'v190' in Path('orion/app/gateway.py').read_text()
    assert 'v190' in Path('orion/ui/index.html').read_text()


def test_historical_universe_pit_and_snapshot():
    s=SQLiteStore(':memory:'); r=HistoricalUniverseRegistry(s)
    r.upsert(UniverseMembership('AAA','NIFTY50',True,'2020-01-01T00:00:00Z',None,'2020-01-02T00:00:00Z'),source_id='src',content_hash='a'*64)
    r.upsert(UniverseMembership('BBB','NIFTY50',True,'2025-01-01T00:00:00Z',None,'2025-01-02T00:00:00Z'),source_id='src',content_hash='b'*64)
    assert [x.security_id for x in r.memberships_as_of('2021-01-01T00:00:00Z')]==['AAA']
    assert [x.security_id for x in r.memberships_as_of('2026-01-01T00:00:00Z')]==['AAA','BBB']
    snap=r.snapshot('2021-01-01T00:00:00Z'); assert snap.lineage_hash and snap.coverage.supplied_counts['NIFTY50']==1
    s.close()


def test_historical_universe_rejects_invalid_interval():
    s=SQLiteStore(':memory:'); r=HistoricalUniverseRegistry(s)
    try: r.upsert(UniverseMembership('AAA','NIFTY50',True,'2025-01-02T00:00:00Z','2025-01-01T00:00:00Z','2025-01-02T00:00:00Z'),source_id='src',content_hash='c'*64)
    except ValueError as e: assert str(e)=='INVALID_MEMBERSHIP_INTERVAL'
    else: assert False
    s.close()


def test_advanced_diagnostics_segments_and_drift():
    from datetime import datetime,timedelta,timezone
    l=ForecastLedger(); base=datetime(2025,1,1,tzinfo=timezone.utc)
    for i in range(20):
        dt=(base+timedelta(days=i)).isoformat().replace('+00:00','Z'); end=(base+timedelta(days=i+7)).isoformat().replace('+00:00','Z')
        f=l.make_forecast(security_id='AAA',event_key=f'e{i}',decision_time=dt,horizon_end=end,probability=.9 if i<10 else .1,evidence_ids=(f'e{i}',),thesis_fingerprint='t',model_id='m',sector='IT',regime='R')
        l.issue(f); l.resolve(__import__('orion.learning.feedback',fromlist=['OutcomeRecord']).OutcomeRecord(f.forecast_id,i>=10,end,'src',(f'e{i}',),'d'*64),evaluation_time=end)
    d=AdvancedDiagnosticsEngine().analyze(l.forecasts(),l.outcomes(),min_sample=5)
    assert d.by_model[0].count==20 and d.calibration_drift.status in {'DRIFT_DETECTED','STABLE_OR_UNDETERMINED'}


def test_portfolio_stress_uses_supplied_correlations_only():
    r=PortfolioStressEngine().analyze({'A':.6,'B':.4},correlations={('A','B'):.9},shocks={'A':-.1,'B':-.2})
    assert len(r.clusters)==1 and set(r.clusters[0].members)=={'A','B'} and r.stressed_loss<0


def test_release_audit_clean_tree():
    a=ReleaseAuditEngine().audit('.', 'v181')
    assert a.passed and not a.forbidden_patterns and not a.live_trade_markers


def test_new_gateway_surfaces_exist():
    g=RuntimeGateway(); assert 'HISTORICAL_UNIVERSE_TIME_MACHINE' in g.capabilities()['architecture']
    assert 'calibration_drift' in g.advanced_learning_snapshot()
    g.control_plane.close()
