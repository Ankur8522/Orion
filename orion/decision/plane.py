from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

class DecisionState(str, Enum):
    DECISION_SUPPORT='DECISION_SUPPORT'
    ABSTAIN='ABSTAIN'
    DEFER='DEFER'
    ESCALATE='ESCALATE'
    BLOCKED='BLOCKED'

@dataclass(frozen=True)
class Uncertainty:
    data: float=0.0; evidence: float=0.0; model: float=0.0; causal: float=0.0
    valuation: float=0.0; timing: float=0.0; regime: float=0.0; outcome: float=0.0
    def __post_init__(self):
        if any(not 0 <= float(x) <= 1 for x in self.__dict__.values()): raise ValueError('INVALID_UNCERTAINTY')
    @property
    def composite(self):
        vals=[self.data,self.evidence,self.model,self.causal,self.valuation,self.timing,self.regime,self.outcome]
        return sum(vals)/len(vals)

@dataclass(frozen=True)
class AgentFinding:
    agent: str
    stance: str
    evidence_ids: tuple[str,...]=()
    claims: tuple[str,...]=()
    risks: tuple[str,...]=()
    uncertainty: float=0.0
    def __post_init__(self):
        if self.stance not in {'SUPPORT','CHALLENGE','NEUTRAL'}: raise ValueError('INVALID_STANCE')
        if not 0 <= self.uncertainty <= 1: raise ValueError('INVALID_AGENT_UNCERTAINTY')

@dataclass(frozen=True)
class CausalChain:
    trigger: str
    direct_effects: tuple[str,...]
    second_order_effects: tuple[str,...]=()
    competitive_response: tuple[str,...]=()
    capital_response: tuple[str,...]=()
    portfolio_effects: tuple[str,...]=()

@dataclass(frozen=True)
class DecisionPacket:
    security_id: str
    decision_time: str
    state: DecisionState
    thesis: str
    evidence_ids: tuple[str,...]
    disagreements: tuple[str,...]
    unresolved: tuple[str,...]
    uncertainty: Uncertainty
    causal_chain: CausalChain | None
    portfolio_risks: tuple[str,...]
    catalysts: tuple[str,...]
    headwinds: tuple[str,...]
    priority_score: float
    rationale_hash: str
    run_manifest_hash: str

class ResearchDecisionPlane:
    """Deterministic decision gate. It does not trade and never upgrades weak evidence into support."""
    AGENTS=('fundamental','forensic','sector','technical','quant','macro','bull','bear','portfolio_risk','evidence_auditor')
    def __init__(self, *, max_parallel_agents=10, max_retries=2):
        if max_parallel_agents < 1 or max_retries < 0: raise ValueError('INVALID_RUNTIME_BUDGET')
        self.max_parallel_agents=int(max_parallel_agents); self.max_retries=int(max_retries)

    def plan(self, *, security_id: str, decision_time: str, required_agents: Sequence[str] | None=None):
        agents=tuple(dict.fromkeys(required_agents or self.AGENTS))
        unknown=set(agents)-set(self.AGENTS)
        if unknown: raise ValueError('UNKNOWN_AGENT:'+','.join(sorted(unknown)))
        return {'security_id':security_id,'decision_time':decision_time,'agents':agents,'max_parallel_agents':self.max_parallel_agents,'max_retries':self.max_retries}

    @staticmethod
    def _hash(obj: Any) -> str:
        return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

    def adjudicate(self, *, security_id, decision_time, findings: Sequence[AgentFinding], evidence_ids=(), evidence_state='EVIDENCE_SUPPORTED', blockers=(), uncertainty=None, causal_chain=None, portfolio_risks=(), catalysts=(), headwinds=(), priority_score=0.0, thesis=''):
        findings=tuple(findings); evidence_ids=tuple(dict.fromkeys(evidence_ids)); blockers=tuple(dict.fromkeys(blockers))
        if not 0 <= priority_score <= 100: raise ValueError('INVALID_PRIORITY')
        disagreements=[]
        stances={f.stance for f in findings if f.stance != 'NEUTRAL'}
        if 'SUPPORT' in stances and 'CHALLENGE' in stances: disagreements.append('SUPPORT_CHALLENGE_SPLIT')
        claim_sets=[set(f.claims) for f in findings if f.claims]
        if claim_sets and len({tuple(sorted(x)) for x in claim_sets}) > 1: disagreements.append('CLAIM_DIVERGENCE')
        evidence_from_agents=set(e for f in findings for e in f.evidence_ids)
        unresolved=list(blockers)
        if evidence_state != 'EVIDENCE_SUPPORTED': unresolved.append('EVIDENCE_NOT_SUPPORTED')
        if not evidence_ids and not evidence_from_agents: unresolved.append('NO_EVIDENCE')
        if any(e not in evidence_ids for e in evidence_from_agents): unresolved.append('AGENT_EVIDENCE_NOT_IN_BUNDLE')
        u=uncertainty or Uncertainty()
        if u.composite >= 0.70: unresolved.append('HIGH_COMPOSITE_UNCERTAINTY')
        if 'SUPPORT_CHALLENGE_SPLIT' in disagreements: unresolved.append('MATERIAL_DISAGREEMENT')
        if unresolved: state=DecisionState.BLOCKED if 'EVIDENCE_NOT_SUPPORTED' in unresolved or 'NO_EVIDENCE' in unresolved else (DecisionState.ESCALATE if 'MATERIAL_DISAGREEMENT' in unresolved else DecisionState.DEFER)
        else: state=DecisionState.DECISION_SUPPORT
        manifest={'security_id':security_id,'decision_time':decision_time,'evidence_ids':evidence_ids,'findings':[f.__dict__ for f in findings], 'uncertainty':u.__dict__, 'blockers':unresolved}
        rationale={'thesis':thesis,'disagreements':disagreements,'unresolved':unresolved,'portfolio_risks':tuple(portfolio_risks),'catalysts':tuple(catalysts),'headwinds':tuple(headwinds),'priority_score':priority_score}
        return DecisionPacket(security_id,decision_time,state,thesis,evidence_ids,tuple(disagreements),tuple(sorted(set(unresolved))),u,causal_chain,tuple(portfolio_risks),tuple(catalysts),tuple(headwinds),float(priority_score),self._hash(rationale),self._hash(manifest))
