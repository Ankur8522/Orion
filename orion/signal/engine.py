from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from orion.decision.plane import DecisionPacket, DecisionState

@dataclass(frozen=True)
class Signal:
    security_id: str
    action: str
    strength: float
    confidence: float
    blocked: bool
    reasons: tuple[str, ...]
    lineage_hash: str

class SignalEngine:
    """Converts a governed DecisionPacket into an auditable non-trading signal."""
    def generate(self, decision: DecisionPacket, *, robustness: float, uncertainty: float, risk_blocked: bool = False) -> Signal:
        if not 0 <= robustness <= 1 or not 0 <= uncertainty <= 1:
            raise ValueError("INVALID_SIGNAL_INPUT")
        blocked = risk_blocked or decision.state in {DecisionState.BLOCKED, DecisionState.DEFER, DecisionState.ESCALATE, DecisionState.ABSTAIN}
        if blocked:
            action = "NO_ACTION"
            strength = 0.0
            reasons = tuple(sorted(set(decision.unresolved or decision.disagreements or ("DECISION_NOT_CLEAR",))))
        else:
            action = "RESEARCH_SUPPORTED"
            strength = max(0.0, min(1.0, 0.60 * decision.priority_score / 100 + 0.25 * robustness + 0.15 * (1 - uncertainty)))
            reasons = ()
        payload={"security_id":decision.security_id,"action":action,"strength":round(strength,12),"confidence":round(1-uncertainty,12),"blocked":blocked,"reasons":reasons,"rationale_hash":decision.rationale_hash}
        return Signal(decision.security_id,action,round(strength,12),round(1-uncertainty,12),blocked,reasons,sha256(json.dumps(payload,sort_keys=True,separators=(",",":" )).encode()).hexdigest())
