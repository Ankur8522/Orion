from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from .time import parse_utc

@dataclass(frozen=True)
class Freshness:
    status: str
    age_hours: float
    source_id: str

def assess(available_time, now_time, source_id, warn_hours=168, block_hours=720):
    a=parse_utc(available_time); n=parse_utc(now_time)
    age=(n-a).total_seconds()/3600
    if age < 0: raise ValueError('FUTURE_DATA')
    status='FRESH' if age <= warn_hours else ('STALE' if age <= block_hours else 'EXPIRED')
    return Freshness(status,age,source_id)
