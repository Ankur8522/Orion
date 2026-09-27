from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, time, json, random

@dataclass(frozen=True)
class ZerodhaConfig:
    base_url: str = 'https://api.kite.trade'
    api_key_env: str = 'ORION_ZERODHA_API_KEY'
    access_token_env: str = 'ORION_ZERODHA_ACCESS_TOKEN'
    timeout_seconds: float = 20.0
    max_retries: int = 3
    backoff_base_seconds: float = 0.5

@dataclass(frozen=True)
class ZerodhaFetchResult:
    dataset: str
    request_url: str
    payload: dict
    available_time: str

class ZerodhaReadOnlyClient:
    """Read-only Kite Connect boundary. No order endpoints are implemented."""
    def __init__(self, config: ZerodhaConfig | None = None, *, api_key: str | None = None, access_token: str | None = None, opener=None, sleep_fn=time.sleep, random_fn=random.random):
        self.config=config or ZerodhaConfig()
        self.api_key=api_key if api_key is not None else os.environ.get(self.config.api_key_env,'').strip()
        self.access_token=access_token if access_token is not None else os.environ.get(self.config.access_token_env,'').strip()
        self.opener=opener or urlopen; self.sleep_fn=sleep_fn; self.random_fn=random_fn; self._last_request=0.0

    @property
    def configured(self) -> bool: return bool(self.api_key and self.access_token)

    def _get(self, path: str, params: dict[str,str]) -> ZerodhaFetchResult:
        if not self.configured: raise RuntimeError('ZERODHA_CREDENTIALS_REQUIRED')
        from urllib.parse import urlencode
        url=f'{self.config.base_url}{path}?{urlencode(params)}'
        headers={'X-Kite-Version':'3','Authorization':f'token {self.api_key}:{self.access_token}'}
        retries=max(0,self.config.max_retries); last=None
        for attempt in range(retries+1):
            wait=0.25-(time.monotonic()-self._last_request)
            if wait>0: self.sleep_fn(wait)
            try:
                req=Request(url,headers=headers,method='GET')
                with self.opener(req,timeout=self.config.timeout_seconds) as response:
                    raw=response.read(); status=getattr(response,'status',200)
                self._last_request=time.monotonic()
                if status < 200 or status >= 300: raise RuntimeError(f'ZERODHA_HTTP_{status}')
                return ZerodhaFetchResult(path,url,json.loads(raw.decode('utf-8')),datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
            except HTTPError as exc:
                last=exc
                if exc.code not in {429,500,502,503,504} or attempt>=retries: raise RuntimeError(f'ZERODHA_HTTP_{exc.code}') from exc
                self.sleep_fn(self.config.backoff_base_seconds*(2**attempt)*(1+0.25*self.random_fn()))
            except (URLError, TimeoutError) as exc:
                last=exc
                if attempt>=retries: raise RuntimeError('ZERODHA_NETWORK_ERROR') from exc
                self.sleep_fn(self.config.backoff_base_seconds*(2**attempt)*(1+0.25*self.random_fn()))
        raise RuntimeError('ZERODHA_REQUEST_FAILED') from last

    def instruments(self, exchange: str | None = None) -> ZerodhaFetchResult:
        # Instrument master is public/auth-light but kept behind this adapter for provenance.
        path='/instruments' if not exchange else f'/instruments/{exchange.upper()}'
        return self._get(path,{})

    def quote(self, instruments: list[str]) -> ZerodhaFetchResult:
        if not instruments: raise ValueError('INSTRUMENTS_REQUIRED')
        return self._get('/quote', {'i': instruments[0]}) if len(instruments)==1 else self._get('/quote', [('i',x) for x in instruments])

    def historical(self, instrument_token: int | str, interval: str, from_date: str, to_date: str, continuous: bool=False, oi: bool=False) -> ZerodhaFetchResult:
        path=f'/instruments/historical/{instrument_token}/{interval}'
        return self._get(path, {'from':from_date,'to':to_date,'continuous':'true' if continuous else 'false','oi':'true' if oi else 'false'})

    def historical_canonical(self, *, security_id: str, instrument_key: str, interval: str, from_date: str, to_date: str):
        from ..acquisition.provider_market import zerodha_canonical_fetch
        return zerodha_canonical_fetch(self, security_id=security_id, instrument_key=instrument_key, interval=interval, from_date=from_date, to_date=to_date)
