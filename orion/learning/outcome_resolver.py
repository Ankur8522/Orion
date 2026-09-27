from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from .feedback import ForecastLedger, ForecastRecord, OutcomeRecord, ForecastScore

@dataclass(frozen=True)
class ObservableOutcome:
    event_key: str
    security_id: str
    occurred: bool
    available_time: str
    source_id: str
    content_hash: str
    return_pct: float | None = None
    max_drawdown: float | None = None
    mae: float | None = None
    mfe: float | None = None
    time_to_target_days: float | None = None

@dataclass(frozen=True)
class ResolutionReport:
    attempted: int
    resolved: int
    skipped: int
    scores: tuple[ForecastScore, ...]
    unresolved_forecast_ids: tuple[str, ...]

class ForecastOutcomeResolver:
    """Resolves only forecasts whose horizon has elapsed and whose outcome is supplied."""
    @staticmethod
    def _utc(v: str) -> datetime:
        d=datetime.fromisoformat(v.replace('Z','+00:00'))
        if d.tzinfo is None: raise ValueError('NAIVE_TIMESTAMP')
        return d.astimezone(timezone.utc)

    def resolve(self, ledger: ForecastLedger, observations: Iterable[ObservableOutcome], *, evaluation_time: str) -> ResolutionReport:
        by_key={(o.security_id,o.event_key): o for o in observations}
        attempted=resolved=skipped=0; scores=[]
        for f in ledger.forecasts():
            key=(f.security_id,f.event_key)
            if key not in by_key:
                skipped += 1; continue
            if self._utc(f.horizon_end) > self._utc(evaluation_time):
                skipped += 1; continue
            o=by_key[key]
            if self._utc(o.available_time) > self._utc(evaluation_time):
                skipped += 1
                continue
            if self._utc(o.available_time) < self._utc(f.horizon_end):
                skipped += 1
                continue
            attempted += 1
            outcome=OutcomeRecord(f.forecast_id,o.occurred,o.available_time,o.source_id,tuple(f.evidence_ids),o.content_hash,o.return_pct,o.max_drawdown,o.mae,o.mfe,o.time_to_target_days)
            try:
                scores.append(ledger.resolve(outcome,evaluation_time=evaluation_time)); resolved += 1
            except (ValueError, KeyError):
                skipped += 1
        unresolved=tuple(f.forecast_id for f in ledger.forecasts() if f.forecast_id not in {s.forecast_id for s in scores})
        return ResolutionReport(attempted,resolved,skipped,tuple(scores),unresolved)
