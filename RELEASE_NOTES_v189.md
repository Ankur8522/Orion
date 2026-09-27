# ORION v189 — Governed Intelligence Pipeline + Empirical Distribution Kernel

## Verified upgrade

v189 closes a key v188 architectural gap: trained specialist models and the meta-model are now exposed through a governed DecisionWorld inference boundary, while PIT datasets expose deterministic point-in-time selection and empirical forecast distributions remain fail-closed until sufficient observed outcomes exist.

### Core changes
- Added `DecisionIntelligenceEngine`: immutable DecisionWorld → trained specialist inference → governed ensemble/meta-intelligence.
- DecisionWorld inference blocks when the canonical decision world is not READY; it does not fall back to deterministic specialist scores.
- Added empirical forecast distribution kernel for verified historical outcomes with quantiles, positive-return probability, downside percentile and explicit `INSUFFICIENT_EVIDENCE` state.
- Added content-addressed model artifact persistence with dataset/feature/code lineage hashes.
- Strengthened canonical Data Fabric point-in-time selection for restatements: the observation available at the decision cutoff is selected deterministically.
- Added regression tests for restatement selection, governed inference, empirical distribution fail-closed behavior and model artifact round-trip.
- Updated runtime/UI identity to v189.

## Audit conclusion

The v188 audit found that specialist training and meta-intelligence existed but were not yet a first-class governed inference boundary, and forecast distributions were still largely caller-constructed. v189 addresses those architectural seams.

## Validation
- Full regression: PASS.
- Clean extraction verification: required before release publication.
- PIT/restatement test: PASS.
- Governed DecisionWorld inference test: PASS.
- Empirical distribution fail-closed test: PASS.
- Model artifact persistence test: PASS.
- Live trading remains disabled.

## Explicit blockers
- Real provider credentials and external historical data remain required for empirical market intelligence.
- No real-data coverage, profitability, alpha, accuracy or Sharpe claim is made.
- 450-security empirical coverage remains unclaimed until actual observations exist.
