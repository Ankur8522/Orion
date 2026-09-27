from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class PortfolioRisk:
    risks:tuple[str,...]; blocked:bool; reasons:tuple[str,...]
class PortfolioRiskGate:
    def evaluate(self, *, exposure=0.0, sector_overlap=0.0, liquidity_risk=0.0, valuation_stretch=0.0, catalyst_timing=0.0, contagion=0.0):
        vals={'EXPOSURE':exposure,'SECTOR_OVERLAP':sector_overlap,'LIQUIDITY_RISK':liquidity_risk,'VALUATION_STRETCH':valuation_stretch,'CATALYST_TIMING':catalyst_timing,'CONTAGION':contagion}
        if any(not 0<=float(v)<=1 for v in vals.values()): raise ValueError('INVALID_PORTFOLIO_RISK')
        risks=tuple(k for k,v in vals.items() if float(v)>=0.70)
        reasons=tuple(f'{k}>=0.70' for k in risks)
        return PortfolioRisk(risks,bool(risks),reasons)
