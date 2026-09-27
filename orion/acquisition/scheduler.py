from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable
from .universe_batch import MarketBatchManifest
from .market_executor import MarketBatchExecutor, BatchExecutionReport
from ..data.store import SQLiteStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

@dataclass(frozen=True)
class SchedulerReport:
    manifest_id: str
    status: str
    batches_total: int
    batches_completed: int
    batches_remaining: int
    jobs_ready: int
    jobs_blocked: int
    jobs_failed: int
    coverage: dict

class AcquisitionScheduler:
    """Persistent, deterministic scheduler over a MarketBatchManifest.

    The scheduler is deliberately single-worker: it guarantees deterministic
    ordering and safe SQLite checkpointing. Concurrency can be added later at
    the job layer without changing the persisted contract.
    """
    def __init__(self, executor: MarketBatchExecutor, store: SQLiteStore, *, clock: Callable[[], str] = _now):
        self.executor, self.store, self.clock = executor, store, clock

    def register(self, manifest: MarketBatchManifest) -> None:
        self.store.market_batch_manifest(manifest, self.clock())
        self.store.market_schedule_register(manifest, self.clock())

    def run(self, manifest: MarketBatchManifest, *, max_batches: int | None = None) -> SchedulerReport:
        self.register(manifest)
        if max_batches is not None and max_batches < 1:
            raise ValueError('INVALID_MAX_BATCHES')
        state = self.store.market_schedule_state(manifest.manifest_id)
        start = int(state.get('next_batch', 0)) if state else 0
        end = min(len(manifest.batches), start + max_batches) if max_batches else len(manifest.batches)
        completed = start
        failed = blocked = ready = 0
        for index in range(start, end):
            ids = manifest.batches[index]
            report: BatchExecutionReport = self.executor.execute(manifest, job_ids=ids)
            ready += report.promoted + report.skipped
            blocked += report.blocked
            failed += report.failed
            # A batch is checkpointed after every job has reached a terminal state.
            if report.attempted + report.skipped >= len(ids):
                completed = index + 1
                self.store.market_schedule_checkpoint(manifest.manifest_id, completed, self.clock())
            else:
                break
        remaining = max(0, len(manifest.batches) - completed)
        status = 'COMPLETE' if remaining == 0 else ('BLOCKED' if blocked and not ready and not failed else 'PARTIAL')
        coverage = self.store.market_batch_coverage(manifest.manifest_id, decision_time=manifest.decision_time)
        return SchedulerReport(manifest.manifest_id,status,len(manifest.batches),completed,remaining,ready,blocked,failed,coverage)
