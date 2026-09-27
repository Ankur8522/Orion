# ORION v188 — Institutional Intelligence Kernel

## Verified upgrade

v188 is a material architecture upgrade over v187. It does not claim live or empirical market intelligence without external data.

### Core changes
- Expanded specialist architecture from the prior 7-domain deterministic set to 15 specialist domains.
- Added dependency-free chronological out-of-sample specialist training with explicit metrics and lineage.
- Added learned meta-intelligence that learns specialist trust from observed outcomes rather than relying only on static weights.
- Added canonical PIT-aware Data Fabric with ingestion, temporal validation, stale-state detection, snapshots, and dataset lineage.
- Extended DecisionWorld to carry canonical dataset snapshots and feature lineage while preserving the single decision-time boundary.
- Added a ResearchFactory entry point that consumes immutable DecisionWorld dataset state.
- Upgraded UI visual system toward a denser institutional workstation aesthetic while preserving explicit no-fake-data boundaries.
- Updated release identity to v188.

## Validation
- Full regression: PASS.
- Tests collected: 294.
- `compileall`: PASS.
- Secret scan: CLEAN; only test placeholder credentials were detected.
- Live order-method scan: CLEAN; no live trading order surface introduced.
- Live trading remains disabled.

## Explicit blockers
- Real market/fundamental/estimate/news provider credentials are still external dependencies.
- No empirical performance claim is made from the code-only release.
- 450-security real-data coverage is not claimed until provider observations establish it.
