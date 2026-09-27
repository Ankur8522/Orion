# ORION v178 — Research Integrity + Replay/PIT Hardening

## Baseline
- v177.0.0 inspected and existing suite validated before modification.

## Implemented
- PIT-safe corporate-action normalization and explicit adjustment-factor calculation.
- Corporate-action availability/effective-time leakage guards.
- Explicit research scenario engine with base/bull/bear cases, counter-thesis, causal chains, catalysts/headwinds, blockers and lineage.
- Deterministic portfolio correlation matrix and high-correlation pair detection from supplied return series only.
- Forecast outcome resolver hardened against pre-horizon and future observation leakage.
- Read-only APIs: `POST /api/research/scenarios`, `POST /api/portfolio/correlation`.
- Release identity synchronized to v178.
- Live trading remains disabled.

## Data boundary
No market, fundamental, membership, corporate-action or empirical observations were fabricated. External data remains blocked until verified provider/source observations exist.
