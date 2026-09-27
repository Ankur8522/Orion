from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping

TARGETS = {"NIFTY50": 50, "NIFTY_MIDCAP150": 150, "NIFTY_SMALLCAP250": 250}

@dataclass(frozen=True)
class UniverseMembership:
    security_id: str
    index: str
    active: bool = True
    effective_from: str | None = None
    effective_to: str | None = None
    available_time: str | None = None

@dataclass(frozen=True)
class UniverseCoverage:
    target_counts: Mapping[str, int]
    supplied_counts: Mapping[str, int]
    unique_securities: int
    duplicate_memberships: int
    missing_memberships: Mapping[str, int]
    coverage_pct: float
    status: str
    lineage_hash: str

    @property
    def target_size(self) -> int:
        return sum(self.target_counts.values())

class InstitutionalUniverseContract:
    """Truth-bound universe contract with optional historical/PIT membership semantics."""
    def __init__(self, targets: Mapping[str, int] | None = None):
        self.targets = dict(targets or TARGETS)
        if any(int(v) <= 0 for v in self.targets.values()):
            raise ValueError("INVALID_UNIVERSE_TARGET")

    @staticmethod
    def _effective(membership: UniverseMembership, as_of: str | None) -> bool:
        if as_of is None:
            return True
        from .time import parse_utc
        point = parse_utc(as_of)
        if membership.available_time is not None and parse_utc(membership.available_time) > point:
            return False
        if membership.effective_from is not None and parse_utc(membership.effective_from) > point:
            return False
        if membership.effective_to is not None and parse_utc(membership.effective_to) <= point:
            return False
        return True

    @property
    def target_size(self) -> int:
        return sum(self.targets.values())

    def membership_as_of(self, memberships: Iterable[UniverseMembership], as_of: str) -> tuple[UniverseMembership, ...]:
        return tuple(m for m in memberships if m.active and self._effective(m, as_of))

    def coverage(self, memberships: Iterable[UniverseMembership], *, as_of: str | None = None) -> UniverseCoverage:
        rows = self.membership_as_of(memberships, as_of) if as_of is not None else tuple(m for m in memberships if m.active)
        seen: set[tuple[str, str]] = set()
        dup = 0
        supplied = {k: 0 for k in self.targets}
        securities: set[str] = set()
        for row in rows:
            if row.index not in self.targets or not row.security_id:
                continue
            key = (row.index, row.security_id)
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            supplied[row.index] += 1
            securities.add(row.security_id)
        missing = {k: max(0, self.targets[k] - supplied.get(k, 0)) for k in self.targets}
        matched = sum(min(self.targets[k], supplied.get(k, 0)) for k in self.targets)
        coverage = round(matched / self.target_size * 100.0, 4) if self.target_size else 0.0
        status = "READY" if not any(missing.values()) else ("PARTIAL" if matched else "BLOCKED")
        payload = {"targets": self.targets, "supplied": supplied, "unique": len(securities), "duplicates": dup, "missing": missing, "as_of": as_of}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return UniverseCoverage(self.targets, supplied, len(securities), dup, missing, coverage, status, lineage)
