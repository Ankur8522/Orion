from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class SourceRequest:
    security_id: str
    dataset: str
    as_of: str

@dataclass(frozen=True)
class SourcePayload:
    source_id: str
    dataset: str
    security_id: str
    event_time: str
    available_time: str
    raw: bytes
    content_type: str

class SourceAdapter(Protocol):
    source_id: str
    def fetch(self, request: SourceRequest) -> SourcePayload: ...
