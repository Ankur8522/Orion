from __future__ import annotations
from dataclasses import dataclass
from .sector import SectorMetricEngine
from .forensics import ForensicEngine
from .priority import PriorityEngine
from ..portfolio.health import assess as assess_health

@dataclass(frozen=True)
class StockResearch:
    security_id: str
    status: str
    metrics: object
    forensic: tuple
    thesis_health: object
    priority: object

class StockResearchExecutor:
    """Runs one deterministic stock through the research stack after PIT evidence gating."""
    def __init__(self, pipeline, *, sector_engine=None, forensic=None, priority=None):
        self.pipeline=pipeline; self.sector=sector_engine or SectorMetricEngine(); self.forensic=forensic or ForensicEngine(); self.priority=priority or PriorityEngine()
    def run(self, security_id, decision_time, *, sector='generic', facts=None, opinions=(), blockers=(), exposure_weight=0.0):
        decision=self.pipeline.run_one(security_id,decision_time,opinions=opinions,blockers=blockers)
        metrics=self.sector.run(security_id,sector,facts or {})
        findings=self.forensic.inspect(metrics.metrics)
        health=assess_health(security_id,decision.thesis_state,len(decision.review.get('evidence_ids',())),bool(metrics.warnings or findings))
        priority=self.priority.score(security_id,data_gap=bool(metrics.warnings),thesis_change=bool(decision.thesis_state.claims),event_urgency=0,portfolio_exposure=float(exposure_weight),evidence_risk=bool(findings))
        return StockResearch(security_id,decision.status,metrics,findings,health,priority)
