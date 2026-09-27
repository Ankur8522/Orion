from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from ..data.time import parse_utc


@dataclass(frozen=True)
class HistoricalPatternMatch:
    security_id: str
    anchor_time: str
    distance: float
    forward_return: float | None
    available_time: str


@dataclass(frozen=True)
class HistoricalPatternResult:
    security_id: str
    as_of: str
    pattern_score: float
    matches: tuple[HistoricalPatternMatch, ...]
    eligible_matches: int
    warnings: tuple[str, ...]


class HistoricalPatternEngine:
    """PIT-safe nearest-pattern search over supplied OHLC/return history.

    A match may only use an anchor whose information was available by `as_of`.
    Forward returns are labels only; they are never included in the similarity vector.
    """

    def find(self, security_id: str, rows: Sequence[Mapping[str, object]], *, as_of: str, window: int = 20, horizon: int = 20, top_k: int = 10, min_history_gap: int = 5) -> HistoricalPatternResult:
        if window < 3 or horizon < 1 or top_k < 1:
            raise ValueError("INVALID_PATTERN_PARAMETERS")
        decision = parse_utc(as_of)
        ordered = sorted(rows, key=lambda r: (parse_utc(str(r["event_time"])), str(r.get("security_id", ""))))
        usable = [r for r in ordered if parse_utc(str(r["available_time"])) <= decision and parse_utc(str(r["event_time"])) <= decision]
        returns = [float(r["return"]) for r in usable if r.get("return") is not None]
        if len(returns) < window + min_history_gap + horizon:
            return HistoricalPatternResult(security_id, as_of, 0.5, (), 0, ("INSUFFICIENT_PATTERN_HISTORY",))
        current = returns[-window:]
        candidates: list[HistoricalPatternMatch] = []
        # Candidate anchors end far enough before the current window to avoid overlap contamination.
        max_anchor = len(returns) - window - min_history_gap
        for end in range(window, max_anchor + 1):
            anchor = returns[end-window:end]
            dist = sqrt(sum((a-b) ** 2 for a, b in zip(current, anchor)) / window)
            row = usable[end-1]
            forward = None
            if end + horizon <= len(returns):
                forward = sum(returns[end:end+horizon])
            candidates.append(HistoricalPatternMatch(security_id, str(row["event_time"]), dist, forward, str(row["available_time"])))
        candidates.sort(key=lambda m: (m.distance, m.anchor_time))
        selected = tuple(candidates[:top_k])
        labeled = [m.forward_return for m in selected if m.forward_return is not None]
        score = 0.5
        if labeled:
            # Convert the historical conditional mean into a bounded probability-like score.
            mean = sum(labeled) / len(labeled)
            score = max(0.0, min(1.0, 0.5 + mean * 5.0))
        warnings = () if labeled else ("PATTERN_OUTCOME_NOT_MATURED",)
        return HistoricalPatternResult(security_id, as_of, round(score, 12), selected, len(selected), warnings)
