import os
from pathlib import Path
from orion import __version__
from orion.app.gateway import RuntimeGateway
from orion.runtime.data_plane import DataPlaneRegistry
from orion.providers.upstox_readonly import UpstoxReadOnlyClient

def test_release_identity_is_coherent():
    assert __version__ == '190.0.0'
    g=RuntimeGateway()
    assert g.state()['version']== 'v190'

def test_clean_checkout_has_pyproject():
    assert Path('pyproject.toml').exists()

def test_configured_provider_is_not_claimed_authenticated():
    d=DataPlaneRegistry()
    d.register('upstox',configured=True,authenticated=False,capabilities=('ohlcv',),historical_datasets=('ohlcv',),reason='CREDENTIAL_PRESENT_AUTH_NOT_VERIFIED')
    c=d.coverage(('ohlcv',))
    assert c['datasets']['ohlcv']['status']=='CONFIGURED_NOT_VERIFIED'
    assert not c['datasets']['ohlcv']['ready']

def test_upstox_readonly_requires_credential():
    c=UpstoxReadOnlyClient(access_token='')
    assert not c.configured
    try:
        c.historical_candles('NSE_EQ|INE002A01018','days',1,'2026-09-25','2026-09-01')
        assert False
    except RuntimeError as e:
        assert str(e)=='UPSTOX_CREDENTIALS_REQUIRED'
