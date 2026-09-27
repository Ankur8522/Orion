from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from orion.data.providers import ProviderObservation, validate_observation
from orion.data.time import parse_utc

READINESS_STATES = ('READY','PARTIAL','DEPENDENCY','BLOCKED','NOT_CONFIGURED','CONFIGURED_NOT_VERIFIED','OFFLINE','STALE','RECONCILIATION_REQUIRED','NO_HISTORY','NO_SUCCESS_OBSERVATION')

@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    configured: bool
    authenticated: bool
    capabilities: tuple[str,...]
    reason: str
    last_success_at: str | None = None
    stale_after_seconds: int = 86400
    historical_datasets: tuple[str,...] = ()

class DataPlaneRegistry:
    """Explicit provider boundary with dataset-specific readiness and freshness.

    Configuration never implies dataset readiness. A dataset becomes READY only
    when an authenticated capable provider has a successful observation; historical
    replay additionally requires explicit historical coverage.
    """
    def __init__(self): self._providers={}; self._dataset_success={}
    def register(self, provider: str, *, configured=False, authenticated=False, capabilities: Sequence[str]=(), reason='NOT_CONFIGURED', last_success_at: str | None = None, stale_after_seconds: int = 86400, historical_datasets: Sequence[str]=()):
        if not provider: raise ValueError('INVALID_PROVIDER')
        if stale_after_seconds <= 0: raise ValueError('INVALID_STALE_AFTER')
        self._providers[provider]=ProviderStatus(provider,bool(configured),bool(authenticated),tuple(sorted(set(capabilities))),reason,last_success_at,int(stale_after_seconds),tuple(sorted(set(historical_datasets))))
        if last_success_at:
            for dataset in capabilities: self._dataset_success[dataset]=last_success_at
    def statuses(self): return tuple(self._providers[k] for k in sorted(self._providers))
    def ingest(self, observation: ProviderObservation, *, decision_time: str | None = None):
        validate_observation(observation, strict=True)
        if not self.ready(observation.provider): raise ValueError('PROVIDER_NOT_READY')
        if observation.dataset not in self._providers[observation.provider].capabilities: raise ValueError('DATASET_CAPABILITY_UNSUPPORTED')
        if decision_time is not None and parse_utc(observation.available_time) > parse_utc(decision_time): raise ValueError('FUTURE_INFORMATION')
        self.record_success(observation.provider, observation.available_time, dataset=observation.dataset)
        return {'accepted':True,'provider':observation.provider,'dataset':observation.dataset,'security_id':observation.security_id,'available_time':observation.available_time,'payload_hash':observation.payload_hash,'quality':observation.quality,'lineage_id':observation.lineage_id}
    def mark_authenticated(self, provider: str, *, reason='AUTHENTICATED'):
        current=self._providers.get(provider)
        if current is None: raise KeyError('PROVIDER_NOT_FOUND')
        from dataclasses import replace
        self._providers[provider]=replace(current,authenticated=True,reason=reason)

    def record_success(self, provider: str, available_time: str, *, dataset: str | None = None):
        current=self._providers.get(provider)
        if current is None: raise KeyError('PROVIDER_NOT_FOUND')
        from dataclasses import replace
        self._providers[provider]=replace(current,last_success_at=available_time,reason='READY')
        if dataset: self._dataset_success[dataset]=available_time
    def coverage(self, datasets: Sequence[str], *, historical=False, now: str | None = None) -> dict:
        statuses=self.statuses(); result={}
        for dataset in datasets:
            providers=[x for x in statuses if dataset in x.capabilities]
            configured=[x for x in providers if x.configured]
            authenticated=[x for x in configured if x.authenticated]
            historical_capable=[x for x in authenticated if dataset in x.historical_datasets]
            last=self._dataset_success.get(dataset) or next((x.last_success_at for x in authenticated if x.last_success_at),None)
            status='NOT_CONFIGURED' if not providers else ('CONFIGURED_NOT_VERIFIED' if configured and not authenticated else ('DEPENDENCY' if not authenticated else ('NO_HISTORY' if historical and not historical_capable else ('NO_SUCCESS_OBSERVATION' if not last else 'READY'))))
            if now and last and status=='READY':
                age=(parse_utc(now)-parse_utc(last)).total_seconds()
                if age<0: status='OFFLINE'
                elif age>min(x.stale_after_seconds for x in authenticated): status='STALE'
            result[dataset]={'ready':status=='READY','providers':tuple(x.provider for x in providers),'status':status,'last_success_at':last,'historical':bool(historical_capable)}
        states=[x['status'] for x in result.values()]
        return {'provider_ready':any(x['ready'] for x in result.values()),'datasets':result,'status':'READY' if states and all(x=='READY' for x in states) else ('PARTIAL' if any(x=='READY' for x in states) else (states[0] if states else 'NOT_CONFIGURED'))}
    def freshness(self, now: str):
        out=[]
        for x in self.statuses():
            status='NOT_CONFIGURED' if not x.configured else ('DEPENDENCY' if not x.authenticated else 'READY')
            if status=='READY' and x.last_success_at:
                age=(parse_utc(now)-parse_utc(x.last_success_at)).total_seconds()
                if age<0: status='OFFLINE'
                elif age>x.stale_after_seconds: status='STALE'
            elif status=='READY': status='NO_SUCCESS_OBSERVATION'
            out.append({'provider':x.provider,'status':status,'last_success_at':x.last_success_at,'stale_after_seconds':x.stale_after_seconds})
        return tuple(out)
    def ready(self, provider):
        x=self._providers.get(provider); return bool(x and x.configured and x.authenticated)
