from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence
from hashlib import sha256
import json

class CapabilityState(str, Enum):
    READY='READY'; NOT_CONFIGURED='NOT_CONFIGURED'; UNSUPPORTED='UNSUPPORTED'; STALE='STALE'; NO_SUCCESS_OBSERVATION='NO_SUCCESS_OBSERVATION'

@dataclass(frozen=True)
class ProviderCapability:
    provider: str
    dataset: str
    state: CapabilityState
    read_only: bool=True
    last_success: str|None=None
    source_priority: int=100
    notes: str=''

@dataclass(frozen=True)
class ProviderCapabilityMatrix:
    rows: tuple[ProviderCapability,...]
    lineage_hash: str
    def state(self, provider:str, dataset:str)->CapabilityState:
        for r in self.rows:
            if r.provider==provider and r.dataset==dataset: return r.state
        return CapabilityState.UNSUPPORTED
    @property
    def connected_datasets(self): return tuple(sorted({r.dataset for r in self.rows if r.state==CapabilityState.READY}))

class ProviderCapabilityRegistry:
    def __init__(self): self._rows: dict[tuple[str,str],ProviderCapability]={}
    def register(self, capability: ProviderCapability):
        if not capability.provider or not capability.dataset: raise ValueError('INVALID_PROVIDER_CAPABILITY')
        if not capability.read_only: raise ValueError('NON_READ_ONLY_PROVIDER_FORBIDDEN')
        self._rows[(capability.provider,capability.dataset)]=capability
    def matrix(self)->ProviderCapabilityMatrix:
        rows=tuple(self._rows[k] for k in sorted(self._rows))
        digest=sha256(json.dumps([r.__dict__ for r in rows],sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
        return ProviderCapabilityMatrix(rows,digest)
