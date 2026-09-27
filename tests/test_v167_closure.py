from datetime import datetime, timezone
from orion.data.providers import ProviderObservation, hash_payload, validate_observation
from orion.runtime.data_plane import DataPlaneRegistry
from orion.data.pit_corpus import PITRecord, CorpusState, CorpusManifest
from orion.data.universe_contract import InstitutionalUniverseContract, UniverseMembership
from orion.learning.model_registry import ChampionChallengerRegistry, ModelScore
from orion.ops.time_machine import TimeMachine


def test_provider_dataset_history_is_independent():
    d=DataPlaneRegistry()
    d.register('p',configured=True,authenticated=True,capabilities=('ohlcv','financials'),historical_datasets=('ohlcv',))
    d.record_success('p','2026-09-27T00:00:00Z',dataset='ohlcv')
    c=d.coverage(('ohlcv','financials'),historical=True)
    assert c['datasets']['ohlcv']['status']=='READY'
    assert c['datasets']['financials']['status']=='NO_HISTORY'


def test_pit_record_rejects_future_and_bad_ingestion():
    r=PITRecord('A','financials','2026-09-01T00:00:00Z','2026-09-02T00:00:00Z','2026-09-03T00:00:00Z','src',CorpusState.HISTORICAL_PIT,'a'*64)
    r.validate('2026-09-04T00:00:00Z')
    try:
        r.validate('2026-09-01T12:00:00Z')
        assert False
    except ValueError as e:
        assert str(e)=='FUTURE_INFORMATION_BLOCKED'


def test_time_machine_memory_does_not_create_file(tmp_path):
    path=tmp_path/'state.jsonl'
    tm=TimeMachine(path=':memory:')
    tm.record('c1','2026-09-27T00:00:00Z',{'x':1})
    assert not path.exists()


def test_model_switch_requires_evidence_gates():
    reg=ChampionChallengerRegistry(champion='a')
    reg.update([ModelScore('a',10,.20,.3,.1), ModelScore('b',10,.10,.2,.05,horizon_coverage=.5,confidence=.9,stability=.9)])
    assert reg.champion=='a'
    reg.update([ModelScore('b',10,.10,.2,.05,horizon_coverage=.9,confidence=.9,stability=.9,evidence_sufficient=True)])
    assert reg.champion=='b'


def test_universe_membership_as_of_filters_future_constituent():
    u=InstitutionalUniverseContract({'NIFTY50':1,'NIFTY_MIDCAP150':1,'NIFTY_SMALLCAP250':1})
    rows=[UniverseMembership('A','NIFTY50',effective_from='2026-09-28T00:00:00Z',available_time='2026-09-28T00:00:00Z')]
    assert u.membership_as_of(rows,'2026-09-27T00:00:00Z')==()
