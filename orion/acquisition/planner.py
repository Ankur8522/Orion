from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from .contracts import AcquisitionJob, SourceSpec, DocumentKind

@dataclass(frozen=True)
class ResearchManifest:
    manifest_id:str
    decision_time:str
    universe_name:str
    security_ids:tuple[str,...]
    jobs:tuple[AcquisitionJob,...]
    blocked:tuple[str,...]

class AcquisitionPlanner:
    """Deterministic planner. It creates jobs only; it never fabricates provider data."""
    def __init__(self,sources:Iterable[SourceSpec]):
        self.sources=tuple(sorted((s for s in sources if s.enabled),key=lambda s:(s.dataset,s.priority,s.source_id)))
    def plan(self,security_ids:Iterable[str],decision_time:str,universe_name='research_3000cr') -> ResearchManifest:
        ids=tuple(sorted(dict.fromkeys(security_ids)))
        jobs=[]; blocked=[]
        datasets=('financial_results','corporate_disclosures')
        for sid in ids:
            for dataset in datasets:
                candidates=[s for s in self.sources if s.dataset==dataset]
                if not candidates:
                    blocked.append(f'{sid}:{dataset}:NO_PROVIDER')
                    continue
                src=candidates[0]
                # URL discovery is deliberately provider-specific; planner emits a contract URL placeholder only.
                # Execution adapters must replace it with a discovered, validated URL before fetching.
                job_id=sha256(f'{sid}|{dataset}|{src.source_id}|{decision_time}'.encode()).hexdigest()
                jobs.append(AcquisitionJob(job_id,sid,src.source_id,dataset,src.base_url,decision_time,decision_time,decision_time,metadata={'requires_discovery':'true'}))
        manifest_id=sha256('|'.join([universe_name,decision_time,*ids]).encode()).hexdigest()
        return ResearchManifest(manifest_id,decision_time,universe_name,ids,tuple(jobs),tuple(blocked))
