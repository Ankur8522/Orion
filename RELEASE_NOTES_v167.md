# ORION v167 — Max Real-Data / PIT / Empirical Closure

Baseline: ORION v166 (audited from the actual release artifact).

## Closed gaps
- Dataset-specific provider readiness and historical coverage.
- Stronger PIT observation/corpus metadata and validation.
- Historical `membership_as_of(T)` API semantics.
- Information-value research priority expansion.
- Evidence-gated champion/challenger switching.
- Observable bounded operating-cycle metadata.
- Time Machine in-memory persistence bug.

## Validation
- 197/197 tests passing
- compileall passing
- API/UI smoke passing
- PIT/future-information tests passing
- persistence/restart passing
- replay determinism passing
- RBAC passing
- paper safety passing
- secret scan passing
- runtime-state exclusion enforced during packaging
- live trading OFF

## Honest limitation
Real-data operation remains dependent on authorized providers and historical PIT datasets. No market data, forecast outcomes, paper returns, or empirical performance are fabricated when those dependencies are unavailable.
