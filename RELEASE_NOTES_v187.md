# ORION v187.0.0 — Decision World / Coverage / Specialist Architecture

## Purpose
v187 is a structural redesign after the v185/v186 architecture audit. It does not claim real-data availability, trading accuracy, or empirical superiority.

## Implemented
- Fail-closed dataset coverage contract with explicit READY/PARTIAL/MISSING/STALE/NOT_CONFIGURED/UNSUPPORTED states.
- Provider capability registry with read-only enforcement and deterministic lineage.
- Evidence graph binding claims, evidence, conflicts and future-evidence blockers.
- Single `DecisionWorld` boundary joining PIT snapshot, dataset coverage and evidence readiness so downstream models cannot silently use split timestamps/data states.
- Seven independent specialist feature domains: fundamental quality, valuation, technical, historical pattern, business visibility, regime and risk.
- Specialist results expose missing features and lineage rather than silently substituting neutral values.
- Ensemble empirical-eligibility gate: when the new required-specialist mode is used, specialists must have out-of-sample Brier evidence, feature coverage and regime coverage before contributing to an empirical probability.
- Backward-compatible diagnostic ensemble behavior retained for existing non-empirical tests; it is not an empirical performance claim.
- Regression coverage for the new architecture.

## Explicit non-claims
- No fundamental/news/estimates provider is connected by this release.
- Zerodha credentials are not embedded.
- No 450-security real dataset is present.
- No empirical profitability/accuracy claim is made.
- Live trading remains disabled.
