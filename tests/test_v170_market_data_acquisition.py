from datetime import datetime, timezone
import json, sqlite3
from pathlib import Path

from orion.acquisition.market_data import MarketDataJob, UpstoxMarketDataAcquirer
from orion.data.store import SQLiteStore
from orion.providers.upstox_readonly import ReadOnlyFetchResult
from orion.providers.upstox import RawEnvelope

class FakeClient:
    def __init__(self, future=False): self.future=future
    def historical_candles(self, instrument_key, unit, interval, to_date, from_date):
        available='2026-09-27T01:00:00Z' if self.future else '2026-09-26T10:00:00Z'
        raw=b'{"data":{"candles":[]}}'
        env=RawEnvelope.create('ohlcv',instrument_key,raw,event_time='2026-09-25T00:00:00Z',available_time=available)
        return ReadOnlyFetchResult(env, ({'event_time':'2026-09-25T00:00:00Z','close':1.0},))

def job(decision='2026-09-26T12:00:00Z'):
    return MarketDataJob('j1','NSE_EQ|INE002A01018','NSE_EQ|INE002A01018','days',1,'2026-09-26','2026-09-01',decision)

def test_provider_payload_is_persisted_as_pit_observation(tmp_path):
    s=SQLiteStore(tmp_path/'o.db')
    r=UpstoxMarketDataAcquirer(FakeClient(),s).acquire(job())
    assert r.state=='PROMOTED' and r.rows==1 and r.payload_hash
    rows=s.pit('NSE_EQ|INE002A01018','ohlcv','2026-09-26T12:00:00Z')
    assert len(rows)==1 and rows[0]['source_id']=='upstox'
    assert len(s.db.execute('select * from source_captures').fetchall())==1
    s.close()

def test_future_provider_payload_is_blocked_and_not_persisted(tmp_path):
    s=SQLiteStore(tmp_path/'o.db')
    r=UpstoxMarketDataAcquirer(FakeClient(future=True),s).acquire(job())
    assert r.state=='BLOCKED' and r.error=='FUTURE_INFORMATION'
    assert s.db.execute('select count(*) from observations').fetchone()[0]==0
    s.close()

def test_persisted_observation_survives_restart(tmp_path):
    path=tmp_path/'restart.db'
    s=SQLiteStore(path)
    UpstoxMarketDataAcquirer(FakeClient(),s).acquire(job())
    s.close()
    s2=SQLiteStore(path)
    assert len(s2.pit('NSE_EQ|INE002A01018','ohlcv','2026-09-26T12:00:00Z'))==1
    s2.close()
