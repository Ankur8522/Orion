from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence

from orion.brain.progressive import Belief, Challenge, MarketState, ProgressiveDecisionBrain
from orion.brain.progressive_loop import ProgressiveMemory, ProgressiveMemoryState, ProgressiveReasoningLoop
from orion.learning.feedback import FeedbackReport
from orion.decision.plane import AgentFinding, CausalChain, DecisionPacket, ResearchDecisionPlane, Uncertainty
from orion.model.scenario import Scenario, ScenarioEngine, ScenarioResult
from orion.model.world import WorldModel
from orion.portfolio.intelligence import FactorExposure, Holding, PortfolioAssessment, PortfolioIntelligenceBrain
from orion.portfolio.allocation import AllocationAssessment, AllocationCandidate, DynamicCapitalAllocationBrain
from orion.portfolio.risk_gate import PortfolioRisk, PortfolioRiskGate

@dataclass(frozen=True)
class IntelligenceCase:
    security_id: str
    decision_time: str
    thesis: str
    evidence_ids: tuple[str, ...]
    findings: tuple[AgentFinding, ...]
    belief: Belief
    challenges: tuple[Challenge, ...] = ()
    scenarios: tuple[Scenario, ...] = ()
    market_state: MarketState | None = None
    holdings: tuple[Holding, ...] = ()
    factors: tuple[FactorExposure, ...] = ()
    scenario_impacts: tuple[float, ...] = ()
    allocation_candidates: tuple[AllocationCandidate, ...] = ()
    uncertainty: Uncertainty | None = None
    causal_chain: CausalChain | None = None
    portfolio_risks: tuple[str, ...] = ()
    catalysts: tuple[str, ...] = ()
    headwinds: tuple[str, ...] = ()
    priority_score: float = 0.0
    evidence_state: str = "EVIDENCE_SUPPORTED"
    blockers: tuple[str, ...] = ()
    robustness: float = 0.5
    risk_inputs: tuple[float, float, float, float, float, float] = (0, 0, 0, 0, 0, 0)
    max_weight: float = 0.25
    cash_floor: float = 0.0
    min_weight: float = 0.0
    scenario_depth: int = 3
    cycle_id: str = "cycle-1"
    feedback_report: FeedbackReport | None = None
    evidence_delta: float = 0.0
    scenario_delta: float = 0.0
    material_change: bool = False

@dataclass(frozen=True)
class IntelligenceRun:
    decision: DecisionPacket
    progressive: object
    progressive_cycle: ProgressiveMemoryState
    scenarios: tuple[ScenarioResult, ...]
    portfolio: PortfolioAssessment | None
    allocation: AllocationAssessment | None
    risk_gate: PortfolioRisk
    run_hash: str

class InvestmentIntelligenceKernel:
    """Authoritative orchestration spine for ORION's decision lifecycle.

    This is a composition layer, not a second scoring system. Each specialized
    engine remains the source of truth for its own domain; the kernel enforces
    ordering, gating, lineage and a single run manifest. It never trades.
    """
    def __init__(self, world_model: WorldModel | None = None):
        self.world = world_model or WorldModel()
        self.decision_plane = ResearchDecisionPlane()
        self.progressive = ProgressiveDecisionBrain()
        self.progressive_memory = ProgressiveMemory()
        self.progressive_loop = ProgressiveReasoningLoop(self.progressive, self.progressive_memory)
        self.scenario_engine = ScenarioEngine(self.world)
        self.portfolio_brain = PortfolioIntelligenceBrain()
        self.allocation_brain = DynamicCapitalAllocationBrain()
        self.risk_gate = PortfolioRiskGate()

    @staticmethod
    def _hash(obj) -> str:
        return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    def run(self, case: IntelligenceCase) -> IntelligenceRun:
        if not case.security_id or not case.thesis:
            raise ValueError("INVALID_INTELLIGENCE_CASE")
        progressive_cycle = self.progressive_loop.run_cycle(
            cycle_id=case.cycle_id,
            belief=case.belief,
            challenges=case.challenges,
            scenario_score=case.belief.scenario_support,
            calibration_score=max(0.0, min(1.0, 0.5 + case.belief.calibration_adjustment)),
            market_state=case.market_state,
            feedback_report=case.feedback_report,
            evidence_delta=case.evidence_delta,
            scenario_delta=case.scenario_delta,
            material_change=case.material_change,
        )
        progressive = progressive_cycle.assessment

        scenario_results: tuple[ScenarioResult, ...] = ()
        if case.scenarios:
            scenario_results = self.scenario_engine.run(case.scenarios, depth=case.scenario_depth)

        portfolio = None
        if case.holdings:
            portfolio = self.portfolio_brain.assess(
                case.holdings, case.factors,
                case.scenario_impacts,
                robustness=case.robustness,
            )

        risk = self.risk_gate.evaluate(
            exposure=case.risk_inputs[0],
            sector_overlap=case.risk_inputs[1],
            liquidity_risk=case.risk_inputs[2],
            valuation_stretch=case.risk_inputs[3],
            catalyst_timing=case.risk_inputs[4],
            contagion=case.risk_inputs[5],
        )

        allocation = None
        if case.allocation_candidates and not risk.blocked:
            allocation = self.allocation_brain.assess(
                case.allocation_candidates,
                max_weight=case.max_weight,
                cash_floor=case.cash_floor,
                min_weight=case.min_weight,
            )

        unresolved = list(case.blockers)
        if risk.blocked:
            unresolved.append("PORTFOLIO_RISK_GATE_BLOCKED")
        if progressive.fragility >= 0.80:
            unresolved.append("HIGH_PROGRESSIVE_FRAGILITY")
        if allocation and allocation.portfolio_uncertainty >= 0.70:
            unresolved.append("HIGH_ALLOCATION_UNCERTAINTY")

        decision = self.decision_plane.adjudicate(
            security_id=case.security_id,
            decision_time=case.decision_time,
            findings=case.findings,
            evidence_ids=case.evidence_ids,
            evidence_state=case.evidence_state,
            blockers=tuple(sorted(set(unresolved))),
            uncertainty=case.uncertainty or Uncertainty(),
            causal_chain=case.causal_chain,
            portfolio_risks=case.portfolio_risks,
            catalysts=case.catalysts,
            headwinds=case.headwinds,
            priority_score=case.priority_score,
            thesis=case.thesis,
        )
        manifest = {
            "decision": decision.run_manifest_hash,
            "progressive": progressive.lineage_hash,
            "progressive_cycle": progressive_cycle.lineage_hash,
            "scenarios": [x.lineage_hash for x in scenario_results],
            "portfolio": portfolio.lineage_hash if portfolio else None,
            "allocation": allocation.lineage_hash if allocation else None,
            "risk": risk.__dict__,
        }
        return IntelligenceRun(decision, progressive, progressive_cycle, scenario_results, portfolio, allocation, risk, self._hash(manifest))
