import json
import pytest
from orion.data.domain_registry import DatasetCatalog, DatasetDomain
from orion.data.world_snapshot import WorldSnapshot
from orion.decision.trade_ensemble import SpecialistOutput, TradeIntelligenceEnsemble
from orion.providers.zerodha_readonly import ZerodhaReadOnlyClient


def test_catalog_exposes_real_data_domains_without_claiming_availability():
    c=DatasetCatalog()
    assert c.domain('ohlcv') == DatasetDomain.MARKET
    assert c.domain('financial_statements') == DatasetDomain.FUNDAMENTAL
    assert c.domain('earnings_estimates') == DatasetDomain.ESTIMATES
    assert 'news_evidence' in c.names()


def test_world_snapshot_rejects_future_information():
    s=WorldSnapshot.build('ABC','2026-01-10T10:00:00Z',observations={
        'ohlcv':[{'available_time':'2026-01-09T10:00:00Z','event_time':'2026-01-09T09:15:00Z','payload_hash':'a'*64},
                 {'available_time':'2026-01-11T10:00:00Z','event_time':'2026-01-11T09:15:00Z','payload_hash':'b'*64}]})
    assert not s.usable
    assert len(s.observations['ohlcv']) == 1
    assert 'ohlcv:FUTURE_OBSERVATION' in s.blockers


def test_ensemble_refuses_untrained_probability():
    out=TradeIntelligenceEnsemble(min_specialists=2).combine([
        SpecialistOutput('fundamental',0.8,100,'f1',False),
        SpecialistOutput('technical',0.7,100,'t1',False),
    ])
    assert out.probability is None
    assert out.status == 'INSUFFICIENT_TRAINED_SPECIALISTS'


def test_ensemble_requires_two_trained_specialists_and_tracks_disagreement():
    out=TradeIntelligenceEnsemble(weights={'fundamental':2,'technical':1}).combine([
        SpecialistOutput('fundamental',0.8,100,'f1',True),
        SpecialistOutput('technical',0.6,100,'t1',True),
    ])
    assert out.status == 'READY'
    assert out.probability == pytest.approx((2*0.8+0.6)/3)
    assert out.disagreement is not None and out.disagreement > 0
    assert out.lineage_hash


def test_zerodha_client_never_has_order_methods():
    c=ZerodhaReadOnlyClient(api_key='x',access_token='y')
    assert c.configured
    assert not hasattr(c,'place_order')
    assert not hasattr(c,'modify_order')
    assert not hasattr(c,'cancel_order')

def test_provider_market_acquirer_blocks_unconfigured_provider():
    from orion.acquisition.provider_market import ProviderMarketAcquirer, ProviderMarketJob
    from orion.data.store import SQLiteStore
    from orion.providers.zerodha_readonly import ZerodhaReadOnlyClient
    store=SQLiteStore(':memory:')
    client=ZerodhaReadOnlyClient(api_key='',access_token='')
    acq=ProviderMarketAcquirer({'zerodha':client},store)
    out=acq.acquire(ProviderMarketJob('j1','zerodha','ABC','123','day','2026-01-01','2026-01-05','2026-01-06T00:00:00Z'))
    assert out['state']=='NOT_CONFIGURED'
    store.close()
