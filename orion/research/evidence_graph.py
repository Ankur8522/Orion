from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence

@dataclass(frozen=True)
class EvidenceNode:
    evidence_id: str
    claim_id: str
    state: str
    available_time: str
    source_id: str
    content_hash: str

@dataclass(frozen=True)
class EvidenceGraph:
    nodes: tuple[EvidenceNode,...]
    edges: tuple[tuple[str,str,str],...]
    blockers: tuple[str,...]
    lineage_hash: str
    @property
    def usable(self): return not self.blockers

class EvidenceGraphBuilder:
    """Binds claims, evidence and contradictions into an auditable graph."""
    def build(self, nodes: Sequence[EvidenceNode], *, decision_time: str) -> EvidenceGraph:
        ordered=tuple(sorted(nodes,key=lambda n:(n.claim_id,n.available_time,n.evidence_id)))
        blockers=[]; edges=[]; by_claim={}
        for n in ordered:
            if n.available_time > decision_time: blockers.append(f'{n.evidence_id}:FUTURE')
            by_claim.setdefault(n.claim_id,[]).append(n)
        for claim, items in sorted(by_claim.items()):
            for i,a in enumerate(items):
                for b in items[i+1:]:
                    if a.content_hash != b.content_hash:
                        edges.append((a.evidence_id,b.evidence_id,'CONFLICT'))
            states={x.state for x in items}
            if 'CONTRADICTED' in states or ('UNRESOLVED' in states and len(items)>0): blockers.append(f'{claim}:UNRESOLVED_OR_CONTRADICTED')
        payload={'nodes':[n.__dict__ for n in ordered],'edges':edges,'blockers':sorted(set(blockers))}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return EvidenceGraph(ordered,tuple(edges),tuple(sorted(set(blockers))),lineage)
