# ORION v172 — Resumable Market Acquisition Executor + Dataset Coverage Ledger

- Added resumable persistent `MarketBatchExecutor` for the read-only market-data bridge.
- Added per-manifest/dataset/security coverage ledger with PIT-bounded observations.
- PROMOTED jobs are skipped on rerun; each execution state is checkpointed.
- Added regression coverage for resumability and durable coverage state.
- Release identity synchronized to v172.0.0.
- Live trading remains disabled; no synthetic market data introduced.

Validation: 215 tests passed; compileall passed; read-only acquisition safety preserved; package hash recorded externally.
