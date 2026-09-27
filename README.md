# ORION v168 — Release Integrity + Read-Only Real-Data Boundary Runtime

Current release adds an auditable forecast -> outcome -> scoring -> calibration loop on top of the v147 real-data/PIT runtime. Existing PIT, evidence, decision, causal, portfolio-risk and no-trading boundaries are preserved.

See `README_v148.md` and `RELEASE_NOTES_v148.md` for the v148 delta.

# ORION v136.0 — Deep Audit / Research Brain / Production Runtime

## Release focus
- PIT-safe market signal analysis: trend, momentum, volume expansion and breakout detection.
- Sector-aware financial metrics retained and integrated into the research pipeline.
- Configurable forensic thresholds with CFO/PAT, receivable intensity, leverage and inventory checks.
- Research priority engine now incorporates data gaps, thesis change, event urgency, portfolio exposure, evidence risk and market signal.
- Batch executor reports completed/blocked/failed work explicitly and preserves checkpoints.
- Existing evidence, PIT, reconciliation, audit/replay, adversarial review and security boundaries retained.

## Validation
- 
- Python compileall passing.
- Source-tree isolated import smoke test passing.
- Offline wheel build was not claimed: build isolation attempted to reach an unavailable package index.

## Data boundary
No synthetic/live market feed is fabricated. Public and licensed providers remain separate; production acquisition requires authorized source access.

## Trading boundary
No live trading, order routing, credential mutation, or external-money movement is enabled.

## v137 — Production Acquisition & Evidence Execution
- Deterministic acquisition planning for the research universe.
- Provider/source contracts with explicit public-vs-licensed boundary.
- No fabricated URLs: unresolved provider discovery is BLOCKED.
- Safe acquisition executor built on the existing HTTPS allowlist, redirect and response-size controls.
- Document classifier for financial results, auditor reports, board disclosures, investor presentations, annual reports and corporate actions.
- Acquisition results preserve payload hash, document kind, confidence and failure state.
- Research manifests are deterministic and deduplicated.

### Runtime boundary
The system does not claim to have a live NSE/BSE/licensed feed unless a legitimate provider is configured. Provider discovery/adapters remain source-specific.

## Validation (v137)
- 66/66 pytest tests passing.
- Python compileall passing.
- Wheel build passing with setuptools/pip offline build path.
- Clean target wheel installation/import passing.
- 500-security manifest smoke test passing; 500 persisted acquisition jobs verified.

## v139 Production Source Adapters
- Official NSE public discovery adapters for financial-results and corporate-announcement pages.
- BSE corporate-data access remains an explicit licensed/API boundary; ORION never guesses undocumented endpoints.
- Retry/backoff and rate-limit primitives.
- Allowlisted filing-link extraction for HTML filing pages.

## v140 — Financial Fact Extraction & Reconciliation
v140 adds deterministic extraction of core financial facts from normalized filing text/rows and a PIT-safe reconciliation layer. Revenue, EBITDA, PAT, CFO, receivables, inventory, debt and cash can be extracted into typed `FinancialFact` records. Small source differences can be marked `AGREED`; material disagreements become `REVIEW` with the competing facts preserved. No missing values, future evidence, or conflicting metrics are silently fabricated or selected.

## v141 — Consolidated company intelligence
ORION now converts reconciled financial facts into a period-aware company model, derives growth/margins/cash conversion/FCF/leverage/return metrics, computes valuation bridges when market inputs are available, and exposes a unified research snapshot. Missing inputs remain missing; flags are transparent rule-based observations rather than investment ratings.

## v143

Production batch bridge now connects the 500-stock manifest to the integrated research dossier. Missing data remains explicitly BLOCKED; no synthetic facts are created.

## v144 — Coverage & Data Quality

ORION now exposes a deterministic coverage report over production batch results. Each security has a stage-derived coverage percentage plus explicit missing data/blockers; aggregate reports expose completion, blocked, failed, average coverage, and stage counts. Coverage is observability only and never bypasses evidence or PIT gates.


