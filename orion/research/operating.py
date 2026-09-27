from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from .factory import ResearchFactory, REQUIRED_DATASETS, ResearchFactoryPlan
from .priority import PriorityEngine
from .production_batch import ProductionResearchBatch, ProductionBatchReport

@dataclass(frozen=True)
class ResearchOperatingPlan:
    security_ids: tuple[str, ...]
    plans: tuple[ResearchFactoryPlan, ...]
    ready_count: int
    blocked_count: int
    coverage_pct: float

class ResearchOperatingCoordinator:
    """Truth-bound bridge from dataset readiness to the production research factory."""
    def __init__(self, factory: ResearchFactory | None = None, batch: ProductionResearchBatch | None = None):
        self.factory=factory or ResearchFactory(); self.batch=batch or ProductionResearchBatch(); self.priority_engine=PriorityEngine()

    def plan(self, security_ids: Sequence[str], *, as_of: str, datasets: Mapping[str, Mapping[str, Mapping[str, object]]], priorities: Mapping[str,float] | None=None) -> ResearchOperatingPlan:
        ids=tuple(dict.fromkeys(security_ids)); priorities=dict(priorities or {})
        # If an explicit priority is absent, derive it from observed information-value signals.
        for sid in ids:
            if sid not in priorities:
                ctx=datasets.get(sid,{}) or {}
                priorities[sid]=self.priority_engine.score(
                    sid,
                    data_gap=1.0 if any(not bool((ctx.get(k) or {}).get('available')) for k in REQUIRED_DATASETS) else 0.0,
                    thesis_change=float(ctx.get('thesis_change',0.0)),
                    event_urgency=float(ctx.get('event_urgency',0.0)),
                    portfolio_exposure=float(ctx.get('portfolio_exposure',0.0)),
                    evidence_risk=float(ctx.get('evidence_risk',0.0)),
                    market_signal=float(ctx.get('market_signal',0.0)),
                ).score
        rows=tuple(self.factory.plan(sid,as_of,datasets.get(sid,{}),float(priorities.get(sid,0.0))) for sid in ids)
        rows=tuple(sorted(rows, key=lambda x:(-x.priority, x.security_id)))
        ordered_ids=tuple(x.security_id for x in rows)
        ready=sum(x.readiness.ready for x in rows); coverage=sum(x.readiness.coverage_pct for x in rows)/len(rows) if rows else 0.0
        return ResearchOperatingPlan(ordered_ids,rows,ready,len(rows)-ready,round(coverage,2))

    def run(self, security_ids: Sequence[str], *, as_of: str, datasets: Mapping[str, Mapping[str, Mapping[str, object]]], contexts: Mapping[str, Mapping[str,Any]] | None=None, priorities: Mapping[str,float] | None=None) -> tuple[ResearchOperatingPlan, ProductionBatchReport]:
        plan=self.plan(security_ids,as_of=as_of,datasets=datasets,priorities=priorities)
        enriched=dict(contexts or {})
        for sid,row in zip(plan.security_ids,plan.plans):
            ctx=dict(enriched.get(sid,{})); ctx.setdefault('evidence_blockers',row.readiness.blockers); enriched[sid]=ctx
        return plan,self.batch.run(plan.security_ids,as_of=as_of,contexts=enriched)
