from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, Sequence

class CoverageState(str, Enum):
    READY='READY'
    PARTIAL='PARTIAL'
    MISSING='MISSING'
    STALE='STALE'
    NOT_CONFIGURED='NOT_CONFIGURED'
    UNSUPPORTED='UNSUPPORTED'

@dataclass(frozen=True)
class DatasetCoverage:
    dataset: str
    state: CoverageState
    observations: int
    source_ids: tuple[str,...]=()
    latest_available_time: str|None=None
    freshness_seconds: float|None=None
    reason: str=''

@dataclass(frozen=True)
class CoverageAssessment:
    required: tuple[str,...]
    rows: tuple[DatasetCoverage,...]
    completeness: float
    blockers: tuple[str,...]
    lineage_hash: str
    @property
    def usable(self): return not self.blockers

class DataCoverageContract:
    """Fail-closed coverage contract for a decision-time research snapshot."""
    def assess(self, required: Sequence[str], coverage: Mapping[str, DatasetCoverage], *, critical: Sequence[str]=()) -> CoverageAssessment:
        req=tuple(sorted(set(required))); crit=set(critical)
        rows=tuple(coverage.get(d, DatasetCoverage(d,CoverageState.MISSING,0,reason='NO_COVERAGE_RECORD')) for d in req)
        blockers=[]
        for r in rows:
            if r.dataset in crit and r.state != CoverageState.READY: blockers.append(f'{r.dataset}:{r.state.value}')
            elif r.observations < 1 and r.state not in {CoverageState.NOT_CONFIGURED,CoverageState.UNSUPPORTED}: blockers.append(f'{r.dataset}:NO_OBSERVATIONS')
        completeness=sum(1 for r in rows if r.state==CoverageState.READY)/max(1,len(rows))
        payload={'required':req,'rows':[r.__dict__ for r in rows],'blockers':sorted(blockers)}
        lineage=sha256(json.dumps(payload,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
        return CoverageAssessment(req,rows,completeness,tuple(sorted(set(blockers))),lineage)
