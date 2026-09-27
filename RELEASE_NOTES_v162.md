# ORION v162 — Institutional Architecture Depth Upgrade

## Added
- Research Factory readiness contract across required market, financial, corporate-action, ownership, valuation, evidence, macro/sector and technical datasets.
- Deterministic portfolio risk engine with volatility, VaR95, expected shortfall, drawdown, concentration and sector concentration metrics.
- Learning diagnostics for hit rate, false positives/negatives, systematic probability bias and model-level outcomes.
- Operating readiness scorecard that explicitly penalizes unresolved external dependencies.
- Runtime gateway now exposes learning diagnostics, system readiness and expanded capability inventory.
- API read surfaces for `/api/learning` and `/api/readiness`.
- UI learning metrics and engineering-readiness telemetry.

## Integrity
- No market data fabricated.
- Provider authentication remains an external dependency.
- Live trading remains structurally disabled.
- Existing architecture and regression suite preserved.

## Validation
- Full regression suite: 171 tests passing.
- Python compileall passing.
- HTTP API smoke: health, state, capabilities, readiness, learning and UI root returned 200 in isolated runtime smoke.
- Live trading remains disabled.
