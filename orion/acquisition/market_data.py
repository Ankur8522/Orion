from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Iterable

from ..data.store import SQLiteStore
from ..data.providers import ProviderObservation
from ..data.time import parse_utc
from ..providers.upstox_readonly import UpstoxReadOnlyClient

@dataclass(frozen=True)
class MarketDataJob:
    job_id: str
    security_id: str
    instrument_key: str
    unit: str
    interval: int
    to_date: str
    from_date: str
    decision_time: str

@dataclass(frozen=True)
class MarketDataJobResult:
    job_id: str
    security_id: str
    state: str
    rows: int
    payload_hash: str | None
    error: str | None = None

class UpstoxMarketDataAcquirer:
    """PIT-safe bridge from the read-only provider into ORION's durable corpus.

    It never places orders. A fetch is promoted to the corpus only after its
    provider payload has been validated against the job decision time.
    """
    def __init__(self, client: UpstoxReadOnlyClient, store: SQLiteStore):
        self.client, self.store = client, store

    def acquire(self, job: MarketDataJob, *, captured_at: str | None = None) -> MarketDataJobResult:
        try:
            decision = parse_utc(job.decision_time)
            result = self.client.historical_candles(job.instrument_key, job.unit, job.interval, job.to_date, job.from_date)
            envelope = result.envelope
            available = parse_utc(envelope.available_time)
            if available > decision:
                return MarketDataJobResult(job.job_id, job.security_id, 'BLOCKED', 0, envelope.payload_sha256, 'FUTURE_INFORMATION')
            # Store the raw provider payload as the durable source observation.
            captured = captured_at or envelope.captured_at
            payload = {
                'provider': envelope.provider,
                'instrument_key': envelope.instrument_key,
                'rows': list(result.rows),
                'event_time': envelope.event_time,
                'available_time': envelope.available_time,
                'raw_payload_sha256': envelope.payload_sha256,
            }
            self.store.insert_observation(
                security_id=job.security_id,
                dataset='ohlcv',
                event_time=envelope.event_time,
                available_time=envelope.available_time,
                source_id='upstox',
                payload_hash=envelope.payload_sha256,
                payload=payload,
                captured_at=captured,
            )
            self.store.source_capture(
                capture_id=sha256(f'upstox|{job.instrument_key}|{envelope.payload_sha256}'.encode()).hexdigest(),
                source_id='upstox', url='upstox://historical-candle', payload_hash=envelope.payload_sha256,
                captured_at=captured, content_type='application/json', byte_size=len(envelope.raw_payload),
            )
            return MarketDataJobResult(job.job_id, job.security_id, 'PROMOTED', len(result.rows), envelope.payload_sha256)
        except Exception as exc:
            return MarketDataJobResult(job.job_id, job.security_id, 'FAILED', 0, None, type(exc).__name__ + ':' + str(exc))

    def acquire_many(self, jobs: Iterable[MarketDataJob]) -> tuple[MarketDataJobResult, ...]:
        return tuple(self.acquire(j) for j in jobs)
