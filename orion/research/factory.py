from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence
from datetime import datetime, timezone

REQUIRED_DATASETS = (
    'universe_membership', 'market_price', 'ohlcv', 'volume', 'corporate_actions',
    'financial_statements', 'quarterly_results', 'cash_flow', 'balance_sheet',
    'valuation', 'promoter_shareholding', 'institutional_flows', 'order_book',
    'business_visibility', 'earnings_estimates', 'sector', 'macro_sensitivity',
    'technical_history', 'forensics', 'news_evidence', 'catalysts', 'headwinds',
    'thesis', 'counter_thesis', 'scenarios', 'forecast_history', 'outcome_history'
)

@dataclass(frozen=True)
class DataRequirement:
    dataset: str
    available: bool
    source_ids: tuple[str, ...] = ()
    blocker: str | None = None
    applicable: bool = True
    evidence_state: str | None = None
    available_time: str | None = None
    effective_time: str | None = None

@dataclass(frozen=True)
class ResearchReadiness:
    security_id: str
    as_of: str
    coverage_pct: float
    ready: bool
    requirements: tuple[DataRequirement, ...]
    blockers: tuple[str, ...]
    lineage_hash: str

@dataclass(frozen=True)
class ResearchFactoryPlan:
    security_id: str
    priority: float
    readiness: ResearchReadiness
    next_actions: tuple[str, ...]

class ResearchFactory:
    def readiness_from_decision_world(self, decision_world, *, max_age_seconds: float | None = None) -> ResearchReadiness:
        """Evaluate research readiness only from the immutable DecisionWorld."""
        if decision_world is None: raise ValueError('DECISION_WORLD_REQUIRED')
        datasets = {}
        for snap in getattr(decision_world, 'datasets', ()):
            datasets[snap.dataset] = {
                'available': snap.state.value == 'READY',
                'source_ids': tuple(r.source_id for r in snap.rows),
                'available_time': snap.latest_available_time,
                'evidence_state': snap.state.value,
            }
        return self.readiness(decision_world.snapshot.security_id, decision_world.snapshot.decision_time, datasets, max_age_seconds=max_age_seconds)

    """Turns heterogeneous source availability into an auditable research plan.

    It deliberately separates readiness from inference: missing source coverage is
    never converted into a synthetic fact or an investment conclusion.
    """
    def readiness(self, security_id: str, as_of: str, datasets: Mapping[str, Mapping[str, object]], *, max_age_seconds: float | None = None) -> ResearchReadiness:
        req=[]; blockers=[]
        for name in REQUIRED_DATASETS:
            raw=datasets.get(name, {}) or {}
            applicable=bool(raw.get('applicable', True))
            available=bool(raw.get('available'))
            sources=tuple(str(x) for x in raw.get('source_ids', ()) if x)
            evidence_state = str(raw.get('evidence_state')) if raw.get('evidence_state') is not None else None
            available_time = raw.get('available_time')
            effective_time = raw.get('effective_time')
            timing_blocker = None
            if applicable and available_time:
                try:
                    av = datetime.fromisoformat(str(available_time).replace('Z','+00:00'))
                    cutoff = datetime.fromisoformat(str(as_of).replace('Z','+00:00'))
                    if av.tzinfo is None: av=av.replace(tzinfo=timezone.utc)
                    if cutoff.tzinfo is None: cutoff=cutoff.replace(tzinfo=timezone.utc)
                    av=av.astimezone(timezone.utc); cutoff=cutoff.astimezone(timezone.utc)
                    if av > cutoff: timing_blocker='FUTURE_AVAILABLE_TIME'
                    elif max_age_seconds is not None and max_age_seconds >= 0 and (cutoff-av).total_seconds() > max_age_seconds: timing_blocker='STALE_EVIDENCE'
                except (TypeError, ValueError):
                    timing_blocker='INVALID_AVAILABLE_TIME'
            if applicable and effective_time:
                try:
                    ev = datetime.fromisoformat(str(effective_time).replace('Z','+00:00'))
                    cutoff = datetime.fromisoformat(str(as_of).replace('Z','+00:00'))
                    if ev.tzinfo is None: ev=ev.replace(tzinfo=timezone.utc)
                    if cutoff.tzinfo is None: cutoff=cutoff.replace(tzinfo=timezone.utc)
                    if ev.astimezone(timezone.utc) > cutoff.astimezone(timezone.utc): timing_blocker='FUTURE_EFFECTIVE_TIME'
                except (TypeError, ValueError):
                    timing_blocker='INVALID_EFFECTIVE_TIME'
            if applicable and evidence_state in {'CONTRADICTED','UNRESOLVED'}:
                timing_blocker='EVIDENCE_'+evidence_state
            if not applicable:
                blocker=None
                effective_available=True
            else:
                blocker=timing_blocker or (None if available and sources else ('NO_SOURCE_EVIDENCE' if not sources else 'DATASET_UNAVAILABLE'))
                effective_available=available and bool(sources) and timing_blocker is None
            req.append(DataRequirement(name, effective_available, sources, blocker, applicable, evidence_state, None if available_time is None else str(available_time), None if effective_time is None else str(effective_time)))
            if blocker: blockers.append(f'{name}:{blocker}')
        coverage=round(sum(r.available for r in req)/len(req)*100,2)
        payload={'security_id':security_id,'as_of':as_of,'requirements':[r.__dict__ for r in req],'blockers':blockers}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return ResearchReadiness(security_id,as_of,coverage,not blockers,tuple(req),tuple(blockers),lineage)

    def plan(self, security_id: str, as_of: str, datasets: Mapping[str, Mapping[str, object]], priority: float=0.0) -> ResearchFactoryPlan:
        r=self.readiness(security_id,as_of,datasets)
        actions=[]
        if not r.ready:
            for b in r.blockers: actions.append('ACQUIRE:'+b.split(':',1)[0])
            actions.append('HOLD_DOSSIER_UNTIL_EVIDENCE_COMPLETE')
        else:
            actions.extend(('BUILD_RESEARCH_DOSSIER','RUN_ADVERSARIAL_REVIEW','RUN_COUNTERFACTUAL_SCENARIOS','UPDATE_FORECAST'))
        return ResearchFactoryPlan(security_id,float(priority),r,tuple(dict.fromkeys(actions)))
