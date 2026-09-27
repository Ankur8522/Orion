from orion.acquisition.contracts import SourceSpec
from orion.acquisition.planner import AcquisitionPlanner
from orion.acquisition.readiness import assess
from orion.data.store import SQLiteStore

def test_manifest_persists_and_readiness_blocks_unresolved_discovery(tmp_path):
    store=SQLiteStore(tmp_path/'orion.db')
    src=SourceSpec('ir','example.com','https://example.com/discover','financial_results')
    m=AcquisitionPlanner([src]).plan(['A','B'],'2026-09-26T10:00:00Z')
    store.acquisition_manifest(m,'2026-09-26T10:01:00Z')
    assert len(store.acquisition_jobs(m.manifest_id))==2
    r=assess(m)
    assert not r.executable and r.discovery_gaps==2
    store.close()
