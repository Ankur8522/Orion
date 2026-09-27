from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence
from .time import parse_utc

@dataclass(frozen=True)
class WorldSnapshot:
    security_id: str
    decision_time: str
    universe_membership: Mapping[str, object]
    observations: Mapping[str, tuple[Mapping[str, object], ...]]
    research_evidence: tuple[Mapping[str, object], ...] = ()
    blockers: tuple[str, ...] = ()
    lineage_hash: str = ''

    @classmethod
    def build(cls, security_id: str, decision_time: str, *, universe_membership: Mapping[str, object] | None = None, observations: Mapping[str, Sequence[Mapping[str, object]]] | None = None, research_evidence: Sequence[Mapping[str, object]] = ()):
        parse_utc(decision_time)
        obs={}
        blockers=[]
        for dataset, rows in (observations or {}).items():
            valid=[]
            for row in rows:
                available=row.get('available_time')
                if available is None:
                    blockers.append(f'{dataset}:MISSING_AVAILABLE_TIME'); continue
                try: parse_utc(str(available))
                except ValueError: blockers.append(f'{dataset}:INVALID_AVAILABLE_TIME'); continue
                if parse_utc(str(available)) <= parse_utc(decision_time): valid.append(dict(row))
                else: blockers.append(f'{dataset}:FUTURE_OBSERVATION')
            obs[dataset]=tuple(sorted(valid,key=lambda r:(str(r.get('available_time','')),str(r.get('event_time','')),str(r.get('payload_hash','')))))
        payload={'security_id':security_id,'decision_time':decision_time,'universe_membership':dict(universe_membership or {}),'observations':obs,'research_evidence':list(research_evidence),'blockers':sorted(set(blockers))}
        lineage=sha256(json.dumps(payload,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
        return cls(security_id,decision_time,dict(universe_membership or {}),obs,tuple(research_evidence),tuple(sorted(set(blockers))),lineage)

    @property
    def usable(self) -> bool: return not self.blockers
