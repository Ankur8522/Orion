# ORION v174 — Governed Instrument Mapping + Acquisition Readiness

## Upgrade
- Added a durable, point-in-time instrument mapping registry.
- Mapping records require provider, instrument key, effective interval, availability time, source lineage and content hash.
- Added PIT-safe mapping resolution; future-available mappings cannot satisfy an earlier decision time.
- Added explicit acquisition readiness reporting for mapped vs blocked securities.
- Added read-only `/api/acquisition/readiness` and `/api/acquisition/mappings` surfaces.
- Preserved the v173 planner, scheduler, executor, PIT corpus and live-trading-off boundary.

## Validation
- Full pytest suite and compile checks recorded in release manifest.
- Mapping PIT and missing-mapping safety regression coverage added.
