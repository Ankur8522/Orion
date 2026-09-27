# ORION v166 — Empirical + Data-Plane Hardening

## Baseline
v165 Max Institutional Architecture + Brain Runtime.

## Implemented
- Expanded research dataset contract across universe, market, OHLCV, volume, corporate actions, financials, quarterly results, cash flow, balance sheet, valuation, ownership, order-book/business visibility, estimates, sector/macro, technicals, forensics, evidence, catalysts, headwinds, thesis, counter-thesis, scenarios, forecast and outcome history.
- Conditional dataset applicability so genuinely non-applicable datasets do not block a dossier when explicitly marked `applicable=false`.
- Dataset-specific provider coverage rather than treating one configured provider as coverage for every dataset.
- Provider freshness tracking with explicit `READY`, `STALE`, `DEPENDENCY`, `NOT_CONFIGURED`, and `NO_SUCCESS_OBSERVATION` states.
- Successful point-in-time provider ingestion records freshness.
- Empirical validation now supports an existing durable forecast ledger and exposes learning diagnostics alongside PIT backtest evidence.
- Runtime empirical validation read-model now derives from observed durable outcomes instead of a static placeholder.
- Portfolio performance now reports Sortino when sufficient verified NAV history exists.
- UI upgraded to v166 and exposes provider freshness and Sortino.
- Live trading remains structurally disabled.

## Safety / Truth Boundary
- No market data, forecast outcome, performance history, or universe constituent is fabricated.
- Missing external providers remain explicit dependencies.
- Persistent runtime state is excluded from release artifacts.
