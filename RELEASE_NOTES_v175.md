# ORION v175 — Operational Data Readiness Gate

## Upgrade
Added a governed operational-readiness projection joining three independently verified conditions: provider authentication, point-in-time instrument mapping, and point-in-time OHLCV observation coverage.

A security is `READY` only when all three are true. Missing credentials, mappings, or observations remain explicit blockers; the layer never synthesizes data.

## Changes
- `orion/acquisition/operational_readiness.py`
- Runtime gateway method and capability `OPERATIONAL_DATA_READINESS`
- Read-only `/api/acquisition/operational-readiness` endpoint
- UI/runtime version identity updated to v175
- Regression tests for provider-auth and PIT coverage gating
- Release identity tests updated to v175

## Safety
- Live trading remains disabled.
- No synthetic market data introduced.
- PIT mapping and observation boundaries remain enforced.
- Provider authentication is never inferred from configuration alone.

## Validation
- 220 tests passed
- compileall passed
- clean package smoke passed
- artifact integrity verified
