from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class RuntimeHealth:
    status: str
    journal_integrity: bool
    live_trading_enabled: bool
    research_ready: bool
    brain_ready: bool
    paper_ready: bool
    reasons: tuple[str, ...]


def evaluate_health(control_plane) -> RuntimeHealth:
    reasons=[]
    journal_ok=control_plane.journal.verify()
    paper_ok=not control_plane.service.paper.live_trading_enabled()
    if not journal_ok: reasons.append('JOURNAL_INTEGRITY_FAILURE')
    if not paper_ok: reasons.append('LIVE_TRADING_BOUNDARY_FAILURE')
    return RuntimeHealth('OK' if not reasons else 'DEGRADED', journal_ok, not paper_ok, True, True, paper_ok, tuple(reasons))
