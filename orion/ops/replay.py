from __future__ import annotations
import json
from pathlib import Path
from hashlib import sha256
from ..data.time import parse_utc

SCHEMA_VERSION=3

def _hash(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def write_replay(path, request):
    if not isinstance(request, dict): raise ValueError('INVALID_REPLAY_REQUEST')
    decision_time=request.get('decision_time')
    if decision_time is not None: parse_utc(decision_time)
    input_hash=request.get('input_hash') or _hash(request.get('inputs', request))
    config_hash=request.get('config_hash') or _hash(request.get('config', {}))
    prompt_hash=request.get('prompt_hash') or _hash(request.get('prompt', ''))
    output_hash=request.get('output_hash')
    envelope={'schema_version':SCHEMA_VERSION,'request':dict(request),'input_hash':input_hash,'config_hash':config_hash,'prompt_hash':prompt_hash,'output_hash':output_hash}
    Path(path).write_text(json.dumps(envelope,sort_keys=True,indent=2),encoding='utf-8')

def load_replay(path, *, expected_config_hash=None, expected_prompt_hash=None, expected_output=None):
    obj=json.loads(Path(path).read_text(encoding='utf-8'))
    if obj.get('schema_version') not in (1,2,SCHEMA_VERSION): raise ValueError('UNSUPPORTED_REPLAY_SCHEMA')
    request=obj['request']
    expected=obj.get('input_hash')
    actual=request.get('input_hash') or _hash(request.get('inputs', request))
    if expected!=actual: raise ValueError('REPLAY_INPUT_INTEGRITY_FAILURE')
    if request.get('decision_time') is not None: parse_utc(request['decision_time'])
    if obj.get('schema_version') >= 3:
        config_hash=obj.get('config_hash')
        prompt_hash=obj.get('prompt_hash')
        if not config_hash or len(config_hash)!=64: raise ValueError('INVALID_REPLAY_CONFIG_HASH')
        if not prompt_hash or len(prompt_hash)!=64: raise ValueError('INVALID_REPLAY_PROMPT_HASH')
        if expected_config_hash is not None and config_hash != expected_config_hash: raise ValueError('REPLAY_CONFIG_MISMATCH')
        if expected_prompt_hash is not None and prompt_hash != expected_prompt_hash: raise ValueError('REPLAY_PROMPT_MISMATCH')
        stored_output=obj.get('output_hash')
        if expected_output is not None:
            actual_output=_hash(expected_output)
            if stored_output != actual_output: raise ValueError('REPLAY_OUTPUT_MISMATCH')
    return request