## v152 — Dynamic Capital Allocation Brain
See `RELEASE_NOTES_v152.md`. v152 adds constrained, auditable capital-allocation reasoning using expected return, uncertainty, robustness, fragility, calibration and factor overlap, with adaptive review triggers and deterministic lineage.

## v156 — Progressive Brain / Closed-Loop Reasoning

ORION v156 adds a stateful progressive reasoning loop: **Observe → Hypothesize → Challenge → Counterfactual → Risk → Decide → Monitor → Reopen**. Thesis states are append-only, cycle-to-cycle deltas are tracked, material changes reopen the thesis, and forecast calibration feedback is bounded into the next reasoning cycle. Live trading remains disabled; paper execution is the only execution boundary.

## v155 — Full Intelligence Architecture Spine
The application now has an authoritative orchestration spine connecting PIT/evidence, research decisioning, progressive reasoning, counterfactual scenarios, portfolio intelligence, risk gates, capital allocation, non-trading signals, and paper-only execution. Every run produces a lineage manifest. Live trading remains disabled by design.


## v157 Architecture Closure
The runtime now includes persistent progressive thesis memory, hash-chained audit journal, paper order/fill/P&L lifecycle, and the OrionControlPlane. Live trading remains disabled.

## v158 architecture completion
The autonomous operating layer now includes restart-safe forecast/outcome learning, bounded champion/challenger selection, persistent time-machine replay, portfolio attribution, universe scheduling, and an integrated autonomous cycle. Live trading remains disabled.


## v159 — Full Runtime + UI/UX Completion
The universe operating runtime, persistent paper lifecycle, runtime JSON gateway, HTTP cockpit server, and runtime health contract are connected. The UI is explicitly runtime-aware and live trading remains disabled.


## v160 — Maximum Architecture / Brain / UI Runtime Hardening
- Durable operating state for cycles, alerts, UI events and research jobs.
- Persistent research queue and runtime control-plane integration.
- Read-only runtime copilot backed only by verified ORION state.
- Expanded runtime API: state, health, brain history and audit.
- UI/UX rebuilt as a runtime-first cockpit: no hard-coded market metrics, responsive navigation, brain timeline, paper portfolio, replay, operations and data-boundary surfaces.
- Docker now runs the HTTP cockpit with persistent state and a healthcheck.
- Live trading remains disabled; provider access is explicit and missing market data is never synthesized.


## v161 Maximum Architecture Upgrade
The runtime now includes explicit data-plane/provider readiness, portfolio performance analytics, bounded orchestration, RBAC policy, unified API read-models, and Data Plane / Performance / Security UI surfaces. Live trading remains OFF and unavailable data is never synthesized.


## v163 — Institutional Architecture Depth
The runtime adds a formal research-readiness contract, deterministic portfolio risk analytics, observed-outcome learning diagnostics, system readiness telemetry, and governed API/UI exposure. External market data remains dependency-bound and live trading remains disabled.


## v163 Institutional Runtime Closure
The control plane now durably owns forecast, model and replay state; provider ingestion enforces PIT boundaries; research readiness bridges into the production factory; paper NAV history is persistent; every intelligence run emits a replay snapshot; and the UI exposes Company, Sector Intelligence and Risk Engine surfaces without synthetic market data. Live trading remains disabled.

## v164 — Cross-Domain Operating Closure
v164 connects the durable control plane to a bounded feedback cycle spanning universe coverage, forecast resolution, model comparison, portfolio attribution, performance analytics and deterministic replay. It also adds a single provider-observation validation/reconciliation boundary and removes the prior synthetic one-point paper-performance fallback. The UI exposes the full progressive reasoning lifecycle. The intended NIFTY 50 + Midcap 150 + Smallcap 250 target is 450 index-membership slots; real constituents require authorized source access.


