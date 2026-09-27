from orion.acquisition.contracts import SourceSpec, AcquisitionJob, AcquisitionState
from orion.acquisition.discovery import DiscoveryRegistry, DiscoveryResult
from orion.acquisition.orchestrator import AcquisitionPreparer

class Adapter:
    source_id='company-ir'; dataset='financial_results'
    def __init__(self,url='https://example.com/result.pdf'): self.url=url
    def discover(self,security_id,job_id,decision_time):
        return DiscoveryResult(job_id,self.url,self.source_id,'2026-09-26T10:00:00Z',0.97,'DISCOVERED')

def job():
    return AcquisitionJob('j1','ABC','company-ir','financial_results','https://example.com/discover','2026-09-01T00:00:00Z','2026-09-02T00:00:00Z','2026-09-03T00:00:00Z',metadata={'requires_discovery':'true'})

def test_discovery_promotes_job():
    r=DiscoveryRegistry(); r.register(Adapter()); out=AcquisitionPreparer(r).prepare(job(),'2026-09-03T00:00:00Z')
    assert out.state==AcquisitionState.PLANNED
    assert out.job.url.endswith('result.pdf')
    assert out.job.metadata['discovery_confidence']=='0.97'

def test_missing_adapter_blocks():
    out=AcquisitionPreparer(DiscoveryRegistry()).prepare(job(),'2026-09-03T00:00:00Z')
    assert out.state==AcquisitionState.BLOCKED and out.reason=='NO_DISCOVERY_ADAPTER'

def test_unsafe_discovery_blocks():
    r=DiscoveryRegistry(); r.register(Adapter('http://example.com/x'))
    out=AcquisitionPreparer(r).prepare(job(),'2026-09-03T00:00:00Z')
    assert out.state==AcquisitionState.BLOCKED and 'UNSAFE_DISCOVERED_URL' in out.reason
