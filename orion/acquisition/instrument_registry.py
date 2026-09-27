from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping
from ..data.time import parse_utc

@dataclass(frozen=True)
class InstrumentMapping:
    security_id: str
    provider: str
    instrument_key: str
    effective_from: str
    effective_to: str | None
    available_time: str
    source_id: str
    content_hash: str
    status: str = 'VERIFIED'

    @classmethod
    def create(cls, *, security_id: str, provider: str, instrument_key: str,
               effective_from: str, available_time: str, source_id: str,
               effective_to: str | None = None, content_hash: str | None = None):
        sid, prov, key, src = (str(x).strip() for x in (security_id, provider, instrument_key, source_id))
        if not sid or not prov or not src: raise ValueError('INVALID_MAPPING_IDENTITY')
        if not key or '|' not in key: raise ValueError('INVALID_INSTRUMENT_KEY')
        ef = parse_utc(effective_from); av = parse_utc(available_time)
        if effective_to is not None and parse_utc(effective_to) <= ef: raise ValueError('INVALID_EFFECTIVE_RANGE')
        if av > ef: raise ValueError('MAPPING_AVAILABLE_AFTER_EFFECTIVE')
        digest = content_hash or sha256(f'{sid}|{prov}|{key}|{effective_from}|{effective_to}|{available_time}|{src}'.encode()).hexdigest()
        return cls(sid, prov, key, effective_from, effective_to, available_time, src, digest)

class InstrumentMappingRegistry:
    """Durable, point-in-time provider instrument mapping registry.

    Mappings are facts only when supplied by an authorized source. The registry
    never discovers or guesses provider keys and never performs network calls.
    """
    def __init__(self, store): self.store = store

    def register(self, mapping: InstrumentMapping) -> None:
        self.store.instrument_mapping(mapping)

    def resolve(self, security_id: str, *, provider: str, as_of: str) -> InstrumentMapping | None:
        return self.store.instrument_mapping_resolve(security_id, provider=provider, as_of=as_of)

    def readiness(self, security_ids: Iterable[str], *, provider: str, as_of: str) -> dict:
        parse_utc(as_of)
        ids=tuple(dict.fromkeys(str(x).strip() for x in security_ids if str(x).strip()))
        rows=[]; counts={s:0 for s in ('MAPPED','BLOCKED')}
        for sid in ids:
            m=self.resolve(sid, provider=provider, as_of=as_of)
            if m:
                counts['MAPPED'] += 1
                rows.append({'security_id':sid,'status':'MAPPED','provider':provider,'instrument_key':m.instrument_key,'source_id':m.source_id,'available_time':m.available_time,'effective_from':m.effective_from,'effective_to':m.effective_to,'content_hash':m.content_hash})
            else:
                counts['BLOCKED'] += 1
                rows.append({'security_id':sid,'status':'BLOCKED','reason':'NO_VERIFIED_INSTRUMENT_MAPPING'})
        total=len(ids); mapped=counts['MAPPED']
        return {'provider':provider,'as_of':as_of,'requested':total,'mapped':mapped,'blocked':counts['BLOCKED'],'coverage_pct':round(mapped/total*100,4) if total else 0.0,'status':'READY' if total and mapped==total else ('PARTIAL' if mapped else 'BLOCKED'),'rows':rows}
