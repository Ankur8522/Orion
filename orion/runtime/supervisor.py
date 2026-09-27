from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence

@dataclass(frozen=True)
class SupervisorStep:
    name: str
    status: str
    detail: str

@dataclass(frozen=True)
class SupervisorReport:
    started_at: str
    finished_at: str
    steps: tuple[SupervisorStep,...]
    status: str

class RuntimeSupervisor:
    """Bounded orchestration shell; never fabricates missing data or enables live trading."""
    def __init__(self, *, max_steps: int=8):
        if max_steps<1: raise ValueError('INVALID_MAX_STEPS')
        self.max_steps=max_steps
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    def run(self, steps: Sequence[tuple[str,Callable[[],str]]]) -> SupervisorReport:
        start=self.now(); out=[]
        for name,fn in tuple(steps)[:self.max_steps]:
            try: out.append(SupervisorStep(name,'OK',str(fn())))
            except Exception as exc: out.append(SupervisorStep(name,'FAILED',type(exc).__name__+':'+str(exc)))
        status='OK' if all(x.status=='OK' for x in out) else 'DEGRADED'
        return SupervisorReport(start,self.now(),tuple(out),status)
