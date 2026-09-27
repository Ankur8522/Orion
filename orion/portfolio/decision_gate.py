from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from .allocation import AllocationAssessment
from .risk_gate import PortfolioRisk

@dataclass(frozen=True)
class PortfolioDecision:
    status: str
    blocked: bool
    reasons: tuple[str, ...]
    target_weights: tuple[tuple[str, float], ...]
    lineage_hash: str

class PortfolioDecisionGate:
    """Single deterministic pre-paper decision boundary; never routes live orders."""
    def evaluate(self, allocation: AllocationAssessment, risk: PortfolioRisk, *, research_ready: bool = True, data_ready: bool = True) -> PortfolioDecision:
        reasons=[]
        if allocation.portfolio_uncertainty >= 0.75: reasons.append('HIGH_PORTFOLIO_UNCERTAINTY')
        if risk.blocked: reasons.extend(risk.reasons)
        if not research_ready: reasons.append('RESEARCH_NOT_READY')
        if not data_ready: reasons.append('DATA_NOT_READY')
        blocked=bool(reasons)
        status='BLOCKED' if blocked else 'APPROVED_FOR_PAPER_ONLY'
        payload={'status':status,'reasons':sorted(set(reasons)),'target':allocation.target_weights,'allocation_lineage':allocation.lineage_hash}
        return PortfolioDecision(status,blocked,tuple(sorted(set(reasons))),allocation.target_weights,sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest())
