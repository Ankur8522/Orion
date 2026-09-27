from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from .state_store import RuntimeStateStore
from .persistent_queue import PersistentResearchQueue
from .universe import UniverseOperatingRuntime

@dataclass(frozen=True)
class OperatingSnapshot:
    status:str; research_jobs:int; active_jobs:int; alerts:int; cycles:int; live_trading_enabled:bool

class OrionOperatingSystem:
    """Top-level operating layer: scheduling, durable state, health and safe lifecycle."""
    def __init__(self, state_path=':memory:', queue_path=':memory:', universe=None):
        self.store=RuntimeStateStore(state_path); self.queue=PersistentResearchQueue(queue_path)
        self.universe=universe or UniverseOperatingRuntime()
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    def enqueue(self, security_ids:Sequence[str], *, chunk_size=50, priorities:Mapping[str,float]|None=None):
        plan=self.universe.plan(security_ids,priorities=priorities,chunk_size=chunk_size)
        ordered=plan.security_order
        for i in range(0,len(ordered),plan.chunk_size):
            self.queue.enqueue(ordered[i:i+plan.chunk_size])
        self.store.event(self.now(),'RESEARCH_ENQUEUED',{'count':len(plan.security_order),'job_keys':plan.job_keys})
        return plan
    def snapshot(self):
        jobs=self.queue.jobs(); cycles=self.store.cycles(); alerts=self.store.alerts()
        active=sum(j.status.value=='RUNNING' for j in jobs)
        return OperatingSnapshot('OK' if not any(a['severity']=='CRITICAL' for a in alerts) else 'DEGRADED',len(jobs),active,len(alerts),len(cycles),False)
    def close(self): self.store.close(); self.queue._db.close()
