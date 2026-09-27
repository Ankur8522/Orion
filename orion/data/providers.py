from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any
from datetime import datetime, timezone

class FeedMode(str, Enum):
    PUBLIC = 'public'
    LICENSED = 'licensed'

@dataclass(frozen=True)
class ProviderObservation:
    provider: str
    dataset: str
    security_id: str
    event_time: str
    available_time: str
    payload_hash: str
    licensed: bool
    effective_time: str | None = None
    observation_time: str | None = None
    quality: str = 'UNASSESSED'
    source_priority: int = 100
    lineage_id: str | None = None
    source_time: str | None = None
    ingestion_time: str | None = None

class ProviderStatus(str, Enum):
    READY = 'READY'
    NOT_CONFIGURED = 'NOT_CONFIGURED'
    STALE = 'STALE'
    NO_SUCCESS_OBSERVATION = 'NO_SUCCESS_OBSERVATION'
    UNSUPPORTED = 'UNSUPPORTED'

@dataclass(frozen=True)
class ProviderDatasetReadiness:
    provider: str
    dataset: str
    status: ProviderStatus
    authenticated: bool
    last_success_at: str | None
    stale_after_seconds: int | None
    reason: str

@dataclass(frozen=True)
class ProviderContract:
    name: str
    mode: FeedMode
    datasets: frozenset[str]
    authenticated: bool = False
    last_success_at: str | None = None
    stale_after_seconds: int = 86400
    historical: bool = False

class ProviderRegistry:
    def __init__(self): self._providers = {}
    def register(self, contract: ProviderContract):
        if contract.name in self._providers: raise ValueError('DUPLICATE_PROVIDER')
        self._providers[contract.name] = contract
    def resolve(self, dataset: str, mode: FeedMode):
        return [p for p in self._providers.values() if dataset in p.datasets and p.mode == mode]

    def readiness(self, dataset: str, *, mode: FeedMode | None = None, as_of: str | None = None) -> tuple[ProviderDatasetReadiness, ...]:
        """Return explicit provider/dataset readiness without inventing coverage.

        ``last_success_at`` is deliberately provider-supplied metadata. A provider
        with credentials but no verified successful observation is NOT_READY.
        """
        cutoff = None
        if as_of is not None:
            cutoff = _parse_utc(as_of)
        rows=[]
        candidates=[p for p in self._providers.values() if dataset in p.datasets and (mode is None or p.mode == mode)]
        for p in sorted(candidates, key=lambda x: (x.name, x.mode.value)):
            if not p.authenticated:
                status, reason = ProviderStatus.NOT_CONFIGURED, 'AUTHENTICATION_NOT_CONFIGURED'
            elif not p.last_success_at:
                status, reason = ProviderStatus.NO_SUCCESS_OBSERVATION, 'NO_VERIFIED_SUCCESS_OBSERVATION'
            else:
                try:
                    last=_parse_utc(p.last_success_at)
                    reference=cutoff or datetime.now(timezone.utc)
                    age=(reference-last).total_seconds()
                    if age < 0:
                        status, reason = ProviderStatus.NOT_CONFIGURED, 'SUCCESS_TIMESTAMP_IN_FUTURE'
                    elif age > p.stale_after_seconds:
                        status, reason = ProviderStatus.STALE, 'LAST_SUCCESS_EXCEEDS_STALE_WINDOW'
                    else:
                        status, reason = ProviderStatus.READY, 'RECENT_SUCCESS_OBSERVATION'
                except ValueError:
                    status, reason = ProviderStatus.STALE, 'INVALID_LAST_SUCCESS_TIMESTAMP'
            rows.append(ProviderDatasetReadiness(p.name,dataset,status,p.authenticated,p.last_success_at,p.stale_after_seconds,reason))
        if not rows:
            return (ProviderDatasetReadiness('',dataset,ProviderStatus.UNSUPPORTED,False,None,None,'NO_PROVIDER_FOR_DATASET'),)
        return tuple(rows)

    def dataset_status(self, dataset: str, *, mode: FeedMode | None = None, as_of: str | None = None) -> ProviderStatus:
        rows=self.readiness(dataset, mode=mode, as_of=as_of)
        if any(r.status == ProviderStatus.READY for r in rows): return ProviderStatus.READY
        if any(r.status == ProviderStatus.STALE for r in rows): return ProviderStatus.STALE
        if any(r.status == ProviderStatus.NO_SUCCESS_OBSERVATION for r in rows): return ProviderStatus.NO_SUCCESS_OBSERVATION
        if any(r.status == ProviderStatus.NOT_CONFIGURED for r in rows): return ProviderStatus.NOT_CONFIGURED
        return ProviderStatus.UNSUPPORTED

def _parse_utc(value: str) -> datetime:
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('NAIVE_TIMESTAMP')
    return dt.astimezone(timezone.utc)

def hash_payload(raw: bytes) -> str:
    return sha256(raw).hexdigest()

def validate_observation(o: ProviderObservation, strict=True):
    from .time import parse_utc
    if not o.provider or not o.dataset or not o.security_id: raise ValueError('INVALID_OBSERVATION_IDENTITY')
    if not o.payload_hash or len(o.payload_hash) != 64 or any(c not in '0123456789abcdefABCDEF' for c in o.payload_hash): raise ValueError('INVALID_PAYLOAD_HASH')
    event=parse_utc(o.event_time); available=parse_utc(o.available_time)
    effective=parse_utc(o.effective_time) if o.effective_time else event
    observed=parse_utc(o.observation_time) if o.observation_time else event
    source=parse_utc(o.source_time) if o.source_time else observed
    ingestion=parse_utc(o.ingestion_time) if o.ingestion_time else available
    if available < effective: raise ValueError('AVAILABILITY_BEFORE_EFFECTIVE')
    if available < observed: raise ValueError('AVAILABILITY_BEFORE_OBSERVATION')
    if available < source: raise ValueError('AVAILABILITY_BEFORE_SOURCE_TIME')
    if ingestion < available: raise ValueError('INGESTION_BEFORE_AVAILABLE_TIME')
    if o.source_priority < 0: raise ValueError('INVALID_SOURCE_PRIORITY')
    if strict and not all(x.endswith('Z') for x in (o.event_time,o.available_time) if x): raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    if o.effective_time and not o.effective_time.endswith('Z'): raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    if o.observation_time and not o.observation_time.endswith('Z'): raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    if o.source_time and not o.source_time.endswith('Z'): raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    if o.ingestion_time and not o.ingestion_time.endswith('Z'): raise ValueError('NAIVE_OR_UNNORMALIZED_TIMESTAMP')
    return True
