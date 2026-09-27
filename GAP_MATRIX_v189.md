# ORION v189 — Architecture Gap Matrix

| Domain | Current capability | Actual implementation | Gap / risk | Priority |
|---|---|---|---|---|
| Data Fabric | PIT canonical datasets | CanonicalDataFabric + snapshots | Real provider corpus absent | P0 external |
| Market/Fundamentals/Valuation | Dataset contracts | Schemas/boundaries exist | Broad live/historical observations absent | P0 external |
| Universe | Historical/PIT boundary | Historical universe infrastructure | Real historical membership corpus absent | P0 external |
| PIT | Temporal fields + future rejection | Fabric + research readiness | Needs real provider/restatement corpus | P0 |
| DecisionWorld | Single decision-time object | Immutable readiness/lineage boundary | More downstream modules must migrate fully | P0/P1 |
| Evidence | Evidence graph/ledger | Conflict/future evidence handling | Real filings/news corpus absent | P1 external |
| Research | ResearchFactory readiness | Evidence/data gated | Full evidence-driven dossier requires source corpus | P1 external |
| Specialist intelligence | 15 domains + chronological models | Dependency-free logistic specialists | Richer ML backends/data needed for empirical strength | P1 external |
| Meta learning | Learned meta-model | Chronological logistic meta learner | Needs persistent outcome corpus | P1 external |
| Forecasting | Probabilistic baseline + empirical distribution | Fail-closed distribution kernel | Full return-distribution calibration needs outcomes | P1 external |
| Historical analogs | Feature/pattern architecture | Existing pattern engine | Needs long PIT history | P1 external |
| Regime | Regime features | Existing regime infrastructure | Needs real macro/sector history | P1 external |
| Risk | Portfolio/stress/correlation | Existing engines | Needs real portfolio + market covariance data | P2 |
| Paper trading | Persistent realistic paper state | Existing execution stack | Real signal stream required for track record | P2 |
| Replay | Hash/version checks | Replay + Time Machine | Full data reconstruction needs corpus | P2 |
| Attribution | Position contribution | Portfolio attribution | Forecast/component attribution can be expanded | P2 |
| Governance | Champion/challenger | Persistent registry | Artifact/model promotion wiring still needs deeper lifecycle integration | P2 |
| Observability | Health/metrics/audit | Runtime/ops modules | Needs production telemetry to validate at scale | P2 |
| Security | No live order surface, secret scan | Verified | External provider permission boundary remains | P0 safety |
| UI/UX | Institutional workstation layer | v188/v189 visual system | Full live intelligence depends on data; richer drilldowns remain | P3 |
| Autonomous ops | Scheduler/control plane | Hourly architecture | Real source ingestion is external dependency | P2 external |

## Highest-value v189 closure

The key architectural seam found in the v188 audit was the gap between **trained models existing** and **governed production inference actually consuming them from the canonical DecisionWorld**. v189 adds that boundary, adds empirical forecast distributions that fail closed, adds model artifact persistence, and makes PIT restatement selection deterministic.

## Remaining blockers

No code-only release can honestly claim real 450-security intelligence, empirical profitability, or production forecasting accuracy without actual provider observations and persistent outcome history. Those remain explicitly blocked rather than simulated.
