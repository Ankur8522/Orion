from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
import json
from .time import parse_utc

class CorpusState(str, Enum):
    CURRENT_PUBLIC='CURRENT_PUBLIC'; HISTORICAL_PIT='HISTORICAL_PIT'; LICENSED='LICENSED'; SYNTHETIC='SYNTHETIC'; BLOCKED='BLOCKED'

@dataclass(frozen=True)
class PITRecord:
    security_id: str
    dataset: str
    event_time: str
    available_time: str
    ingestion_time: str
    source_id: str
    corpus_state: CorpusState
    raw_hash: str
    supersedes: str | None = None
    effective_time: str | None = None
    quality: str = 'UNASSESSED'
    source_priority: int = 100
    lineage_id: str | None = None

    def validate(self, decision_time: str) -> None:
        decision=parse_utc(decision_time)
        event=parse_utc(self.event_time); available=parse_utc(self.available_time)
        effective=parse_utc(self.effective_time) if self.effective_time else event
        ingestion=parse_utc(self.ingestion_time)
        if available > decision: raise ValueError('FUTURE_INFORMATION_BLOCKED')
        if available < effective: raise ValueError('AVAILABILITY_BEFORE_EFFECTIVE')
        if ingestion < available: raise ValueError('INGESTION_BEFORE_AVAILABILITY')
        if self.corpus_state == CorpusState.SYNTHETIC: raise ValueError('SYNTHETIC_NOT_PROMOTABLE')
        if len(self.raw_hash) != 64 or any(c not in '0123456789abcdefABCDEF' for c in self.raw_hash): raise ValueError('INVALID_RAW_HASH')
        if self.source_priority < 0: raise ValueError('INVALID_SOURCE_PRIORITY')

@dataclass(frozen=True)
class CorpusManifest:
    manifest_id: str
    decision_time: str
    records: tuple[PITRecord,...]
    schema_version: str='1.1'

    def validate(self) -> None:
        for record in self.records: record.validate(self.decision_time)

    def digest(self) -> str:
        self.validate()
        blob=json.dumps({'manifest_id':self.manifest_id,'decision_time':self.decision_time,
                         'schema_version':self.schema_version,'records':[asdict(r) for r in self.records]},
                        default=lambda x:x.value if isinstance(x,Enum) else x,sort_keys=True,separators=(',',':')).encode()
        return sha256(blob).hexdigest()
