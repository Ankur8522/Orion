from orion.data.providers import ProviderRegistry, ProviderContract, FeedMode, ProviderStatus


def test_provider_readiness_is_explicit_and_deterministic():
    r=ProviderRegistry()
    r.register(ProviderContract('upstox',FeedMode.LICENSED,frozenset({'ohlcv'}),authenticated=False))
    assert r.dataset_status('ohlcv') == ProviderStatus.NOT_CONFIGURED
    rows=r.readiness('ohlcv')
    assert rows[0].reason == 'AUTHENTICATION_NOT_CONFIGURED'


def test_provider_with_auth_but_no_success_is_not_ready():
    r=ProviderRegistry()
    r.register(ProviderContract('licensed',FeedMode.LICENSED,frozenset({'financials'}),authenticated=True,last_success_at=None))
    assert r.dataset_status('financials') == ProviderStatus.NO_SUCCESS_OBSERVATION


def test_provider_staleness_is_checked_at_historical_cutoff():
    r=ProviderRegistry()
    r.register(ProviderContract('licensed',FeedMode.LICENSED,frozenset({'ohlcv'}),authenticated=True,last_success_at='2026-09-25T00:00:00Z',stale_after_seconds=3600))
    assert r.dataset_status('ohlcv',as_of='2026-09-27T00:00:00Z') == ProviderStatus.STALE


def test_provider_future_success_is_not_ready():
    r=ProviderRegistry()
    r.register(ProviderContract('licensed',FeedMode.LICENSED,frozenset({'ohlcv'}),authenticated=True,last_success_at='2026-09-28T00:00:00Z',stale_after_seconds=3600))
    assert r.dataset_status('ohlcv',as_of='2026-09-27T00:00:00Z') == ProviderStatus.NOT_CONFIGURED


def test_unsupported_dataset_is_explicit():
    r=ProviderRegistry()
    assert r.dataset_status('news') == ProviderStatus.UNSUPPORTED


def test_empty_registry_reports_unsupported_not_ready():
    r=ProviderRegistry()
    assert r.dataset_status('ohlcv') == ProviderStatus.UNSUPPORTED
