from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from ..providers.upstox import UpstoxNormalizer, RawEnvelope
from ..data.time import parse_utc

@dataclass(frozen=True)
class RuntimeResult:
    security_id: str
    dataset: str
    rows: int
    manifest_hash: str
    state: str
    blockers: tuple[str,...]=()

class RealDataVerticalRuntime:
    """Provider response -> raw envelope -> normalized PIT observations -> governed research."""
    def __init__(self, store, execution, provider='upstox'):
        self.store=store; self.execution=execution; self.provider=provider

    @staticmethod
    def _manifest(obj):
        return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

    def ingest_upstox_candles(self, *, security_id, instrument_key, payload, event_time, available_time, captured_at, decision_time):
        parse_utc(event_time); parse_utc(available_time); parse_utc(captured_at); parse_utc(decision_time)
        if parse_utc(available_time) > parse_utc(decision_time):
            return RuntimeResult(security_id,'ohlcv',0,self._manifest({'security_id':security_id,'decision_time':decision_time}), 'BLOCKED', ('FUTURE_INFORMATION',))
        raw=UpstoxNormalizer.raw_json(payload)
        env=RawEnvelope.create('ohlcv',instrument_key,raw,event_time,available_time)
        rows=UpstoxNormalizer.candles(payload,instrument_key,available_time)
        normalized=[]
        for row in rows:
            row={**row,'security_id':security_id,'source_id':'upstox','captured_at':captured_at,'payload_hash':env.payload_sha256}
            if parse_utc(row['event_time']) > parse_utc(decision_time):
                continue
            normalized.append(row)
        obs=self.execution.ingest_market_observations(normalized,decision_time=decision_time)
        manifest={'provider':self.provider,'security_id':security_id,'dataset':'ohlcv','instrument_key':instrument_key,'payload_hash':env.payload_sha256,'rows':len(obs),'decision_time':decision_time}
        return RuntimeResult(security_id,'ohlcv',len(obs),self._manifest(manifest),'READY' if obs else 'DEFER',() if obs else ('NO_PIT_OBSERVATIONS',))
