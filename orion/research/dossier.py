from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence, Mapping, Any

from ..company.model import CompanyModel
from ..company.snapshot import ResearchSnapshot, build_research_snapshot
from ..company.valuation import ValuationSnapshot, derive_valuation
from ..research.sector import MetricSnapshot, SectorMetricEngine
from ..research.market_signals import MarketSignal, analyze as analyze_market
from ..portfolio.impact import PortfolioImpact, assess as assess_portfolio
from ..brain.state import ThesisState, BrainStateBuilder
from ..brain.delta import ThesisDelta, compare as compare_thesis
from ..evidence.ledger import EvidenceRecord
from ..evidence.adjudication import EvidenceAdjudicator

D = Decimal

@dataclass(frozen=True)
class EvidenceBundle:
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return bool(self.evidence_ids) and not self.blockers and all(s == 'EVIDENCE_SUPPORTED' for s in self.states or ('EVIDENCE_SUPPORTED',))

@dataclass(frozen=True)
class ResearchDossier:
    security_id: str
    as_of: str
    company: ResearchSnapshot
    sector: MetricSnapshot
    market: MarketSignal
    portfolio: PortfolioImpact | None
    thesis: ThesisState
    thesis_delta: ThesisDelta | None
    evidence: EvidenceBundle
    catalysts: tuple[str, ...]
    headwinds: tuple[str, ...]
    change_log: tuple[str, ...]
    warnings: tuple[str, ...]


def _claims(company: ResearchSnapshot, sector: MetricSnapshot, market: MarketSignal, catalysts: Sequence[str], headwinds: Sequence[str]) -> tuple[str, ...]:
    claims = []
    for key in ('revenue_growth','ebitda_growth','pat_growth','cfo_growth','fcf_growth'):
        value = company.growth.get(key)
        if value is not None:
            claims.append(f'{key}={value}')
    for flag in company.quality_flags:
        claims.append(f'FLAG:{flag}')
    for warning in sector.warnings:
        if warning.startswith('MISSING_'):
            continue
        claims.append(f'SECTOR:{warning}')
    if market.breakout:
        claims.append('TECHNICAL:BREAKOUT')
    if market.trend != 'UNKNOWN':
        claims.append(f'TECHNICAL:TREND_{market.trend}')
    claims.extend(f'CATALYST:{x}' for x in catalysts)
    claims.extend(f'HEADWIND:{x}' for x in headwinds)
    return tuple(sorted(set(claims)))


def _warnings(company: ResearchSnapshot, sector: MetricSnapshot, market: MarketSignal, evidence: EvidenceBundle) -> tuple[str, ...]:
    out = list(company.warnings) + list(company.quality_flags) + list(sector.warnings) + list(market.warnings) + list(evidence.blockers)
    if evidence.evidence_ids and not evidence.usable:
        out.append('EVIDENCE_REVIEW_REQUIRED')
    if not evidence.evidence_ids:
        out.append('NO_EVIDENCE_LINKED')
    return tuple(sorted(set(out)))


def build_research_dossier(
    model: CompanyModel,
    *,
    as_of: str,
    sector: str = 'generic',
    sector_facts: Mapping[str, Any] | None = None,
    market_rows: Sequence[Mapping[str, Any]] = (),
    valuation_kwargs: Mapping[str, Any] | None = None,
    forensic_findings=(),
    portfolio_weight: float | None = None,
    thesis_status: str = 'GREEN',
    priority_score: float = 0.0,
    previous_thesis: ThesisState | None = None,
    evidence_ids: Sequence[str] = (),
    source_ids: Sequence[str] = (),
    evidence_states: Sequence[str] = (),
    evidence_blockers: Sequence[str] = (),
    evidence_records: Sequence[EvidenceRecord] = (),
    catalysts: Sequence[str] = (),
    headwinds: Sequence[str] = (),
) -> ResearchDossier:
    valuation = None
    if valuation_kwargs is not None:
        valuation = derive_valuation(model.security_id, **dict(valuation_kwargs))
    company = build_research_snapshot(model, valuation=valuation, forensic_findings=forensic_findings)
    facts = dict(sector_facts or {})
    if not facts and model.periods:
        latest = model.periods[-1]
        facts = {k: getattr(latest, k) for k in ('revenue','ebitda','pat','cfo','debt','cash','receivables','inventory','capex') if getattr(latest, k) is not None}
    sector_snapshot = SectorMetricEngine().run(model.security_id, sector, facts)
    market = analyze_market(model.security_id, market_rows)
    portfolio = None
    if portfolio_weight is not None:
        portfolio = assess_portfolio(model.security_id, portfolio_weight, thesis_status, priority_score)
    adjudications = EvidenceAdjudicator().adjudicate(tuple(evidence_records), decision_time=as_of) if evidence_records else ()
    adjudicated_ids = tuple(e.evidence_id for r in evidence_records for e in (r,))
    adjudicated_states = tuple(a.status for a in adjudications)
    derived_blockers = list(evidence_blockers)
    for a in adjudications:
        if a.status in {'CONTRADICTED','UNRESOLVED'}:
            derived_blockers.append('EVIDENCE_'+a.status+':'+a.claim_key)
    evidence = EvidenceBundle(tuple(dict.fromkeys(tuple(evidence_ids)+adjudicated_ids)), tuple(dict.fromkeys(source_ids)), tuple(evidence_states)+adjudicated_states, tuple(dict.fromkeys(derived_blockers)))
    claims = _claims(company, sector_snapshot, market, catalysts, headwinds)
    blockers = list(evidence.blockers)
    if any(s not in ('EVIDENCE_SUPPORTED',) for s in evidence.states):
        blockers.append('EVIDENCE_STATE_NOT_SUPPORTED')
    thesis = BrainStateBuilder().build(model.security_id, as_of, claims, evidence.evidence_ids, tuple(sorted(set(blockers))))
    delta = compare_thesis(previous_thesis, thesis) if previous_thesis is not None else None
    change_log = []
    if delta:
        change_log.extend(f'ADDED_CLAIM:{x}' for x in delta.added_claims)
        change_log.extend(f'REMOVED_CLAIM:{x}' for x in delta.removed_claims)
        change_log.extend(f'ADDED_EVIDENCE:{x}' for x in delta.added_evidence)
        change_log.extend(f'REMOVED_EVIDENCE:{x}' for x in delta.removed_evidence)
        change_log.extend(f'BLOCKER_ADDED:{x}' for x in delta.blockers_added)
        change_log.extend(f'BLOCKER_REMOVED:{x}' for x in delta.blockers_removed)
    warnings = _warnings(company, sector_snapshot, market, evidence)
    return ResearchDossier(model.security_id, as_of, company, sector_snapshot, market, portfolio, thesis, delta, evidence, tuple(catalysts), tuple(headwinds), tuple(sorted(change_log)), warnings)
