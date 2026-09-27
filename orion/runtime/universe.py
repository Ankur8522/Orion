from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from orion.research.production_batch import ProductionBatchReport, ProductionResearchBatch
from orion.runtime.control_plane import OrionControlPlane, RuntimeResult
from orion.runtime.scheduler import ResearchPlan, UniverseResearchScheduler


@dataclass(frozen=True)
class UniverseCycleReport:
    plan: ResearchPlan
    research: ProductionBatchReport
    intelligence_runs: int
    blocked: int
    failed: int
    status: str


class UniverseOperatingRuntime:
    """Connects universe scheduling, production research and decision runtime.

    It never fabricates company models or market facts. Missing context is
    surfaced as BLOCKED and can be retried after data acquisition completes.
    """
    def __init__(self, *, control_plane: OrionControlPlane | None = None,
                 research: ProductionResearchBatch | None = None,
                 scheduler: UniverseResearchScheduler | None = None):
        self.control_plane = control_plane or OrionControlPlane()
        self.research = research or ProductionResearchBatch()
        self.scheduler = scheduler or UniverseResearchScheduler()

    def plan(self, security_ids: Sequence[str], *, priorities: Mapping[str, float] | None = None,
             chunk_size: int = 50) -> ResearchPlan:
        return self.scheduler.plan(security_ids, priorities=priorities, chunk_size=chunk_size)

    def research_cycle(self, security_ids: Sequence[str], *, as_of: str,
                       priorities: Mapping[str, float] | None = None,
                       chunk_size: int = 50,
                       contexts: Mapping[str, Mapping[str, Any]] | None = None) -> UniverseCycleReport:
        plan = self.plan(security_ids, priorities=priorities, chunk_size=chunk_size)
        report = self.research.run(plan.security_order, as_of=as_of, contexts=contexts)
        status = "COMPLETE" if report.failed == 0 and report.blocked == 0 else ("PARTIAL" if report.complete else "BLOCKED")
        return UniverseCycleReport(plan, report, 0, report.blocked, report.failed, status)

    def run_cases(self, cases: Sequence[Any]) -> tuple[RuntimeResult, ...]:
        return tuple(self.control_plane.run_case(case) for case in cases)

    def health(self) -> dict:
        h = self.control_plane.health()
        h.update({"runtime": "UNIVERSE_OPERATING_RUNTIME", "live_trading_enabled": False})
        return h
