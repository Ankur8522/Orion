from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence
from .time import parse_utc

class DatasetState(str, Enum):
    READY='READY'; PARTIAL='PARTIAL'; MISSING='MISSING'; STALE='STALE'; NOT_CONFIGURED='NOT_CONFIGURED'; UNSUPPORTED='UNSUPPORTED'; DEGRADED='DEGRADED'

@dataclass(frozen=True)
class DatasetObservation:
    dataset: str
    security_id: str
    source_id: str
    source_time: str | None
    effective_time: str | None
    available_time: str
    ingestion_time: str
    payload_hash: str
    values: Mapping[str, Any]

@dataclass(frozen=True)
class DatasetSnapshot:
    dataset: str
    security_id: str
    state: DatasetState
    rows: tuple[DatasetObservation,...]
    latest_available_time: str | None
    completeness: float
    blockers: tuple[str,...]
    lineage_hash: str
    selected: DatasetObservation | None = None

class CanonicalDataFabric:
    """Canonical, PIT-aware dataset boundary shared by research and intelligence."""
    def __init__(self): self._datasets: dict[tuple[str,str], list[DatasetObservation]]={}
    def ingest(self, observation: DatasetObservation, *, decision_time: str | None = None):
        parse_utc(observation.available_time); parse_utc(observation.ingestion_time)
        if observation.source_time: parse_utc(observation.source_time)
        if observation.effective_time: parse_utc(observation.effective_time)
        if decision_time and parse_utc(observation.available_time)>parse_utc(decision_time): raise ValueError('FUTURE_OBSERVATION')
        self._datasets.setdefault((observation.dataset,observation.security_id),[]).append(observation)
    def snapshot(self, dataset: str, security_id: str, *, decision_time: str, max_age_seconds: float|None=None) -> DatasetSnapshot:
        rows=[]; blockers=[]
        cutoff=parse_utc(decision_time)
        for r in self._datasets.get((dataset,security_id),[]):
            if parse_utc(r.available_time)<=cutoff: rows.append(r)
        rows.sort(key=lambda x:(x.available_time,x.effective_time or '',x.source_time or '',x.payload_hash))
        latest=rows[-1].available_time if rows else None
        selected=None
        if rows:
            # Point-in-time selection: latest observation available by decision cutoff;
            # for restatements sharing an effective/source date, the latest available wins.
            selected=max(rows,key=lambda x:(x.effective_time or x.source_time or x.available_time,x.available_time,x.ingestion_time,x.payload_hash))
        state=DatasetState.READY if rows else DatasetState.MISSING
        if latest and max_age_seconds is not None and (cutoff-parse_utc(latest)).total_seconds()>max_age_seconds: state=DatasetState.STALE; blockers.append('STALE_DATASET')
        payload={'dataset':dataset,'security_id':security_id,'state':state.value,'rows':[r.payload_hash for r in rows],'latest':latest,'blockers':blockers}
        return DatasetSnapshot(dataset,security_id,state,tuple(rows),latest,1.0 if rows else 0.0,tuple(blockers),sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(),selected)
    def snapshot_many(self, security_id: str, datasets: Sequence[str], *, decision_time: str, max_age_seconds: float|None=None):
        return {d:self.snapshot(d,security_id,decision_time=decision_time,max_age_seconds=max_age_seconds) for d in datasets}
