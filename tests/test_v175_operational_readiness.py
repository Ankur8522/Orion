from pathlib import Path
from orion.acquisition.instrument_registry import InstrumentMapping, InstrumentMappingRegistry
from orion.acquisition.operational_readiness import build_operational_readiness
from orion.data.store import SQLiteStore


def test_operational_readiness_requires_auth_mapping_and_observation(tmp_path):
    store=SQLiteStore(tmp_path/'a.sqlite')
    reg=InstrumentMappingRegistry(store)
    reg.register(InstrumentMapping.create(security_id='A',provider='upstox',instrument_key='NSE_EQ|A',effective_from='2026-01-01T00:00:00Z',available_time='2025-12-01T00:00:00Z',source_id='verified'))
    r=build_operational_readiness(security_ids=['A','B'],mapping_registry=reg,store=store,provider='upstox',as_of='2026-09-27T00:00:00Z',provider_authenticated=True)
    assert r.status=='PARTIAL'
    assert [x['status'] for x in r.rows]==['STALE_OR_MISSING','BLOCKED']
    store.close()


def test_operational_readiness_never_claims_ready_without_provider_auth(tmp_path):
    store=SQLiteStore(tmp_path/'a.sqlite')
    reg=InstrumentMappingRegistry(store)
    reg.register(InstrumentMapping.create(security_id='A',provider='upstox',instrument_key='NSE_EQ|A',effective_from='2026-01-01T00:00:00Z',available_time='2025-12-01T00:00:00Z',source_id='verified'))
    r=build_operational_readiness(security_ids=['A'],mapping_registry=reg,store=store,provider='upstox',as_of='2026-09-27T00:00:00Z',provider_authenticated=False)
    assert r.ready==0 and r.rows[0]['reason']=='PROVIDER_NOT_AUTHENTICATED'
    store.close()
