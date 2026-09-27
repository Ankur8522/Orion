from dataclasses import dataclass
from .state import ThesisState

@dataclass(frozen=True)
class ThesisDelta:
    changed: bool
    added_claims: tuple[str,...]
    removed_claims: tuple[str,...]
    added_evidence: tuple[str,...]
    removed_evidence: tuple[str,...]
    blockers_added: tuple[str,...]
    blockers_removed: tuple[str,...]

def compare(previous: ThesisState|None, current: ThesisState) -> ThesisDelta:
    if previous is None:
        return ThesisDelta(True,current.claims,(),current.evidence_ids,(),current.blockers,())
    pc,cc=set(previous.claims),set(current.claims); pe,ce=set(previous.evidence_ids),set(current.evidence_ids); pb,cb=set(previous.blockers),set(current.blockers)
    return ThesisDelta(previous.fingerprint!=current.fingerprint,tuple(sorted(cc-pc)),tuple(sorted(pc-cc)),tuple(sorted(ce-pe)),tuple(sorted(pe-ce)),tuple(sorted(cb-pb)),tuple(sorted(pb-cb)))
