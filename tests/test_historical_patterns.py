from datetime import datetime, timedelta, timezone
from orion.research.historical_patterns import HistoricalPatternEngine


def test_pattern_engine_uses_only_pit_safe_history():
    rows=[]
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    for i in range(80):
        ts=(start+timedelta(days=i)).strftime("%Y-%m-%dT00:00:00Z")
        rows.append({"security_id":"X", "event_time":ts, "available_time":ts, "return":0.01 if i % 4 == 0 else 0.0})
    # Future row must be excluded despite a very attractive return.
    rows.append({"security_id":"X", "event_time":"2026-04-01T00:00:00Z", "available_time":"2026-04-01T00:00:00Z", "return":1.0})
    result=HistoricalPatternEngine().find("X", rows, as_of="2026-03-20T00:00:00Z", window=10, horizon=5, top_k=5)
    assert result.eligible_matches > 0
    assert all(m.anchor_time < "2026-03-20T00:00:00Z" for m in result.matches)


def test_pattern_engine_requires_enough_history():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[]
    for i in range(10):
        ts=(start+timedelta(days=i)).strftime("%Y-%m-%dT00:00:00Z")
        rows.append({"event_time":ts, "available_time":ts, "return":0.01})
    result=HistoricalPatternEngine().find("X", rows, as_of="2026-01-10T00:00:00Z", window=5, horizon=5)
    assert result.pattern_score == 0.5
    assert "INSUFFICIENT_PATTERN_HISTORY" in result.warnings
