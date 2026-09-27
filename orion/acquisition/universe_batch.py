from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping
from .market_data import MarketDataJob
from ..data.time import parse_utc

@dataclass(frozen=True)
class UniverseMarketRequest:
    universe_name: str
    security_id: str
    instrument_key: str | None
    indexes: tuple[str, ...]

@dataclass(frozen=True)
class MarketBatchManifest:
    manifest_id: str
    decision_time: str
    universe_names: tuple[str, ...]
    requests: tuple[UniverseMarketRequest, ...]
    jobs: tuple[MarketDataJob, ...]
    blocked: tuple[str, ...]
    batches: tuple[tuple[str, ...], ...]

class UniverseMarketDataPlanner:
    """Deterministic 450-slot market-data planner.

    It consumes an authorized/historical universe snapshot plus a verified
    security->provider instrument mapping. It never invents constituents or
    instrument keys and never performs network calls.
    """
    def __init__(self, *, batch_size: int = 25):
        if batch_size <= 0:
            raise ValueError('INVALID_BATCH_SIZE')
        self.batch_size = int(batch_size)

    def plan(
        self,
        memberships: Iterable[Mapping[str, object]],
        instrument_keys: Mapping[str, str],
        *,
        decision_time: str,
        from_date: str,
        to_date: str,
        unit: str = 'days',
        interval: int = 1,
        universe_names: Iterable[str] = ('NIFTY50','NIFTY_MIDCAP150','NIFTY_SMALLCAP250'),
    ) -> MarketBatchManifest:
        parse_utc(decision_time)
        names = tuple(sorted(dict.fromkeys(universe_names)))
        rows = [m for m in memberships if str(m.get('index','')) in names and m.get('active', True)]
        # Historical/PIT membership filtering is deliberately caller-owned; the
        # planner receives the already-governed snapshot and only plans work.
        grouped: dict[str, set[str]] = {n: set() for n in names}
        for row in rows:
            sid = str(row.get('security_id','')).strip()
            idx = str(row.get('index','')).strip()
            if sid and idx in grouped:
                grouped[idx].add(sid)

        requests: list[UniverseMarketRequest] = []
        blocked: list[str] = []
        jobs: list[MarketDataJob] = []
        # One security can belong to multiple index slots. Plan one acquisition
        # job per unique security while retaining all index provenance.
        all_ids = sorted({sid for ids in grouped.values() for sid in ids})
        for sid in all_ids:
            idxs = tuple(n for n in names if sid in grouped[n])
            key = str(instrument_keys.get(sid, '')).strip()
            requests.append(UniverseMarketRequest('ALL_TARGETS', sid, key or None, idxs))
            if not key:
                blocked.append(f'{sid}:ohlcv:NO_INSTRUMENT_MAPPING')
                continue
            job_id = sha256(f'upstox|{sid}|{key}|ohlcv|{decision_time}|{from_date}|{to_date}|{unit}|{interval}'.encode()).hexdigest()
            jobs.append(MarketDataJob(job_id, sid, key, unit, interval, to_date, from_date, decision_time))

        ids = tuple(j.job_id for j in jobs)
        batches = tuple(tuple(ids[i:i+self.batch_size]) for i in range(0, len(ids), self.batch_size))
        manifest_id = sha256('|'.join(['market', *names, decision_time, from_date, to_date, *sorted(ids)]).encode()).hexdigest()
        return MarketBatchManifest(manifest_id, decision_time, names, tuple(requests), tuple(jobs), tuple(sorted(blocked)), batches)
