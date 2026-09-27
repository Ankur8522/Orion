from dataclasses import dataclass
from .time import parse_utc

@dataclass(frozen=True)
class Observation:
    security_id: str
    event_time: str
    available_time: str
    value: float
    source_id: str
    dataset: str='generic'
    evidence_id: str|None=None
    source_time: str|None=None
    ingestion_time: str|None=None

class PITStore:
    def __init__(self): self._rows=[]
    def append(self, row: Observation):
        event, available=parse_utc(row.event_time),parse_utc(row.available_time)
        source=parse_utc(row.source_time) if row.source_time else event
        ingestion=parse_utc(row.ingestion_time) if row.ingestion_time else available
        if available < event: raise ValueError('INVALID_TEMPORAL_ORDER')
        if available < source: raise ValueError('AVAILABILITY_BEFORE_SOURCE_TIME')
        if ingestion < available: raise ValueError('INGESTION_BEFORE_AVAILABLE_TIME')
        self._rows.append(row)
    def as_of(self, security_id: str, decision_time: str):
        decision=parse_utc(decision_time)
        rows=[r for r in self._rows if r.security_id==security_id and parse_utc(r.available_time)<=decision]
        return sorted(rows,key=lambda x:(parse_utc(x.available_time),parse_utc(x.event_time),x.source_id))
    def latest_by_event(self, security_id: str, decision_time: str):
        rows=self.as_of(security_id,decision_time); latest={}
        for r in rows: latest[(r.dataset,r.event_time)]=r
        return sorted(latest.values(),key=lambda x:(x.dataset,parse_utc(x.event_time)))
