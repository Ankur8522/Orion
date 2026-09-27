from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

class EvidenceState(str,Enum): SUPPORTED='EVIDENCE_SUPPORTED'; REVIEW='REVIEW'; UNCERTAIN='UNCERTAIN'; BLOCKED='BLOCKED'
@dataclass(frozen=True)
class ThesisState:
    security_id:str
    decision_time:str
    state:EvidenceState
    claims:tuple[str,...]
    evidence_ids:tuple[str,...]
    blockers:tuple[str,...]
    fingerprint:str

class BrainStateBuilder:
    def build(self,security_id,decision_time,claims,evidence_ids,blockers=()):
        if not security_id or not decision_time: raise ValueError('INVALID_THESIS_CONTEXT')
        if len(set(evidence_ids)) != len(tuple(evidence_ids)): raise ValueError('DUPLICATE_EVIDENCE_IDS')
        state=EvidenceState.BLOCKED if blockers else (EvidenceState.SUPPORTED if evidence_ids else EvidenceState.UNCERTAIN)
        payload={'security_id':security_id,'decision_time':decision_time,'claims':list(claims),'evidence_ids':list(evidence_ids),'blockers':list(blockers)}
        fp=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return ThesisState(security_id,decision_time,state,tuple(claims),tuple(evidence_ids),tuple(blockers),fp)
