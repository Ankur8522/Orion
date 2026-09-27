# ORION v173 — Persistent Acquisition Scheduler

## Upgrade
Added a deterministic, persistent scheduler over the v171/v172 450-slot market acquisition planner/executor.

- batch-level checkpointing and resumability
- bounded batch execution per run
- durable scheduler state in SQLite
- explicit COMPLETE/PARTIAL/BLOCKED states
- new `/api/acquisition/schedule` read surface
- no concurrency or live trading introduced
- release identity synchronized to v173

## Validation
- full pytest suite: recorded in release manifest
- compileall
- scheduler checkpoint/resume regression
- clean extraction/import validation
- PIT and paper-safety preserved
