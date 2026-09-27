from datetime import datetime, timezone, timedelta
import json
import os

from orion.data.providers import ProviderObservation, hash_payload
from orion.runtime.data_plane import DataPlaneRegistry
from orion.research.factory import ResearchFactory, REQUIRED_DATASETS
from orion.validation.empirical import EmpiricalValidationLab
from orion.learning.feedback import ForecastLedger, OutcomeRecord
from orion.portfolio.performance import PortfolioPerformanceEngine


def test_provider_coverage_is_dataset_specific_and_supports_freshness():
    d=DataPlaneRegistry()
    d.register('market', configured=True, authenticated=True, capabilities=('ohlcv',), last_success_at='2026-09-27T00:00:00Z', stale_after_seconds=3600)
    c=d.coverage(('ohlcv','financials'))
    assert c['datasets']['ohlcv']['status']=='READY'
    assert c['datasets']['financials']['status']=='NOT_CONFIGURED'
    assert d.freshness('2026-09-27T00:30:00Z')[0]['status']=='READY'
    assert d.freshness('2026-09-27T02:00:00Z')[0]['status']=='STALE'
    obs=ProviderObservation('market','ohlcv','ABC','2026-09-27T00:10:00Z','2026-09-27T00:11:00Z',hash_payload(b'abc'),False)
    d.ingest(obs)
    assert d.statuses()[0].last_success_at=='2026-09-27T00:11:00Z'


def test_research_factory_allows_conditionally_not_applicable_dataset():
    f=ResearchFactory()
    datasets={k:{'available':True,'source_ids':['src']} for k in REQUIRED_DATASETS}
    # Use module-level catalog via an explicit conditional field.
    datasets['order_book']={'applicable':False}
    r=f.readiness('ABC','2026-09-27T00:00:00Z',datasets)
    assert r.requirements[[x.dataset for x in r.requirements].index('order_book')].applicable is False


def test_empirical_validation_uses_supplied_ledger_without_fabricating_history():
    l=ForecastLedger(); now='2026-09-27T00:00:00Z'; end='2026-09-29T00:00:00Z'
    f=l.make_forecast(security_id='A',event_key='E',decision_time=now,horizon_end=end,probability=.8,evidence_ids=('e',),thesis_fingerprint='t',sector='BANKING',regime='RISK_ON')
    l.issue(f); l.resolve(OutcomeRecord(f.forecast_id,True,end,'src',('e',),'a'*64), evaluation_time='2026-09-29T01:00:00Z')
    r=EmpiricalValidationLab().run(decision_time=now, ledger=l)
    assert r.status=='READY'
    assert r.diagnostics['resolved']==1
    assert r.forecast_report['resolved']==1


def test_performance_exposes_sortino_only_from_real_nav_history():
    s=PortfolioPerformanceEngine().summarize([('1',100),('2',102),('3',98),('4',105)])
    assert s.observations==4
    assert s.sortino is not None
