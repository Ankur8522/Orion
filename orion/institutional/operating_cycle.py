from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json, time
from typing import Any, Iterable, Mapping, Sequence
from orion.learning.outcome_resolver import ObservableOutcome, ResolutionReport, ForecastOutcomeResolver
from orion.learning.model_registry import ModelScore, ModelDecision
from orion.portfolio.attribution import PortfolioAttribution, PortfolioAttributionEngine
from orion.portfolio.performance import PortfolioPerformanceEngine, PerformanceSummary
from orion.ops.time_machine import TimeMachine, ReplayResult
from orion.data.universe_contract import InstitutionalUniverseContract, UniverseMembership, UniverseCoverage
from orion.intelligence.decision_pipeline import DecisionIntelligenceEngine, IntelligenceResult
from orion.intelligence.decision_world import DecisionWorld
from orion.learning.specialist_models import ChronologicalLogisticSpecialist
from orion.learning.meta_intelligence import LearnedMetaIntelligence

@dataclass(frozen=True)
class InstitutionalCycleReport:
    run_id: str
    started_at: str
    finished_at: str
    duration_ms: float
    universe: UniverseCoverage
    resolved_forecasts: int
    resolution: ResolutionReport
    model_decision: ModelDecision
    attribution: PortfolioAttribution | None
    performance: PerformanceSummary | None
    replay: ReplayResult
    status: str
    processed_count: int
    blocked_count: int
    dependency_count: int
    errors: tuple[str,...]
    lineage_hash: str
    intelligence: IntelligenceResult | None = None

class InstitutionalOperatingCycle:
    """One bounded, observable feedback cycle across existing domain engines.

    It deliberately orchestrates existing engines instead of creating another brain.
    External acquisition/research stages may be blocked; their state is reported rather
    than bypassed or fabricated.
    """
    def __init__(self, *, universe=None, resolver=None, attribution=None, performance=None, time_machine=None, intelligence=None):
        self.universe=universe or InstitutionalUniverseContract(); self.resolver=resolver or ForecastOutcomeResolver(); self.attribution=attribution or PortfolioAttributionEngine(); self.performance=performance or PortfolioPerformanceEngine(); self.time_machine=time_machine or TimeMachine(); self.intelligence=intelligence or DecisionIntelligenceEngine()
    def run(self, *, memberships: Iterable[UniverseMembership], ledger, observations: Sequence[ObservableOutcome], evaluation_time: str, model_registry, model_scores: Sequence[ModelScore]=(), attribution_rows: Sequence[tuple[str,float,float]]=(), nav_rows: Sequence[tuple[str,float]]=(), state: Mapping[str,Any]|None=None, decision_world: DecisionWorld | None = None, specialist_models: Mapping[str, ChronologicalLogisticSpecialist] | None = None, meta_model: LearnedMetaIntelligence | None = None, required_specialists: Sequence[str] = (), evidence_count: int = 0, regime: str = 'UNKNOWN') -> InstitutionalCycleReport:
        started=datetime.now(timezone.utc); t=time.perf_counter(); evaluation_time = datetime.fromisoformat(evaluation_time.replace('Z','+00:00')).astimezone(timezone.utc).isoformat().replace('+00:00','Z'); run_id=sha256(f'{evaluation_time}|{len(tuple(memberships))}'.encode()).hexdigest()[:20]
        errors=[]; members=tuple(memberships); universe=self.universe.coverage(members,as_of=evaluation_time)
        resolution=self.resolver.resolve(ledger,observations,evaluation_time=evaluation_time)
        decision=model_registry.update(model_scores) if model_scores else model_registry.update(())
        attr=self.attribution.attribute(attribution_rows) if attribution_rows else None; perf=self.performance.summarize(nav_rows) if nav_rows else None
        intelligence_result = None
        if decision_world is not None:
            intelligence_result = self.intelligence.infer(decision_world, specialist_models or {}, meta_model=meta_model, required_specialists=required_specialists, evidence_count=evidence_count, regime=regime)
        blocked=sum(1 for x in universe.missing_memberships.values() if x); dependency=1 if (not observations and len(ledger.forecasts())>len(ledger.outcomes())) else 0
        snapshot=dict(state or {}); snapshot.update({'run_id':run_id,'universe':universe.__dict__,'resolved_forecasts':resolution.resolved,'champion_model':decision.champion,'attribution_return':attr.total_return_pct if attr else None,'intelligence_status': intelligence_result.status if intelligence_result else None,'intelligence_lineage': intelligence_result.lineage_hash if intelligence_result else None,'performance_return':perf.total_return_pct if perf else None,'status':'READY' if universe.status=='READY' else ('PARTIAL' if universe.status=='PARTIAL' else 'BLOCKED')})
        cycle_id=f'cycle:{run_id}'
        self.time_machine.record(cycle_id,evaluation_time,snapshot); replay=self.time_machine.replay()
        status='READY' if universe.status=='READY' and not dependency else ('PARTIAL' if universe.status!='BLOCKED' else 'BLOCKED')
        finished=datetime.now(timezone.utc); duration=(time.perf_counter()-t)*1000
        payload={'run_id':run_id,'started_at':started.isoformat(),'finished_at':finished.isoformat(),'duration_ms':round(duration,3),'status':status,'processed_count':universe.unique_securities,'blocked_count':blocked,'dependency_count':dependency,'errors':errors,'replay_hash':replay.lineage_hash}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return InstitutionalCycleReport(run_id,started.isoformat().replace('+00:00','Z'),finished.isoformat().replace('+00:00','Z'),round(duration,3),universe,resolution.resolved,resolution,decision,attr,perf,replay,status,universe.unique_securities,blocked,dependency,tuple(errors),lineage,intelligence_result)
