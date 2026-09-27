from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import random

from .upstox import UpstoxConfig, UpstoxRequestBuilder, UpstoxNormalizer, RawEnvelope

@dataclass(frozen=True)
class ReadOnlyFetchResult:
    envelope: RawEnvelope
    rows: tuple[dict, ...]

class UpstoxReadOnlyClient:
    """Read-only Upstox market-data boundary. No order/trading endpoints exist here."""
    def __init__(self, config: UpstoxConfig | None = None, access_token: str | None = None, min_interval_seconds: float = 0.25, opener=None, sleep_fn=time.sleep, random_fn=random.random):
        self.config=config or UpstoxConfig()
        self.access_token=access_token if access_token is not None else os.environ.get(self.config.access_token_env,'').strip()
        self.min_interval_seconds=max(0.0,float(min_interval_seconds)); self._last_request=0.0
        self.opener=opener or urlopen; self.sleep_fn=sleep_fn; self.random_fn=random_fn
        self.builder=UpstoxRequestBuilder(self.config)

    def _request(self, request):
        retries=max(0,int(getattr(self.config,'max_retries',3)))
        base=max(0.0,float(getattr(self.config,'backoff_base_seconds',0.5)))
        retryable=set(getattr(self.config,'retryable_statuses',(429,500,502,503,504)))
        last_error=None
        for attempt in range(retries+1):
            try:
                return self.opener(request, timeout=self.config.timeout_seconds)
            except HTTPError as e:
                last_error=e
                if e.code not in retryable or attempt >= retries:
                    raise RuntimeError(f'UPSTOX_HTTP_{e.code}') from e
                retry_after=e.headers.get('Retry-After') if e.headers else None
                try: delay=max(0.0,float(retry_after)) if retry_after is not None else 0.0
                except ValueError: delay=0.0
                if delay <= 0.0: delay=base*(2**attempt)*(1.0+0.25*self.random_fn())
                self.sleep_fn(delay)
            except (URLError, TimeoutError) as e:
                last_error=e
                if attempt >= retries: raise RuntimeError('UPSTOX_NETWORK_ERROR') from e
                delay=base*(2**attempt)*(1.0+0.25*self.random_fn())
                self.sleep_fn(delay)
        raise RuntimeError('UPSTOX_REQUEST_FAILED') from last_error

    @property
    def configured(self) -> bool: return bool(self.access_token)

    def historical_candles(self, instrument_key: str, unit: str, interval: int, to_date: str, from_date: str) -> ReadOnlyFetchResult:
        if not self.configured: raise RuntimeError('UPSTOX_CREDENTIALS_REQUIRED')
        url, headers=self.builder.historical_candle(instrument_key,unit,interval,to_date,from_date)
        headers={**headers,'Authorization':f'Bearer {self.access_token}'}
        wait=self.min_interval_seconds-(time.monotonic()-self._last_request)
        if wait>0: time.sleep(wait)
        req=Request(url,headers=headers,method='GET')
        with self._request(req) as response:
            payload=response.read()
            status=getattr(response,'status',200)
        self._last_request=time.monotonic()
        if status < 200 or status >= 300: raise RuntimeError(f'UPSTOX_HTTP_{status}')
        available=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        envelope=RawEnvelope.create('ohlcv',instrument_key,payload,event_time=available,available_time=available)
        import json
        data=json.loads(payload.decode('utf-8'))
        rows=tuple(UpstoxNormalizer.candles(data,instrument_key,available))
        return ReadOnlyFetchResult(envelope,rows)
