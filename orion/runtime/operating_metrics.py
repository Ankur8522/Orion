from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class OperatingScore:
    architecture: float
    data_readiness: float
    brain_readiness: float
    portfolio_readiness: float
    ui_readiness: float
    overall: float
    blockers: tuple[str,...]

class OperatingScorecard:
    def score(self, *, data_readiness: float, brain_readiness: float, portfolio_readiness: float, ui_readiness: float, blockers: Mapping[str,bool]) -> OperatingScore:
        vals=[float(data_readiness),float(brain_readiness),float(portfolio_readiness),float(ui_readiness)]
        vals=[max(0,min(100,x)) for x in vals]
        architecture=round(sum(vals)/4,2)
        active=tuple(sorted(k for k,v in blockers.items() if v))
        overall=round(max(0,architecture-(min(20,len(active)*3))),2)
        return OperatingScore(architecture,vals[0],vals[1],vals[2],vals[3],overall,active)
