# ORION v168 — Release Integrity + Read-Only Real-Data Boundary

Baseline: ORION v167 actual artifact.

## Implemented
- Corrected release identity so package metadata, Python version, runtime API identity and UI identity all report v168.
- Added clean-checkout `pyproject.toml` and pytest configuration; source imports no longer depend on an implicit `PYTHONPATH`.
- Added explicit `CONFIGURED_NOT_VERIFIED` provider state so a credential being present is never mistaken for successful authentication.
- Added `mark_authenticated()` to the data-plane boundary; authentication becomes trusted only after an actual successful provider interaction.
- Added read-only Upstox market-data client for historical OHLCV acquisition with bearer-token boundary, request throttling, payload hashing, PIT timestamps and no order/trading surface.
- Runtime gateway exposes Upstox as configured only when the credential exists; it remains unverified until a successful observation is ingested.

## Validation
See release manifest and test output. Live trading remains OFF and no market data is fabricated.
