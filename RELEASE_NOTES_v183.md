# ORION v183.0.0 — Unified PIT Temporal & Historical Universe Provenance

## Verified changes
- Added canonical `TemporalLineage` for source/effective/available/ingestion timestamps.
- Hardened provider observations against impossible source/availability/ingestion ordering.
- Hardened PIT observations with source and ingestion lineage while preserving backward compatibility.
- Hardened corporate-action normalization with source and ingestion timestamps.
- Historical universe snapshots now bind selected membership provenance (`source_id` + `content_hash`) into snapshot lineage.
- Added regression coverage for temporal ordering and historical-universe provenance.
- Live trading remains disabled; no synthetic market data added.

## Validation
- Full pytest suite passes.
- Python compile check required before release.
- Clean extraction regression required before release.
