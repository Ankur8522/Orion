# ORION v170 — PIT Market-Data Acquisition Bridge

## Upgrade
- Added `UpstoxMarketDataAcquirer`, a read-only provider-to-corpus bridge.
- Persists normalized OHLCV payloads into the durable observation store with source capture lineage.
- Enforces decision-time availability before promotion, blocking future information.
- Supports batch acquisition through deterministic job contracts.
- No order/trading capability was introduced.

## Validation
- Full regression suite executed before and after the upgrade.
- Added v170 PIT promotion and future-information regression tests.
- Live trading remains OFF.
