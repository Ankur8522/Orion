from decimal import Decimal
import pytest
from orion.analytics.calculations import derive
from orion.data.store import SQLiteStore
from orion.execution.vertical_slice import ResearchExecution, Capture
from orion.financials.statement import StatementMapper

def test_safe_formula_and_lineage():
    r=derive('S1','margin','pat/revenue',{'pat':Decimal('20'),'revenue':Decimal('100')},source_ids=['e2','e1'])
    assert r.value == Decimal('0.200000') and r.source_ids==('e1','e2')

def test_formula_rejects_attribute_access():
    with pytest.raises(ValueError): derive('S1','x','pat.real.__class__',{'pat':Decimal('2')})

def test_vertical_capture_evidence_and_financials(tmp_path):
    store=SQLiteStore(tmp_path/'o.db'); ex=ResearchExecution(store)
    cap=Capture('company-ir','https://example.com/r','S1',b'Q1 revenue 100; PAT 20','2026-01-02T00:00:00Z','text/plain')
    art=ex.capture(cap); chunks=ex.ingest_text(art,'Q1 revenue 100; PAT 20','2026-01-02T00:00:00Z')
    assert chunks and len(store.evidence_for('S1','2026-01-03T00:00:00Z'))==len(chunks)
    facts=ex.ingest_financial_facts([{'label':'Revenue','security_id':'S1','period_end':'2025-12-31','value':'100','unit':'INR','currency':'INR','source_id':'company-ir','available_time':'2026-01-02T00:00:00Z','evidence_id':'e1'}],'2026-01-03T00:00:00Z')
    assert facts[0].metric=='revenue'
    store.close()
