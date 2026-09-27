from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReadinessReport:
    securities:int
    planned_jobs:int
    blocked_jobs:int
    provider_gaps:int
    discovery_gaps:int
    executable:bool
    reasons:tuple[str,...]

def assess(manifest):
    provider_gaps=sum(1 for x in manifest.blocked if x.endswith(':NO_PROVIDER'))
    discovery_gaps=sum(1 for j in manifest.jobs if j.metadata.get('requires_discovery')=='true')
    reasons=[]
    if provider_gaps: reasons.append(f'NO_PROVIDER:{provider_gaps}')
    if discovery_gaps: reasons.append(f'URL_DISCOVERY_REQUIRED:{discovery_gaps}')
    return ReadinessReport(len(manifest.security_ids),len(manifest.jobs),len(manifest.blocked),provider_gaps,discovery_gaps,not reasons,tuple(reasons))
