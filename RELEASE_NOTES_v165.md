# ORION v165 — Empirical Validation + Research Intelligence Depth

## What changed
- Added `EmpiricalValidationLab` combining observed forecast scoring with PIT backtest look-ahead rejection.
- Added `/api/validation` and runtime UI telemetry for empirical-validation readiness.
- Research operating plans now derive information-value priority from observed data gaps, thesis changes, event urgency, exposure, evidence risk and market signals when explicit priority is absent.
- Fixed priority ordering so the research execution order and security IDs remain aligned after sorting.
- Universe memberships now carry optional effective-from/effective-to/available timestamps and can be evaluated as-of a historical point.
- Learning diagnostics now expose Brier score, log loss and probability calibration gap in addition to existing outcome diagnostics.
- Preserved no-fabrication, PIT, audit and paper-only boundaries.

## Validation
- 186/186 tests passing.
- compileall passing.
- HTTP API smoke passing for health, state, validation, capabilities, UI root and research requirements.
- Look-ahead rejection verified.
- Runtime state excluded from release artifact.
- Live trading remains OFF.
