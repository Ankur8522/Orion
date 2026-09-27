from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence, Callable, Any
from orion.learning.feedback import ForecastLedger, ForecastRecord
from orion.learning.outcome_resolver import ForecastOutcomeResolver, ObservableOutcome, ResolutionReport
from orion.learning.model_registry import ChampionChallengerRegistry, ModelDecision, ModelScore
from orion.ops.time_machine import TimeMachine, ReplayResult
from orion.portfolio.attribution import PortfolioAttribution, PortfolioAttributionEngine
from orion.research.queue import ResearchQueue, Status

@dataclass(frozen=True)
class AutonomousCycleReport:
    queued_jobs: int
    resolved_forecasts: int
    model_decision: ModelDecision
    attribution: PortfolioAttribution | None
    replay: ReplayResult

class AutonomousRuntime:
    """Coordinates recurring research, feedback, attribution and replay without trading."""
    def __init__(self):
        self.queue=ResearchQueue(); self.resolver=ForecastOutcomeResolver(); self.models=ChampionChallengerRegistry()
        self.time_machine=TimeMachine(); self.attribution_engine=PortfolioAttributionEngine()

    def enqueue_universe(self, security_ids: Sequence[str], *, chunk_size: int=50) -> tuple[str,...]:
        if chunk_size<1: raise ValueError('INVALID_CHUNK_SIZE')
        ids=tuple(dict.fromkeys(security_ids)); keys=[]
        for i in range(0,len(ids),chunk_size): keys.append(self.queue.enqueue(ids[i:i+chunk_size]).key)
        return tuple(keys)

    def cycle(self, *, ledger: ForecastLedger, observations: Sequence[ObservableOutcome], evaluation_time: str,
              model_scores: Sequence[ModelScore]=(), attribution_rows: Sequence[tuple[str,float,float]]=(), state: Mapping[str,Any]|None=None) -> AutonomousCycleReport:
        resolution=self.resolver.resolve(ledger,observations,evaluation_time=evaluation_time)
        model_decision=self.models.update(model_scores)
        attribution=self.attribution_engine.attribute(attribution_rows) if attribution_rows else None
        snapshot=dict(state or {}); snapshot.update({'resolved_forecasts':resolution.resolved,'champion_model':model_decision.champion,'attribution_return':attribution.total_return_pct if attribution else None})
        replay=self.time_machine.record(evaluation_time,evaluation_time,snapshot)
        rr=self.time_machine.replay()
        return AutonomousCycleReport(len(self.queue.jobs),resolution.resolved,model_decision,attribution,rr)
