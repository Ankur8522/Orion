from __future__ import annotations
from dataclasses import dataclass
from ..agents.research_society import EvidenceAuditor, AdversarialReview
from ..brain.state import BrainStateBuilder

@dataclass(frozen=True)
class ResearchDecision:
    security_id: str
    status: str
    thesis_state: object
    review: dict

class ResearchOrchestrator:
    def __init__(self, evidence_auditor=None, brain=None):
        self.evidence_auditor=evidence_auditor or EvidenceAuditor(); self.brain=brain or BrainStateBuilder()
    def run(self, security_id, decision_time, evidence_rows, opinions=(), blockers=()):
        audit=self.evidence_auditor.audit(evidence_rows,decision_time)
        review=AdversarialReview().review(opinions,audit)
        valid_opinions=[o for o in opinions if set(o.evidence_ids) <= set(audit.accepted)]
        all_blockers=tuple(blockers)+tuple(audit.missing)
        if review['status']=='REVIEW': all_blockers=tuple(dict.fromkeys(all_blockers+('ADVERSARIAL_REVIEW_REQUIRED',)))
        state=self.brain.build(security_id,decision_time,tuple(sorted({o.thesis for o in valid_opinions if o.thesis})),audit.accepted,all_blockers)
        return ResearchDecision(security_id,review['status'],state,review)
