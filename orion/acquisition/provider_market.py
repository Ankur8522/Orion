from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Protocol, Sequence
import json

from ..data.store import SQLiteStore
from ..data.time import parse_utc

@dataclass(frozen=True)
class CanonicalMarketFetch:
    provider: str
    security_id: str
    instrument_key: str
    rows: tuple[dict, ...]
    payload_hash: str
    event_time: str
    available_time: str
    raw_payload: bytes

class ReadOnlyMarketProvider(Protocol):
    @property
    def configured(self) -> bool: ...
    def historical_canonical(self, *, security_id: str, instrument_key: str, interval: str, from_date: str, to_date: str) -> CanonicalMarketFetch: ...

@dataclass(frozen=True)
class ProviderMarketJob:
    job_id: str
    provider: str
    security_id: str
    instrument_key: str
    interval: str
    from_date: str
    to_date: str
    decision_time: str

class ProviderMarketAcquirer:
    """Provider-neutral market ingestion boundary.

    The provider is responsible only for authenticated read-only retrieval and
    normalization; this layer enforces the ORION PIT boundary and durable storage.
    """
    def __init__(self, providers: dict[str, ReadOnlyMarketProvider], store: SQLiteStore):
        self.providers=dict(providers); self.store=store

    def acquire(self, job: ProviderMarketJob) -> dict:
        provider=self.providers.get(job.provider)
        if provider is None: return {'job_id':job.job_id,'state':'UNSUPPORTED_PROVIDER','rows':0,'error':'NO_PROVIDER_ADAPTER'}
        if not provider.configured: return {'job_id':job.job_id,'state':'NOT_CONFIGURED','rows':0,'error':'PROVIDER_CREDENTIALS_REQUIRED'}
        decision=parse_utc(job.decision_time)
        try:
            fetched=provider.historical_canonical(security_id=job.security_id,instrument_key=job.instrument_key,interval=job.interval,from_date=job.from_date,to_date=job.to_date)
            available=parse_utc(fetched.available_time)
            if available>decision: return {'job_id':job.job_id,'state':'BLOCKED','rows':0,'error':'FUTURE_PROVIDER_AVAILABILITY'}
            payload={'provider':fetched.provider,'instrument_key':fetched.instrument_key,'rows':list(fetched.rows),'event_time':fetched.event_time,'available_time':fetched.available_time,'payload_hash':fetched.payload_hash}
            self.store.insert_observation(security_id=job.security_id,dataset='ohlcv',event_time=fetched.event_time,available_time=fetched.available_time,source_id=fetched.provider,payload_hash=fetched.payload_hash,payload=payload,captured_at=fetched.available_time)
            self.store.source_capture(capture_id=sha256(f'{fetched.provider}|{fetched.instrument_key}|{fetched.payload_hash}'.encode()).hexdigest(),source_id=fetched.provider,url=f'{fetched.provider}://historical',payload_hash=fetched.payload_hash,captured_at=fetched.available_time,content_type='application/json',byte_size=len(fetched.raw_payload))
            return {'job_id':job.job_id,'state':'PROMOTED','rows':len(fetched.rows),'payload_hash':fetched.payload_hash}
        except Exception as exc:
            return {'job_id':job.job_id,'state':'FAILED','rows':0,'error':type(exc).__name__+':'+str(exc)}


def zerodha_canonical_fetch(client, *, security_id: str, instrument_key: str, interval: str, from_date: str, to_date: str) -> CanonicalMarketFetch:
    """Adapt Kite historical response into ORION's canonical OHLCV contract."""
    result=client.historical(instrument_key,interval,from_date,to_date)
    data=result.payload.get('data',{}).get('candles',[])
    rows=[]
    for candle in data:
        if len(candle)<6: continue
        rows.append({'event_time':str(candle[0]),'open':candle[1],'high':candle[2],'low':candle[3],'close':candle[4],'volume':candle[5],**({'oi':candle[6]} if len(candle)>6 else {})})
    raw=json.dumps(result.payload,sort_keys=True,separators=(',',':')).encode()
    return CanonicalMarketFetch('zerodha',security_id,instrument_key,tuple(rows),sha256(raw).hexdigest(),result.available_time,result.available_time,raw)
