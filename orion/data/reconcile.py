from dataclasses import dataclass
from typing import Sequence
from .providers import ProviderObservation, validate_observation

@dataclass(frozen=True)
class Reconciliation:
    dataset: str
    security_id: str
    observations: tuple[ProviderObservation, ...]
    status: str
    selected_provider: str | None
    disagreement: bool

class Reconciler:
    def reconcile(self, observations: Sequence[ProviderObservation], *, as_of: str | None = None) -> Reconciliation:
        if not observations: raise ValueError('NO_OBSERVATIONS')
        keys={(o.dataset,o.security_id) for o in observations}
        if len(keys)!=1: raise ValueError('MIXED_OBSERVATION_KEYS')
        valid=[]
        for o in observations:
            validate_observation(o)
            if as_of is not None:
                from .time import parse_utc
                if parse_utc(o.available_time) > parse_utc(as_of):
                    continue
            valid.append(o)
        if not valid: raise ValueError('NO_PIT_VALID_OBSERVATIONS')
        hashes={o.payload_hash for o in valid}
        disagreement=len(hashes)>1
        status='DISAGREEMENT' if disagreement else 'AGREED'
        selected=None if disagreement else min(valid,key=lambda o:(o.source_priority,o.provider)).provider
        d,s=next(iter(keys))
        return Reconciliation(d,s,tuple(valid),status,selected,disagreement)
