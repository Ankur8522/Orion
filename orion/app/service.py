from __future__ import annotations
from dataclasses import dataclass
from orion.brain.kernel import IntelligenceCase, InvestmentIntelligenceKernel
from orion.execution.paper import PaperExecutionBook
from orion.signal.engine import SignalEngine

@dataclass(frozen=True)
class ServiceRun:
    intelligence: object
    signal: object
    paper_orders: tuple[object, ...]

class OrionService:
    """Application service that wires the full research-to-paper lifecycle."""
    def __init__(self, kernel: InvestmentIntelligenceKernel | None = None, paper: PaperExecutionBook | None = None):
        self.kernel=kernel or InvestmentIntelligenceKernel()
        self.signals=SignalEngine()
        self.paper=paper or PaperExecutionBook()
    def analyze(self, case: IntelligenceCase) -> ServiceRun:
        result=self.kernel.run(case)
        signal=self.signals.generate(result.decision, robustness=result.progressive.robustness, uncertainty=result.progressive.uncertainty, risk_blocked=result.risk_gate.blocked)
        orders=[]
        if result.allocation:
            targets=dict(result.allocation.target_weights)
            current={c.security_id:c.current_weight for c in case.allocation_candidates}
            for sid,target in sorted(targets.items()):
                orders.append(self.paper.stage(security_id=sid,target_weight=target,current_weight=current.get(sid,0.0),allowed=not signal.blocked,reason=signal.action,lineage_hash=result.run_hash))
        return ServiceRun(result,signal,tuple(orders))
