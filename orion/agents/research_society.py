from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

class Verdict(str, Enum): SUPPORT = 'SUPPORT'
    # intentionally simple enum values for deterministic downstream routing
    
@dataclass(frozen=True)
class AnalystOpinion:
    agent: str
    security_id: str
    thesis: str
    evidence_ids: tuple[str, ...]
    risks: tuple[str, ...]
    confidence: float
    rationale_hash: str

@dataclass(frozen=True)
class EvidenceAudit:
    accepted: tuple[str, ...]
    rejected: tuple[str, ...]
    missing: tuple[str, ...]

class EvidenceAuditor:
    def audit(self, evidence_rows, decision_time: str, required_ids=()):
        from ..data.time import parse_utc
        parse_utc(decision_time)
        accepted=[]; rejected=[]; present=set()
        for row in evidence_rows:
            eid=row.get('evidence_id')
            if not eid: continue
            try: available=row['available_time']; parse_utc(available)
            except Exception: rejected.append(eid); continue
            try:
                decision=parse_utc(decision_time)
                available_dt=parse_utc(available)
            except Exception:
                rejected.append(eid); continue
            content_hash=str(row.get('content_hash') or '')
            if available_dt <= decision and 0 <= float(row.get('confidence',0)) <= 1 and len(content_hash)==64 and all(c in '0123456789abcdefABCDEF' for c in content_hash):
                accepted.append(eid); present.add(eid)
            else: rejected.append(eid)
        missing=tuple(x for x in required_ids if x not in present)
        return EvidenceAudit(tuple(sorted(set(accepted))),tuple(sorted(set(rejected))),tuple(sorted(missing)))

def opinion(agent, security_id, thesis, evidence_ids=(), risks=(), confidence=0.5):
    if not 0 <= confidence <= 1: raise ValueError('INVALID_CONFIDENCE')
    payload={'agent':agent,'security_id':security_id,'thesis':thesis,'evidence_ids':list(evidence_ids),'risks':list(risks),'confidence':confidence}
    h=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return AnalystOpinion(agent,security_id,thesis,tuple(evidence_ids),tuple(risks),confidence,h)

class AdversarialReview:
    def review(self, opinions, audited_evidence: EvidenceAudit):
        opinions=tuple(opinions)
        support=set(audited_evidence.accepted)
        valid=[o for o in opinions if set(o.evidence_ids) <= support]
        disagreements=[]
        theses={o.thesis for o in valid}
        if len(theses)>1: disagreements.append('THESIS_DISAGREEMENT')
        risks=tuple(sorted({r for o in valid for r in o.risks}))
        evidence=tuple(sorted({e for o in valid for e in o.evidence_ids}))
        status='REVIEW' if disagreements or audited_evidence.missing else ('SUPPORTED' if evidence else 'UNCERTAIN')
        return {'status':status,'opinions':len(valid),'disagreements':tuple(disagreements),'risks':risks,'evidence_ids':evidence}
