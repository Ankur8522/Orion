from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ThesisHealth:
    security_id: str
    status: str
    reasons: tuple[str,...]
    evidence_count: int
    blocker_count: int

def assess(security_id, thesis_state, evidence_count, max_age_warning=False):
    reasons=[]
    if thesis_state.state.value == 'BLOCKED': reasons.append('BLOCKED')
    if thesis_state.state.value in {'UNCERTAIN','REVIEW'}: reasons.append(thesis_state.state.value)
    if max_age_warning: reasons.append('STALE_EVIDENCE')
    status='RED' if 'BLOCKED' in reasons else ('AMBER' if reasons else 'GREEN')
    return ThesisHealth(security_id,status,tuple(reasons),int(evidence_count),len(thesis_state.blockers))
