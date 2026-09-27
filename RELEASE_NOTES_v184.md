# ORION v184.0 — Trade Intelligence Brain

## Focus
Fundamental + technical + historical-pattern + risk/context fusion with PIT-safe model training.

## Implemented
- Added `orion.decision.trade_intelligence` with a 14-feature normalized trade-fusion vector.
- Added auditable candidate scoring, confidence, completeness, blockers and lineage hashes.
- Added deterministic ranking with duplicate-security protection.
- Added chronological logistic training using only supplied observed outcomes.
- Added explicit future-feature rejection and optional training-cutoff protection for unresolved outcomes.
- Added validation Brier score and coefficient lineage.
- Added `orion.research.historical_patterns` for PIT-safe nearest-pattern matching using historical return windows.
- Historical forward returns are treated as labels only and are never included in similarity features.
- No market data, provider access, empirical performance or forecast accuracy is fabricated.
- Live trading remains disabled.

## Verification
- Full regression suite: PASS.
- Dedicated trade-intelligence tests: PASS.
- Historical-pattern PIT tests: PASS.
- Compile/static checks and release audit required before artifact publication.

## Remaining
Real provider observations are still required for production training, calibration and historical 450-security replay.
