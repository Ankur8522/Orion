
# ORION v164 — Cross-Domain Operating Closure

## Major changes
- Added institutional universe contract for NIFTY 50 / Midcap 150 / Smallcap 250 target membership without inventing constituents.
- Added one bounded operating-cycle coordinator connecting forecast resolution, model selection, portfolio attribution, performance analytics and deterministic replay.
- Added sector/regime segmentation to observed forecast diagnostics.
- Wired the operating feedback cycle into the durable control plane.
- Added a single provider-observation validation + reconciliation boundary that refuses silent provider selection on disagreement.
- Corrected performance read-model behavior to use persistent paper NAV history only; no synthetic one-point NAV is generated.
- Expanded the progressive-brain UI phase map to the full target reasoning lifecycle.
- Added universe contract and integrity status to the runtime/UI surfaces.

## Explicit boundaries
- NIFTY 50 + 150 + 250 represents 450 index membership slots; actual constituents require an authorized membership source and are never synthesized.
- Real market data, licensed feeds, and credentials remain external dependencies.
- Live trading remains structurally disabled.
