from __future__ import annotations
from dataclasses import dataclass
from .autonomous import AutonomousRuntime

@dataclass(frozen=True)
class ResearchPlan:
    job_keys: tuple[str,...]
    security_order: tuple[str,...]
    chunk_size: int
    rationale: str

class UniverseResearchScheduler:
    """Deterministic universe scheduler: priority first, stable tie-break, bounded chunks."""
    def __init__(self, runtime: AutonomousRuntime | None = None): self.runtime=runtime or AutonomousRuntime()
    def plan(self, security_ids, *, priorities=None, chunk_size=50) -> ResearchPlan:
        if chunk_size<1: raise ValueError('INVALID_CHUNK_SIZE')
        priorities=priorities or {}; ids=tuple(dict.fromkeys(security_ids))
        ordered=tuple(sorted(ids,key=lambda x:(-float(priorities.get(x,0.0)),str(x))))
        keys=self.runtime.enqueue_universe(ordered,chunk_size=chunk_size)
        return ResearchPlan(keys,ordered,chunk_size,'PRIORITY_SORTED_STABLE_BATCHING')
