# ORION v171 — 450-Slot PIT Market Acquisition Planner

## Upgrade
- Added `UniverseMarketDataPlanner` for deterministic NIFTY 50 + NIFTY Midcap 150 + NIFTY Smallcap 250 market-data planning.
- Preserves index membership provenance while deduplicating acquisition work by security ID.
- Requires a verified provider instrument mapping; missing mappings become explicit `NO_INSTRUMENT_MAPPING` blockers.
- Added deterministic batching with configurable batch size for resumable acquisition execution.
- Added durable market batch manifest/job persistence and PIT-bounded OHLCV coverage reporting.
- Added `/api/acquisition/coverage` read-only endpoint.
- No provider/network call is performed by the planner; it remains safe until an authorized credential and verified instrument map exist.

## Validation
- Full regression suite executed after implementation.
- PIT coverage is bounded by `available_time <= decision_time`.
- No synthetic market data added.
- Live trading remains OFF.
