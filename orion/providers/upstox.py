from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json
from typing import Any, Mapping
from urllib.parse import quote

UPSTOX_V3 = 'https://api.upstox.com/v3'

@dataclass(frozen=True)
class UpstoxConfig:
    access_token_env: str = 'UPSTOX_ACCESS_TOKEN'
    base_url: str = UPSTOX_V3
    timeout_seconds: float = 20.0
    max_quote_batch: int = 500
    max_retries: int = 3
    backoff_base_seconds: float = 0.5
    retryable_statuses: tuple[int,...] = (429,500,502,503,504)

@dataclass(frozen=True)
class RawEnvelope:
    provider: str
    dataset: str
    captured_at: str
    event_time: str
    available_time: str
    instrument_key: str
    payload_sha256: str
    raw_payload: bytes

    @classmethod
    def create(cls, dataset: str, instrument_key: str, raw_payload: bytes,
               event_time: str, available_time: str | None = None) -> 'RawEnvelope':
        now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        return cls('upstox', dataset, now, event_time, available_time or now,
                   instrument_key, hashlib.sha256(raw_payload).hexdigest(), raw_payload)

class UpstoxRequestBuilder:
    """Pure request builder: no credentials, network, or order side effects."""
    def __init__(self, config: UpstoxConfig | None = None): self.config = config or UpstoxConfig()
    def historical_candle(self, instrument_key: str, unit: str, interval: int, to_date: str, from_date: str) -> tuple[str, dict]:
        if unit not in {'minutes','hours','days','weeks','months'}: raise ValueError('INVALID_CANDLE_UNIT')
        if not instrument_key or '|' not in instrument_key: raise ValueError('INVALID_INSTRUMENT_KEY')
        path = f"/historical-candle/{quote(instrument_key, safe='')}/{unit}/{interval}/{to_date}/{from_date}"
        return self.config.base_url + path, {'Accept':'application/json','Content-Type':'application/json'}
    def full_quotes(self, instrument_keys: list[str]) -> tuple[str, dict]:
        if not instrument_keys or len(instrument_keys) > self.config.max_quote_batch: raise ValueError('INVALID_QUOTE_BATCH')
        if any('|' not in x for x in instrument_keys): raise ValueError('INVALID_INSTRUMENT_KEY')
        joined=','.join(quote(x,safe='') for x in instrument_keys)
        return self.config.base_url.replace('/v3','/v2') + '/market-quote/quotes?instrument_key=' + joined, {'Accept':'application/json','Content-Type':'application/json'}
    def instrument_search(self, query: str) -> tuple[str, dict]:
        if not query.strip(): raise ValueError('EMPTY_INSTRUMENT_QUERY')
        return self.config.base_url.replace('/v3','/v2') + '/instruments/search?query=' + quote(query), {'Accept':'application/json'}

class UpstoxNormalizer:
    @staticmethod
    def candles(payload: Mapping[str, Any], instrument_key: str, available_time: str) -> list[dict[str, Any]]:
        candles = payload.get('data', {}).get('candles', [])
        out=[]
        for row in candles:
            if not isinstance(row, list) or len(row) < 6: raise ValueError('MALFORMED_CANDLE_ROW')
            ts,o,h,l,c,v = row[:6]
            raw_ts=str(ts)
            parsed=datetime.fromisoformat(raw_ts.replace('Z','+00:00'))
            if parsed.tzinfo is None: raise ValueError('NAIVE_CANDLE_TIMESTAMP')
            event_time=parsed.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            out.append({'provider':'upstox','dataset':'ohlcv','instrument_key':instrument_key,
                        'event_time':event_time,'available_time':available_time,
                        'open':float(o),'high':float(h),'low':float(l),'close':float(c),'volume':float(v)})
        return out

    @staticmethod
    def raw_json(payload: Any) -> bytes:
        return json.dumps(payload, separators=(',',':'), sort_keys=True).encode()
