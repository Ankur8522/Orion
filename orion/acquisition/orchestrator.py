from __future__ import annotations
from dataclasses import dataclass
from .contracts import AcquisitionState
from .discovery import DiscoveryRegistry, DiscoveryResult, promote_job

@dataclass(frozen=True)
class PreparationResult:
    job_id: str
    state: AcquisitionState
    job: object
    discovery: DiscoveryResult | None
    reason: str | None = None

class AcquisitionPreparer:
    def __init__(self, registry: DiscoveryRegistry): self.registry=registry
    def prepare(self, job, decision_time: str) -> PreparationResult:
        adapter=self.registry.resolve(job.source_id, job.dataset)
        if adapter is None:
            return PreparationResult(job.job_id, AcquisitionState.BLOCKED, job, None, 'NO_DISCOVERY_ADAPTER')
        result=adapter.discover(job.security_id,job.job_id,decision_time)
        if result.status!='DISCOVERED':
            return PreparationResult(job.job_id,AcquisitionState.BLOCKED,job,result,result.reason or 'DISCOVERY_FAILED')
        try:
            promoted=promote_job(job,result)
        except Exception as e:
            return PreparationResult(job.job_id,AcquisitionState.BLOCKED,job,result,type(e).__name__+':'+str(e))
        return PreparationResult(job.job_id,AcquisitionState.PLANNED,promoted,result)
