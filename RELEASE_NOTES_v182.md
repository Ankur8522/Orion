# ORION v182

## Provider/data readiness boundary

- Added explicit provider/dataset readiness states: `READY`, `NOT_CONFIGURED`, `STALE`, `NO_SUCCESS_OBSERVATION`, and `UNSUPPORTED`.
- Provider readiness is evaluated deterministically against an optional historical cutoff, preventing future-success metadata from being treated as available at an earlier decision time.
- Added explicit provider reason codes and dataset-level status aggregation without fabricating observations or coverage.
- Live trading remains disabled; this release adds no trading route.
