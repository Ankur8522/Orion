# ORION v155 — Full Intelligence Architecture Spine

## Purpose
Bind the mature ORION domain engines into one auditable, end-to-end intelligence lifecycle without replacing their specialized logic.

## Architecture
```text
Market Data / Documents
        ↓
PIT + Data Quality + Reconciliation
        ↓
Evidence Ledger / Research / Forensics / Agents
        ↓
Research Decision Plane
        ↓
Progressive Decision Brain
        ↓
Counterfactual World + Scenario Engine
        ↓
Portfolio Intelligence + Risk Gate
        ↓
Dynamic Capital Allocation
        ↓
Signal Engine
        ↓
Paper Execution Boundary  ← live trading intentionally OFF
        ↓
Feedback / Forecast Calibration
        ↓
Dashboard / API / Audit Lineage
```

## Added
- `orion.brain.kernel.InvestmentIntelligenceKernel`: authoritative orchestration spine.
- `IntelligenceCase` / `IntelligenceRun`: typed end-to-end run contract.
- `orion.signal.engine.SignalEngine`: governed decision-to-signal boundary; no trading.
- `orion.execution.paper.PaperExecutionBook`: paper-only order staging with immutable lineage.
- `orion.app.service.OrionService`: application-service wiring for the full research-to-paper lifecycle.
- Full run manifest hash joining decision, progressive brain, scenarios, portfolio, allocation and risk state.
- Hard risk-gate propagation: blocked risk prevents allocation and signal execution.
- High fragility / high uncertainty propagation into decision blockers.
- Regression tests for the complete spine and live-trading-off invariant.

## Preserved
- PIT/evidence discipline
- Real-data pathways and Upstox normalization
- Existing research/forensics/agent layers
- Forecast feedback/calibration
- Counterfactual world model
- Portfolio intelligence
- Dynamic capital allocation
- Existing UI cockpit
- Backward-compatible specialized modules

## Safety boundary
No live brokerage routing is implemented or enabled. The execution layer is explicitly paper-only.
