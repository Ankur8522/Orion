from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

STAGE_ORDER = ('ACQUISITION','EVIDENCE','FINANCIAL_MODEL','DOSSIER','PRIORITY','COMPLETE')

@dataclass(frozen=True)
class StockCoverage:
    security_id: str
    status: str
    stage: str
    coverage_pct: float
    missing: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

@dataclass(frozen=True)
class CoverageReport:
    total: int
    complete: int
    blocked: int
    failed: int
    average_coverage_pct: float
    stage_counts: Mapping[str, int]
    stocks: tuple[StockCoverage, ...]


def coverage_from_stage(stage: str, status: str) -> float:
    if status == 'COMPLETE': return 100.0
    if status == 'FAILED': return 0.0
    try: return round(STAGE_ORDER.index(stage) / (len(STAGE_ORDER)-1) * 100.0, 1)
    except ValueError: return 0.0


def build_coverage(results: Sequence[object]) -> CoverageReport:
    rows=[]; counts={s:0 for s in STAGE_ORDER}
    for r in results:
        status=getattr(r,'status','FAILED'); stage=getattr(r,'stage','UNKNOWN')
        counts[stage]=counts.get(stage,0)+1
        reason=getattr(r,'reason',None)
        missing=(reason,) if reason else ()
        blockers=missing if status in ('BLOCKED','FAILED') else ()
        rows.append(StockCoverage(getattr(r,'security_id'),status,stage,coverage_from_stage(stage,status),missing,blockers))
    total=len(rows); complete=sum(x.status=='COMPLETE' for x in rows); blocked=sum(x.status=='BLOCKED' for x in rows); failed=sum(x.status=='FAILED' for x in rows)
    avg=round(sum(x.coverage_pct for x in rows)/total,1) if total else 0.0
    return CoverageReport(total,complete,blocked,failed,avg,counts,tuple(rows))

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping
@dataclass(frozen=True)
class UniverseCoverageSummary:
    total:int; complete:int; blocked:int; failed:int; coverage_pct:float; blocker_reasons:Mapping[str,int]; lineage_hash:str

def build_universe_coverage(results: Iterable[object]) -> UniverseCoverageSummary:
    rows=tuple(results); total=len(rows); complete=sum(getattr(x,'status',None)=='COMPLETE' for x in rows); blocked=sum(getattr(x,'status',None)=='BLOCKED' for x in rows); failed=total-complete-blocked
    reasons=Counter(getattr(x,'reason',None) for x in rows if getattr(x,'status',None)=='BLOCKED')
    import hashlib,json
    payload={'total':total,'complete':complete,'blocked':blocked,'failed':failed,'reasons':dict(sorted(reasons.items()))}
    h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return UniverseCoverageSummary(total,complete,blocked,failed,0 if total==0 else round(complete*100/total,4),dict(sorted(reasons.items())),h)
