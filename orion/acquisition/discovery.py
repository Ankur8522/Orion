from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

@dataclass(frozen=True)
class DiscoveryResult:
    job_id: str
    url: str | None
    source_id: str
    discovered_at: str
    confidence: float
    status: str
    reason: str | None = None

class SourceDiscoveryAdapter(Protocol):
    source_id: str
    dataset: str
    def discover(self, security_id: str, job_id: str, decision_time: str) -> DiscoveryResult: ...

class DiscoveryRegistry:
    def __init__(self): self._adapters: dict[tuple[str,str], SourceDiscoveryAdapter] = {}
    def register(self, adapter: SourceDiscoveryAdapter):
        key=(adapter.source_id, adapter.dataset)
        if key in self._adapters: raise ValueError('DUPLICATE_DISCOVERY_ADAPTER')
        self._adapters[key]=adapter
    def resolve(self, source_id: str, dataset: str):
        return self._adapters.get((source_id,dataset))

def validate_discovery(result: DiscoveryResult, allowed_host: str | None = None) -> DiscoveryResult:
    if result.status != 'DISCOVERED':
        return result
    if not result.url or not (0 <= result.confidence <= 1):
        raise ValueError('INVALID_DISCOVERY_RESULT')
    p=urlparse(result.url)
    if p.scheme != 'https' or not p.netloc:
        raise ValueError('UNSAFE_DISCOVERED_URL')
    if allowed_host and p.hostname != allowed_host:
        raise ValueError('DISCOVERED_HOST_MISMATCH')
    return result

def promote_job(job, discovery: DiscoveryResult):
    validate_discovery(discovery)
    if discovery.job_id != job.job_id or discovery.source_id != job.source_id:
        raise ValueError('DISCOVERY_JOB_MISMATCH')
    if discovery.status != 'DISCOVERED' or not discovery.url:
        raise ValueError('DISCOVERY_NOT_EXECUTABLE')
    meta=dict(job.metadata or {})
    meta.pop('requires_discovery', None)
    meta['discovered_at']=discovery.discovered_at
    meta['discovery_confidence']=str(discovery.confidence)
    from dataclasses import replace
    return replace(job, url=discovery.url, metadata=meta)
