# ORION v152 — Dynamic Capital Allocation Brain

## Major upgrade
Adds an auditable capital-allocation reasoning layer on top of v151 Portfolio Intelligence.

### New capabilities
- Dynamic Capital Allocation Brain
- Bounded multi-signal allocation scoring using expected return, uncertainty, robustness, fragility, calibration and factor overlap
- Explicit allocation constraints: maximum position weight, cash floor and minimum viable weight
- No forced capital for low-quality candidates
- Target weights plus incremental additions/reductions relative to current holdings
- Aggregate expected-return and uncertainty estimates
- Diversification score
- Adaptive triggers for fragility, weak calibration, factor overlap and aggregate uncertainty
- Deterministic lineage hash for allocation state
- API surface for allocation assessment

## Architecture
Evidence/PIT → Research → Thesis → Forecast → Counterfactual → Progressive Decision Brain → Portfolio Intelligence → **Dynamic Capital Allocation Brain** → future optimizer/execution boundaries.

The module is decision support only. It does not fetch market data, invent returns, place orders, or mutate brokerage credentials.

## Validation
- 129/129 pytest tests passing.
- Python compileall passing.
- Existing v127–v151 regression tests retained.
