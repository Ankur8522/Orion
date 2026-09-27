# ORION v177 — Code-Completable Forecast + Paper Execution Closure

## Baseline
- v176.0.0 inspected and validated before modification.
- Existing suite: 227 tests passing.

## Implemented
- Bounded probabilistic forecast generator using caller-supplied base rate and evidence signals.
- Explicit uncertainty, thesis fingerprint and lineage hash.
- No empirical accuracy is claimed by the generator itself.
- Realistic paper execution cost engine with explicit slippage, impact, brokerage, exchange, GST, STT, stamp duty and SEBI fee assumptions.
- Deterministic cost lineage hash.
- Empirical validation gateway now evaluates persisted outcomes at a valid observed evaluation time instead of accidentally using an earlier forecast decision timestamp.
- Read-only computation APIs:
  - `POST /api/forecast/probabilistic`
  - `POST /api/paper/cost`
- Release identity synchronized to v177.
- Live trading remains disabled.

## Data boundary
External market/fundamental/history providers remain explicitly blocked unless authenticated and verified. No market data or empirical performance was fabricated.
