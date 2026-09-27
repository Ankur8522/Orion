from orion.brain.kernel import IntelligenceCase, InvestmentIntelligenceKernel
from orion.brain.progressive import Belief
from orion.decision.plane import AgentFinding
from orion.portfolio.allocation import AllocationCandidate
from orion.signal.engine import SignalEngine
from orion.execution.paper import PaperExecutionBook


def test_full_brain_spine_and_paper_boundary():
    case=IntelligenceCase(
        security_id="TEST", decision_time="2026-09-27T00:00:00Z", thesis="test thesis",
        evidence_ids=("e1",), findings=(AgentFinding("fundamental","SUPPORT",("e1",),("claim",)),),
        belief=Belief("t1",0.6,0.8,0.75,0.1,0.05),
        allocation_candidates=(AllocationCandidate("TEST",0.18,0.2,0.8,0.1,0.75,0.1,0.1),),
        priority_score=80,
    )
    result=InvestmentIntelligenceKernel().run(case)
    assert result.decision.security_id=="TEST"
    assert result.allocation is not None
    assert result.risk_gate.blocked is False
    signal=SignalEngine().generate(result.decision, robustness=result.progressive.robustness, uncertainty=result.progressive.uncertainty)
    assert signal.blocked is False
    book=PaperExecutionBook(); order=book.stage(security_id="TEST",target_weight=0.2,current_weight=0.1,allowed=True,reason="TEST",lineage_hash=result.run_hash)
    assert order.state=="STAGED"
    assert PaperExecutionBook.live_trading_enabled() is False


def test_risk_gate_blocks_allocation_and_signal():
    case=IntelligenceCase(
        security_id="TEST", decision_time="2026-09-27T00:00:00Z", thesis="test thesis",
        evidence_ids=("e1",), findings=(AgentFinding("fundamental","SUPPORT",("e1",),("claim",)),),
        belief=Belief("t1",0.6,0.8,0.75,0.1,0.05),
        allocation_candidates=(AllocationCandidate("TEST",0.18,current_weight=0.1),),
        risk_inputs=(0.9,0,0,0,0,0), priority_score=80,
    )
    result=InvestmentIntelligenceKernel().run(case)
    assert result.risk_gate.blocked is True
    assert result.allocation is None

from orion.app.service import OrionService

def test_application_service_wires_signal_and_paper_only():
    case=IntelligenceCase(
        security_id="TEST2", decision_time="2026-09-27T00:00:00Z", thesis="service thesis",
        evidence_ids=("e1",), findings=(AgentFinding("fundamental","SUPPORT",("e1",),("claim",)),),
        belief=Belief("t2",0.65,0.85,0.8,0.05,0.1),
        allocation_candidates=(AllocationCandidate("TEST2",0.20,0.15,0.85,0.08,0.8,0.05,0.05),),
        priority_score=90,
    )
    run=OrionService().analyze(case)
    assert run.intelligence.run_hash
    assert run.signal.lineage_hash
    assert all(o.state in {"STAGED","BLOCKED"} for o in run.paper_orders)
    assert not run.paper_orders or run.paper_orders[0].lineage_hash == run.intelligence.run_hash
    assert run.paper_orders is not None
