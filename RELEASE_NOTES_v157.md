# ORION v157 — Architecture Closure & Persistent Adaptive Runtime

## Purpose
Close the major runtime gaps above v156 without replacing existing domain brains.

## Architecture
`Market/Data Sources -> PIT/Data Quality/Reconciliation -> Evidence/Research/Forensics -> Decision Plane -> Progressive Brain -> Counterfactual/Scenario -> Portfolio/Risk -> Allocation -> Signal -> Paper Execution -> Outcome/Feedback -> Persistent Memory -> Replay/Audit/Observability`

## Major upgrades
- SQLite-backed append-only progressive thesis memory with restart hydration.
- Hash-chained runtime journal for deterministic audit/replay lineage.
- Paper execution lifecycle: staged order -> fill -> position -> mark-to-market -> P&L snapshot.
- Central `OrionControlPlane` for runtime lifecycle, metrics, audit and paper-only safety.
- Existing v155/v156 decision and progressive brains remain authoritative; no duplicate scoring engine.
- Live trading remains structurally disabled.

## Safety
This release does not add broker order routing. Missing evidence remains blocked rather than synthesized.
