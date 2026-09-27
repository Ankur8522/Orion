# ORION v156 — Progressive Brain / Closed-Loop Reasoning

## Major upgrade
v156 adds a stateful progressive reasoning layer above the existing v155 intelligence spine.

### New architecture
`Evidence → Belief → Challenge → Counterfactual → Risk → Decision → Monitor → Reopen`

The brain now preserves thesis state across cycles instead of treating every analysis as an isolated calculation.

### New components
- `orion/brain/progressive_loop.py`
  - `ProgressiveReasoningLoop`
  - `ProgressiveMemory`
  - `ProgressiveLearningPolicy`
  - explicit reasoning phases
  - cycle-to-cycle deltas
  - material-change reopen logic
  - feedback-quality integration
  - deterministic lineage hashes
- `InvestmentIntelligenceKernel` now runs the progressive loop as the authoritative progressive state layer.
- `IntelligenceCase` supports cycle IDs, feedback reports, evidence/scenario deltas and material-change signals.
- `IntelligenceRun` exposes `progressive_cycle` in addition to the existing assessment.

## Closed-loop behavior
Forecast calibration feedback can now influence the next reasoning cycle through a bounded effective-calibration score. Poor calibration reduces confidence; good calibration improves it. No outcomes are invented and historical states are append-only.

## Safety / architecture
- Existing research, scenario, portfolio and risk engines remain authoritative for their own domains.
- No live trading path was introduced.
- Paper execution remains the only execution boundary.
- Existing v155 architecture is preserved.
