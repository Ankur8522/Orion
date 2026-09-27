from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from ..data.time import parse_utc

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    security_id: str | None
    source_id: str
    document_id: str
    locator: str
    claim: str
    extracted_value: object | None
    confidence: float
    available_time: str
    content_hash: str

    def validate(self, decision_time: str | None = None) -> None:
        if not self.evidence_id or not self.source_id or not self.document_id:
            raise ValueError('INVALID_EVIDENCE_IDENTITY')
        if not 0 <= self.confidence <= 1:
            raise ValueError('INVALID_CONFIDENCE')
        parse_utc(self.available_time)
        if len(self.content_hash) != 64 or any(c not in '0123456789abcdef' for c in self.content_hash.lower()):
            raise ValueError('INVALID_CONTENT_HASH')
        if decision_time is not None and parse_utc(self.available_time) > parse_utc(decision_time):
            raise ValueError('FUTURE_EVIDENCE')

    @staticmethod
    def id_for(document_id: str, locator: str, claim: str, content_hash: str) -> str:
        raw = f'{document_id}|{locator}|{claim}|{content_hash}'.encode()
        return sha256(raw).hexdigest()
