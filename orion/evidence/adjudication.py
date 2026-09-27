from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence
from .ledger import EvidenceRecord

@dataclass(frozen=True)
class ClaimAdjudication:
    claim_key: str
    status: str
    supporting_ids: tuple[str, ...]
    contradicting_ids: tuple[str, ...]
    confidence: float
    lineage_hash: str

class EvidenceAdjudicator:
    """Deterministically classifies same-key evidence without inventing a winner.

    Evidence is grouped by (security, claim). A contradiction is explicit whenever
    extracted values disagree. When values are absent, records remain UNRESOLVED.
    """
    @staticmethod
    def _value_key(value: object) -> str:
        return json.dumps(value, sort_keys=True, default=str, separators=(',', ':'))

    def adjudicate(self, records: Sequence[EvidenceRecord], *, decision_time: str | None = None) -> tuple[ClaimAdjudication, ...]:
        groups: dict[str, list[EvidenceRecord]] = {}
        for r in records:
            r.validate(decision_time)
            key=f"{r.security_id or ''}|{r.claim.strip()}"
            groups.setdefault(key, []).append(r)
        out=[]
        for key, rows in sorted(groups.items()):
            values={self._value_key(r.extracted_value) for r in rows if r.extracted_value is not None}
            if len(values) > 1:
                status='CONTRADICTED'
                confidence=round(max(r.confidence for r in rows), 8)
                supporting=tuple(r.evidence_id for r in rows if r.extracted_value is not None)
                contradicting=supporting
            elif not values:
                status='UNRESOLVED'
                confidence=round(max(r.confidence for r in rows), 8)
                supporting=tuple(r.evidence_id for r in rows)
                contradicting=()
            else:
                status='SUPPORTED'
                confidence=round(sum(r.confidence for r in rows)/len(rows), 8)
                supporting=tuple(r.evidence_id for r in rows)
                contradicting=()
            payload={'claim_key':key,'status':status,'supporting':supporting,'contradicting':contradicting,'confidence':confidence}
            lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            out.append(ClaimAdjudication(key,status,supporting,contradicting,confidence,lineage))
        return tuple(out)
