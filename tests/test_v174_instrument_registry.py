from orion.data.store import SQLiteStore
from orion.acquisition.instrument_registry import InstrumentMapping, InstrumentMappingRegistry

ASOF='2026-01-10T00:00:00Z'

def test_mapping_register_and_pit_resolve(tmp_path):
    st=SQLiteStore(tmp_path/'db.sqlite')
    r=InstrumentMappingRegistry(st)
    r.register(InstrumentMapping.create(security_id='S1',provider='upstox',instrument_key='NSE_EQ|INE001A01036',effective_from='2025-01-01T00:00:00Z',available_time='2025-01-01T00:00:00Z',source_id='verified-map'))
    assert r.resolve('S1',provider='upstox',as_of=ASOF).instrument_key=='NSE_EQ|INE001A01036'
    assert r.resolve('S1',provider='upstox',as_of='2024-12-31T00:00:00Z') is None
    st.close()

def test_mapping_rejects_future_available_time(tmp_path):
    try:
        InstrumentMapping.create(security_id='S1',provider='upstox',instrument_key='NSE_EQ|X',effective_from='2025-01-01T00:00:00Z',available_time='2025-01-02T00:00:00Z',source_id='map')
    except ValueError as e:
        assert str(e)=='MAPPING_AVAILABLE_AFTER_EFFECTIVE'
    else: assert False

def test_readiness_is_explicit_about_missing_mappings(tmp_path):
    st=SQLiteStore(tmp_path/'db.sqlite'); r=InstrumentMappingRegistry(st)
    r.register(InstrumentMapping.create(security_id='S1',provider='upstox',instrument_key='NSE_EQ|X',effective_from='2025-01-01T00:00:00Z',available_time='2025-01-01T00:00:00Z',source_id='map'))
    out=r.readiness(['S1','S2'],provider='upstox',as_of=ASOF)
    assert out['status']=='PARTIAL' and out['mapped']==1 and out['blocked']==1
    assert out['rows'][1]['reason']=='NO_VERIFIED_INSTRUMENT_MAPPING'
    st.close()
