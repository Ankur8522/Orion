from decimal import Decimal
from orion.documents.ingest import DocumentIngestor
from orion.data.normalize import FinancialNormalizer
from orion.brain.state import BrainStateBuilder, EvidenceState
from orion.ops.integrity import canonical_hash, verify_chain
from orion.data.store import SQLiteStore

def test_document_hash_and_chunks():
    a=DocumentIngestor().ingest_bytes(b'abc','nse','S1','text/plain','2026-01-01T00:00:00Z')
    c=DocumentIngestor().text_chunks(a,'Revenue increased materially.','2026-01-02T00:00:00Z',100)
    assert a.content_hash and c[0].document_id==a.document_id and c[0].security_id=='S1'

def test_normalizer_decimal():
    x=FinancialNormalizer().normalize({'security_id':'S1','metric':'revenue','period_end':'2026-03-31','value':'10.25','unit':'INR','currency':'INR','source_id':'nse','available_time':'2026-05-01T00:00:00Z'})
    assert x.value==Decimal('10.25')

def test_brain_state_fingerprint():
    x=BrainStateBuilder().build('S1','2026-06-01T00:00:00Z',['revenue up'],['e1'])
    assert x.state==EvidenceState.SUPPORTED and len(x.fingerprint)==64

def test_brain_blocks_without_evidence():
    x=BrainStateBuilder().build('S1','2026-06-01T00:00:00Z',['claim'],[],['NO_EVIDENCE'])
    assert x.state==EvidenceState.BLOCKED

def test_integrity_chain():
    assert verify_chain([{'a':1},{'b':2}]) != verify_chain([{'a':1},{'b':3}])
    assert len(canonical_hash({'x':1}))==64

def test_persistent_v130_records(tmp_path):
    s=SQLiteStore(tmp_path/'o.db')
    s.source_capture('c1','nse','https://example.com/a','a'*64,'2026-01-01T00:00:00Z','text/html',3)
    s.normalized_financial({'security_id':'S1','metric':'pat','period_end':'2026-03-31','value':'12.5','unit':'INR','currency':'INR','source_id':'nse','available_time':'2026-05-01T00:00:00Z'})
    st=BrainStateBuilder().build('S1','2026-06-01T00:00:00Z',['pat'],['e1'])
    s.thesis_state(st)
    assert s.db.execute('select count(*) from source_captures').fetchone()[0]==1
    assert s.db.execute('select count(*) from normalized_financials').fetchone()[0]==1
    assert s.db.execute('select count(*) from thesis_states').fetchone()[0]==1

def test_api_limits_and_idempotency():
    from orion.app.api import API,RequestContext
    a=API(max_ids=2,rate_limit=5)
    c=RequestContext('u','r','analyst'); x=a.research_request(c,['S1','S1']); assert x['count']==1
    assert a.research_request(c,['S1','S1'])==x
    import pytest
    with pytest.raises(ValueError): a.research_request(RequestContext('u','r2','analyst'),['1','2','3'])

def test_thesis_delta():
    from orion.brain.state import BrainStateBuilder
    from orion.brain.delta import compare
    b=BrainStateBuilder(); p=b.build('S','2026-01-01T00:00:00Z',['a'],['e1']); c=b.build('S','2026-02-01T00:00:00Z',['a','b'],['e1','e2'])
    d=compare(p,c); assert d.changed and d.added_claims==('b',) and d.added_evidence==('e2',)
