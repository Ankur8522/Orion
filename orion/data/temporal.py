from __future__ import annotations
from dataclasses import dataclass
from .time import parse_utc

@dataclass(frozen=True)
class TemporalLineage:
    """Canonical timestamp boundary for point-in-time data.

    source_time: timestamp assigned by the source (publication/observation time).
    effective_time: when the fact economically becomes effective.
    available_time: when ORION could legitimately consume the fact.
    ingestion_time: when ORION persisted the fact.
    """
    source_time: str
    effective_time: str
    available_time: str
    ingestion_time: str

    def validate(self) -> bool:
        source = parse_utc(self.source_time)
        effective = parse_utc(self.effective_time)
        available = parse_utc(self.available_time)
        ingestion = parse_utc(self.ingestion_time)
        if available < source:
            raise ValueError('AVAILABILITY_BEFORE_SOURCE_TIME')
        if ingestion < available:
            raise ValueError('INGESTION_BEFORE_AVAILABLE_TIME')
        return True

    def usable_as_of(self, decision_time: str) -> bool:
        self.validate()
        return parse_utc(self.available_time) <= parse_utc(decision_time)

    def as_dict(self):
        return {
            'source_time': self.source_time,
            'effective_time': self.effective_time,
            'available_time': self.available_time,
            'ingestion_time': self.ingestion_time,
        }
