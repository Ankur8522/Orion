from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class EvidenceItem:
    evidence_id:str; source_id:str; claim:str; state:str='EVIDENCE_SUPPORTED'; content_hash:str=''; available_time:str=''

@dataclass(frozen=True)
class Contradiction:
    left_id:str; right_id:str; claim_key:str; reason:str

class EvidenceAdjudicator:
    VALID={'EVIDENCE_SUPPORTED','REVIEW','UNCERTAIN','BLOCKED'}
    def adjudicate(self, items, *, required_ids=()):
        items=tuple(items); accepted=[]; review=[]; blocked=[]; contradictions=[]
        by_claim={}
        for x in items:
            if x.state not in self.VALID: raise ValueError('INVALID_EVIDENCE_STATE')
            if x.state=='EVIDENCE_SUPPORTED': accepted.append(x.evidence_id)
            elif x.state=='BLOCKED': blocked.append(x.evidence_id)
            else: review.append(x.evidence_id)
            key=x.claim.split('=',1)[0].strip() if '=' in x.claim else x.claim
            by_claim.setdefault(key,[]).append(x)
        for claim, rows in by_claim.items():
            vals=[]
            for r in rows:
                try: vals.append((r.evidence_id, json.loads(r.claim) if r.claim.startswith('{') else r.claim))
                except Exception: vals.append((r.evidence_id,r.claim))
            # Contradiction is explicit when same claim key carries opposite scalar values encoded as key=value.
            parsed=[]
            for eid,val in vals:
                if isinstance(val,str) and '=' in val:
                    k,v=val.split('=',1); parsed.append((eid,k.strip(),v.strip()))
            for i,a in enumerate(parsed):
                for b in parsed[i+1:]:
                    if a[1]==b[1] and a[2]!=b[2]: contradictions.append(Contradiction(a[0],b[0],a[1],'CONFLICTING_VALUES'))
        missing=tuple(sorted(set(required_ids)-set(accepted)))
        if contradictions: review.append('CONTRADICTION_REVIEW')
        return {'accepted':tuple(sorted(set(accepted))),'review':tuple(sorted(set(review))),'blocked':tuple(sorted(set(blocked))),'missing':missing,'contradictions':tuple(contradictions)}