## v165 — Empirical Validation / Research Intelligence Depth
v165 adds a first-class empirical validation boundary combining observed forecast outcomes with point-in-time backtest look-ahead rejection. Research operating plans now derive bounded information-value priority when explicit priorities are absent, while preserving deterministic dossier readiness gates. Universe memberships now support effective/availability timestamps for historical point-in-time reconstruction. Learning diagnostics expose Brier score, log loss and probability calibration gap alongside existing hit/false-positive/false-negative and model/sector/regime diagnostics. The UI exposes empirical-validation readiness without fabricating performance. Live trading remains disabled.

## v166 — Empirical + Data-Plane Hardening
- Dataset-specific provider coverage and freshness states.
- Provider ingestion records successful observation freshness.
- Expanded research dataset contract with conditional applicability.
- Empirical validation consumes durable forecast outcomes without fabricating history.
- Portfolio performance adds Sortino when sufficient verified NAV observations exist.
- UI/API expose provider freshness and updated v166 runtime identity.
- Live trading remains permanently disabled.


## v167 — Max Real-Data / PIT / Empirical Closure

Built directly from v166 after an actual baseline test/audit. This release strengthens the existing architecture rather than adding a duplicate brain.

- Explicit dataset-specific provider readiness and historical coverage states.
- Provider observations carry effective/observation time, quality, source priority and lineage metadata.
- PIT corpus validates decision-time eligibility and ingestion ordering.
- Historical universe exposes `membership_as_of(T)` semantics.
- Research priority incorporates forecast failure, model disagreement, risk/valuation/regime changes, data-quality improvement, evidence conflict and uncertainty.
- Champion/challenger selection requires observed outcomes plus horizon, confidence, stability, regime and performance-delta gates.
- Bounded operating cycle exposes run ID, timing, processed/blocked/dependency counts, errors and lineage.
- Fixed Time Machine `:memory:` persistence bug.
- Live trading remains structurally disabled.
- No external market data or performance is fabricated; unavailable dependencies remain explicit.


## v168 — Release Integrity + Read-Only Real-Data Boundary
v168 corrects release identity drift, adds a clean-checkout packaging/test contract, distinguishes configured-but-unverified providers from authenticated providers, and adds a read-only Upstox historical OHLCV acquisition boundary. No order or live-trading endpoint is introduced.

## v173
450-slot PIT market acquisition planner, durable batch jobs, and PIT-bounded coverage reporting.

## v174
Governed, point-in-time instrument mapping and acquisition readiness are now part of the real-data boundary. Mapping records carry provider, effective interval, availability time, source lineage and content hash; readiness explicitly reports mapped versus blocked securities. New read-only API surfaces: `/api/acquisition/readiness` and `/api/acquisition/mappings`.

## v175
Operational Data Readiness Gate: provider authentication + PIT instrument mapping + PIT observation coverage are now combined into an explicit per-security readiness projection and read-only API. No security is marked ready without verified evidence for all required conditions.


## v176 — Code-Completable Institutional Closure Sweep
- Added persistent PIT-safe historical universe membership registry and time-machine snapshots.
- Added restart-safe forecast outcome resolution facade over the persistent ledger.
- Added model/sector/regime/horizon diagnostics with minimum-sample flags and calibration drift detection.
- Added supplied-data-only portfolio correlation clustering and stress/fragility analytics.
- Added static release/security audit capability.
- Added API surfaces for historical universe snapshots, advanced learning diagnostics, and portfolio stress.
- No provider credential, market observation, forecast outcome, or universe constituent was fabricated.


## v178 — Code-Completable Forecast + Paper Execution Closure

- Bounded probabilistic forecast generation from explicit evidence inputs.
- Explicit forecast uncertainty, thesis fingerprint and lineage.
- Realistic paper execution cost engine with explicit slippage/impact/fee/tax assumptions.
- Empirical validation evaluation-time boundary hardened.
- Real-data providers remain explicitly blocked until authenticated and verified.

## v178 — Research Integrity + Replay/PIT Hardening
- Adds PIT-safe corporate actions, explicit research scenarios/counter-thesis/causal chains, deterministic correlation analytics, and stricter forecast outcome timing.
