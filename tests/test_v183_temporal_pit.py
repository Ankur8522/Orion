import pytest
from orion.data.temporal import TemporalLineage
from orion.data.providers import ProviderObservation, validate_observation
from orion.data.pit import Observation, PITStore
from orion.data.corporate_actions import CorporateActionLedger

T='2026-01-01T10:00:00Z'; T2='2026-01-01T10:01:00Z'; T3='2026-01-01T10:02:00Z'

def test_temporal_lineage_orders_source_available_ingestion():
    assert TemporalLineage(T,T,T2,T3).validate()
    with pytest.raises(ValueError, match='INGESTION_BEFORE_AVAILABLE_TIME'):
        TemporalLineage(T,T,T3,T2).validate()

def test_provider_observation_rejects_ingestion_before_available():
    o=ProviderObservation('p','ohlcv','ABC',T,T3,'a'*64,False,ingestion_time=T2)
    with pytest.raises(ValueError, match='INGESTION_BEFORE_AVAILABLE_TIME'):
        validate_observation(o)

def test_pit_store_filters_by_available_not_ingestion():
    store=PITStore(); store.append(Observation('ABC',T,T2,10.0,'src',source_time=T,ingestion_time=T3))
    assert len(store.as_of('ABC',T2)) == 1
    assert len(store.as_of('ABC',T)) == 0

def test_corporate_action_temporal_lineage():
    row={'security_id':'ABC','action_id':'a1','action_type':'DIVIDEND','effective_time':T,'available_time':T2,'source_id':'src','content_hash':'b'*64,'source_time':T,'ingestion_time':T3}
    a=CorporateActionLedger().normalize(row)
    assert a.ingestion_time==T3
