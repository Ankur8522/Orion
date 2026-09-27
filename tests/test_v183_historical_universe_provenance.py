from orion.data.historical_universe import HistoricalUniverseRegistry
from orion.data.universe_contract import UniverseMembership
from orion.data.store import SQLiteStore

def test_snapshot_binds_membership_source_provenance(tmp_path):
    store=SQLiteStore(str(tmp_path/'d.db'))
    reg=HistoricalUniverseRegistry(store)
    m=UniverseMembership('ABC','NIFTY50',True,'2025-01-01T00:00:00Z',None,'2025-01-02T00:00:00Z')
    reg.upsert(m,source_id='official',content_hash='a'*64)
    snap=reg.snapshot('2025-02-01T00:00:00Z')
    assert snap.provenance[0]['source_id']=='official'
    assert snap.provenance[0]['content_hash']=='a'*64
    assert len(snap.lineage_hash)==64
