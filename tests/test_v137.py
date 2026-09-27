from datetime import datetime, timezone
from pathlib import Path
import tempfile
from orion.acquisition.contracts import SourceSpec, AcquisitionState, DocumentKind, AcquisitionJob
from orion.acquisition.planner import AcquisitionPlanner
from orion.acquisition.classifier import classify_document
from orion.acquisition.executor import AcquisitionExecutor
from orion.data.http_provider import PublicHTTPProvider

class FakeProvider:
    def __init__(self): self.calls=[]
    def fetch(self,url):
        from orion.data.http_provider import FetchResult
        self.calls.append(url)
        payload=b'Independent Auditor\'s Report. Basis for Opinion. Audited financial results.'
        return FetchResult(url,200,'text/plain',payload,'a'*64,'2026-09-26T10:00:00Z')

def test_planner_is_deterministic_and_deduplicates():
    src=SourceSpec('company-ir','example.com','https://example.com/discover','financial_results')
    p=AcquisitionPlanner([src])
    m1=p.plan(['B','A','A'],'2026-09-26T10:00:00Z')
    m2=p.plan(['A','B'],'2026-09-26T10:00:00Z')
    assert m1.manifest_id==m2.manifest_id and len(m1.security_ids)==2 and len(m1.jobs)==2

def test_missing_provider_is_blocked():
    m=AcquisitionPlanner([]).plan(['A'],'2026-09-26T10:00:00Z')
    assert len(m.jobs)==0 and 'A:financial_results:NO_PROVIDER' in m.blocked

def test_classifier_separates_auditor_report():
    kind,conf=classify_document("Independent Auditor's Report\nBasis for Opinion",'application/pdf')
    assert kind==DocumentKind.AUDITOR_REPORT and conf>0.7

def test_executor_blocks_unresolved_discovery():
    job=AcquisitionJob('j','A','s','financial_results','https://example.com','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',metadata={'requires_discovery':'true'})
    r=AcquisitionExecutor(FakeProvider()).run(job)
    assert r.state==AcquisitionState.BLOCKED and r.error=='URL_DISCOVERY_REQUIRED'

def test_executor_classifies_real_payload_fixture():
    job=AcquisitionJob('j','A','s','financial_results','https://example.com/file','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',metadata={})
    r=AcquisitionExecutor(FakeProvider()).run(job)
    assert r.state==AcquisitionState.PARSED and r.document_kind==DocumentKind.AUDITOR_REPORT.value and r.payload_hash=='a'*64
