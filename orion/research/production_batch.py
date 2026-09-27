from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Mapping, Any, Callable, Sequence
import json
from .dossier import ResearchDossier, build_research_dossier
from ..company.model import CompanyModel

STAGES = ('ACQUISITION','EVIDENCE','FINANCIAL_MODEL','DOSSIER','PRIORITY','COMPLETE')

@dataclass(frozen=True)
class StockRun:
    security_id: str
    status: str
    stage: str
    dossier: ResearchDossier | None = None
    reason: str | None = None

@dataclass(frozen=True)
class ProductionBatchReport:
    total: int
    complete: int
    blocked: int
    failed: int
    stage_counts: Mapping[str,int]
    results: tuple[StockRun,...]

class ProductionResearchBatch:
    """Deterministic batch bridge from available PIT company models to dossiers.

    This is deliberately data-bound: it never invents missing models or live facts.
    A missing model/evidence context is BLOCKED rather than silently synthesized.
    """
    def __init__(self, *, model_provider: Callable[[str], CompanyModel | None] | None = None):
        self.model_provider = model_provider

    def run(self, security_ids: Sequence[str], *, as_of: str,
            contexts: Mapping[str, Mapping[str,Any]] | None = None) -> ProductionBatchReport:
        ids = list(dict.fromkeys(security_ids))
        contexts = contexts or {}
        results=[]
        counts={s:0 for s in STAGES}
        for sid in ids:
            ctx=dict(contexts.get(sid, {}))
            try:
                model = ctx.get('model')
                if model is None and self.model_provider:
                    model=self.model_provider(sid)
                if model is None:
                    results.append(StockRun(sid,'BLOCKED','FINANCIAL_MODEL',None,'NO_COMPANY_MODEL'))
                    counts['FINANCIAL_MODEL']+=1; continue
                counts['ACQUISITION']+=1
                evidence_ids=tuple(ctx.get('evidence_ids',()))
                if not evidence_ids:
                    results.append(StockRun(sid,'BLOCKED','EVIDENCE',None,'NO_EVIDENCE_LINKED'))
                    counts['EVIDENCE']+=1; continue
                counts['EVIDENCE']+=1; counts['FINANCIAL_MODEL']+=1
                dossier=build_research_dossier(model, as_of=as_of,
                    sector=ctx.get('sector','generic'), sector_facts=ctx.get('sector_facts'),
                    market_rows=ctx.get('market_rows',()), valuation_kwargs=ctx.get('valuation_kwargs'),
                    forensic_findings=ctx.get('forensic_findings',()), portfolio_weight=ctx.get('portfolio_weight'),
                    thesis_status=ctx.get('thesis_status','GREEN'), priority_score=float(ctx.get('priority_score',0)),
                    previous_thesis=ctx.get('previous_thesis'), evidence_ids=evidence_ids,
                    source_ids=ctx.get('source_ids',()), evidence_states=ctx.get('evidence_states',()),
                    evidence_blockers=ctx.get('evidence_blockers',()), catalysts=ctx.get('catalysts',()),
                    headwinds=ctx.get('headwinds',()))
                counts['DOSSIER']+=1; counts['PRIORITY']+=1; counts['COMPLETE']+=1
                results.append(StockRun(sid,'COMPLETE','COMPLETE',dossier,None))
            except Exception as exc:
                results.append(StockRun(sid,'FAILED','DOSSIER',None,type(exc).__name__+':'+str(exc)))
        complete=sum(r.status=='COMPLETE' for r in results); blocked=sum(r.status=='BLOCKED' for r in results)
        failed=len(results)-complete-blocked
        return ProductionBatchReport(len(ids),complete,blocked,failed,dict(counts),tuple(results))

def report_json(report: ProductionBatchReport) -> str:
    def clean(x):
        if hasattr(x,'__dict__'):
            return {k:clean(v) for k,v in x.__dict__.items()}
        if isinstance(x, Mapping): return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x,(tuple,list)): return [clean(v) for v in x]
        return x
    return json.dumps(clean(asdict(report)), default=str, sort_keys=True)

# v144 compatibility helper: coverage can be generated without changing batch semantics.
def coverage_report(report: ProductionBatchReport):
    from .coverage import build_coverage
    return build_coverage(report.results)
