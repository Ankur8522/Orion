# ORION v169 — Resilient Read-Only Real-Data Acquisition Boundary

Built from v168 after baseline inspection and regression testing.

## Upgrade
- Added clean-checkout pytest import path contract (`pythonpath = ["."]`).
- Hardened the read-only Upstox historical OHLCV client with bounded exponential backoff.
- Retries are limited to transient network failures and HTTP 429/5xx responses; authentication/client errors are surfaced immediately.
- Honors `Retry-After` when provided.
- Added injectable transport/sleep hooks for deterministic offline tests.
- Preserved bearer-token boundary and no-order/no-live-trading architecture.
- Upgraded runtime/package/UI release identity coherently to v169.

## Data/PIT status
Upstox historical candles remain a read-only production data pathway. A successful authenticated response can now be integrated into the existing PIT ingestion path without silently treating credentials as verified. No external market data was fabricated during this release.

Current environment still has no authorized Upstox token, so production market-data readiness remains dependency-bound.

## Validation
- Full pytest suite: PASS
- Compileall: PASS
- Retry/429 regression: PASS
- Non-retryable auth error regression: PASS
- Existing PIT/evidence/replay/paper-safety tests preserved
- Live trading remains OFF
