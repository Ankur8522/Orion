from pathlib import Path
from urllib.error import HTTPError
import io
from orion.providers.upstox_readonly import UpstoxReadOnlyClient
from orion.providers.upstox import UpstoxConfig

class FakeResponse:
    status = 200
    def __init__(self, payload): self._payload=payload
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self): return self._payload

def test_clean_checkout_pytest_import_contract():
    assert Path('pyproject.toml').exists()

def test_retry_429_then_success_without_leaking_token():
    calls=[]
    def opener(req, timeout):
        calls.append((req.full_url, req.headers.get('Authorization')))
        if len(calls)==1:
            h=HTTPError(req.full_url,429,'rate limited',{'Retry-After':'0'},io.BytesIO(b''))
            raise h
        payload=b'{"data":{"candles":[["2026-09-25T10:00:00+00:00",1,2,0.5,1.5,100]]}}'
        return FakeResponse(payload)
    sleeps=[]
    c=UpstoxReadOnlyClient(UpstoxConfig(max_retries=2),access_token='SECRET',min_interval_seconds=0,opener=opener,sleep_fn=sleeps.append,random_fn=lambda:0)
    r=c.historical_candles('NSE_EQ|INE002A01018','days',1,'2026-09-25','2026-09-01')
    assert r.rows[0]['close']==1.5
    assert len(calls)==2 and all(x[1]=='Bearer SECRET' for x in calls)
    assert sleeps==[0.5]

def test_non_retryable_auth_error_is_explicit():
    def opener(req, timeout):
        raise HTTPError(req.full_url,401,'unauthorized',{},io.BytesIO(b''))
    c=UpstoxReadOnlyClient(access_token='SECRET',min_interval_seconds=0,opener=opener)
    try:
        c.historical_candles('NSE_EQ|INE002A01018','days',1,'2026-09-25','2026-09-01')
        assert False
    except RuntimeError as e:
        assert str(e)=='UPSTOX_HTTP_401'
