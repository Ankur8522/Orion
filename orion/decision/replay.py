from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
@dataclass(frozen=True)
class RunManifest:
    schema_version:int; run_id:str; config_version:str; prompt_version:str; input_hash:str; decision_time:str; mode:str
    def digest(self): return sha256(json.dumps(self.__dict__,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class ReplayGuard:
    def validate(self, manifest:RunManifest, *, expected_mode='RESEARCH'):
        if manifest.mode!=expected_mode: raise ValueError('INVALID_REPLAY_MODE')
        if not manifest.input_hash or len(manifest.input_hash)!=64: raise ValueError('INVALID_INPUT_HASH')
        return manifest.digest()
