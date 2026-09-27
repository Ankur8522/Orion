# ORION v185.0.0 — PIT Technical/Fundamental Feature Bridge & Walk-Forward Calibration

## Meaningful upgrade
- Added PIT-safe technical feature extraction from supplied OHLCV observations.
- Added transparent normalized fundamental feature extraction from reconciled company metrics.
- Added raw-observation bridge into the trade-intelligence engine.
- Added explicit missing-feature handling; training no longer silently imputes absent features unless explicitly opted in.
- Aligned trade classifications to `STRONG_CANDIDATE`, `CANDIDATE`, `WATCH`, `NO_ACTION`, `BLOCKED`.
- Added dependency-free isotonic probability calibration with explicit insufficient-history state.
- Added chronological train → calibration → untouched test workflow.
- Added regression tests for future leakage, missing-data behavior, calibration and raw feature derivation.

## Safety / truthfulness
- No market data, provider observations or empirical performance were fabricated.
- Synthetic fixtures are test-only and are not represented as market observations.
- Real provider credentials are not embedded.
- Live trading remains disabled.
- Probabilities remain model outputs until verified historical outcomes support calibration.

## Verification
- Full pytest: PASS
- Compileall: PASS
- PIT technical future-observation guard: PASS
- Training missing-feature guard: PASS
- Walk-forward chronology: PASS
- Calibration insufficient-history behavior: PASS
- Live-trading guard: OFF
