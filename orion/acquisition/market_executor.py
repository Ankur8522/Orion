from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable
from .market_data import MarketDataJob, MarketDataJobResult, UpstoxMarketDataAcquirer
from .universe_batch import MarketBatchManifest
from ..data.store import SQLiteStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

@dataclass(frozen=True)
class BatchExecutionReport:
    manifest_id: str
    attempted: int
    promoted: int
    blocked: int
    failed: int
    skipped: int
    results: tuple[MarketDataJobResult, ...]
    coverage: dict

class MarketBatchExecutor:
    """Resumable, persistent executor for the read-only market acquisition plan.

    It executes only planned jobs, checkpoints each terminal state, and can be
    safely rerun: PROMOTED jobs are skipped. It never places orders.
    """
    def __init__(self, acquirer: UpstoxMarketDataAcquirer, store: SQLiteStore, *, clock: Callable[[], str] = _now):
        self.acquirer, self.store, self.clock = acquirer, store, clock

    def register(self, manifest: MarketBatchManifest) -> None:
        self.store.market_batch_manifest(manifest, self.clock())

    def execute(self, manifest: MarketBatchManifest, *, job_ids: Iterable[str] | None = None) -> BatchExecutionReport:
        self.register(manifest)
        allowed = set(job_ids) if job_ids is not None else None
        persisted = {r['job_id']: r for r in self.store.market_batch_jobs(manifest.manifest_id)}
        results=[]; attempted=promoted=blocked=failed=skipped=0
        for job in manifest.jobs:
            if allowed is not None and job.job_id not in allowed:
                continue
            current=persisted.get(job.job_id, {})
            if current.get('state') == 'PROMOTED':
                skipped += 1
                continue
            attempted += 1
            self.store.market_batch_state(job.job_id,'RUNNING',self.clock())
            result=self.acquirer.acquire(job)
            results.append(result)
            if result.state == 'PROMOTED':
                promoted += 1
            elif result.state == 'BLOCKED':
                blocked += 1
            else:
                failed += 1
            self.store.market_batch_state(job.job_id,result.state,self.clock(),result.error)
        coverage=self.store.market_batch_coverage(manifest.manifest_id, decision_time=manifest.decision_time)
        return BatchExecutionReport(manifest.manifest_id,attempted,promoted,blocked,failed,skipped,tuple(results),coverage)
