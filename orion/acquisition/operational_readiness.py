from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OperationalReadiness:
    provider: str
    as_of: str
    requested: int
    mapped: int
    covered: int
    ready: int
    stale_or_missing: int
    blocked: int
    status: str
    rows: tuple[dict, ...]


def build_operational_readiness(*, security_ids: Iterable[str], mapping_registry, store,
                                provider: str, as_of: str, provider_authenticated: bool,
                                dataset: str = "ohlcv") -> OperationalReadiness:
    """Combine provider auth, PIT-safe mapping, and observed corpus coverage.

    This is a status projection only: it never invents mappings or observations.
    A security is READY only when the provider is authenticated, a verified PIT
    mapping resolves at ``as_of``, and at least one PIT-valid observation exists.
    """
    ids = tuple(dict.fromkeys(str(x).strip() for x in security_ids if str(x).strip()))
    coverage = store.acquisition_coverage(ids, dataset=dataset, decision_time=as_of) if ids else {
        'covered': 0, 'missing': []
    }
    covered_ids = set(ids) - set(coverage.get('missing', []))
    rows = []
    counts = {k: 0 for k in ('MAPPED', 'READY', 'STALE_OR_MISSING', 'BLOCKED')}
    for sid in ids:
        mapping = mapping_registry.resolve(sid, provider=provider, as_of=as_of)
        if not provider_authenticated:
            status, reason = 'BLOCKED', 'PROVIDER_NOT_AUTHENTICATED'
        elif mapping is None:
            status, reason = 'BLOCKED', 'NO_VERIFIED_INSTRUMENT_MAPPING'
        elif sid not in covered_ids:
            status, reason = 'STALE_OR_MISSING', 'NO_PIT_VALID_OBSERVATION'
        else:
            status, reason = 'READY', None
        counts[status] += 1
        rows.append({'security_id': sid, 'status': status, 'reason': reason,
                     'provider': provider, 'instrument_key': mapping.instrument_key if mapping else None,
                     'mapping_source_id': mapping.source_id if mapping else None,
                     'latest_available': None})
    total = len(ids)
    if not total:
        overall = 'NO_REQUESTS'
    elif counts['READY'] == total:
        overall = 'READY'
    elif counts['READY'] or counts['STALE_OR_MISSING']:
        overall = 'PARTIAL'
    else:
        overall = 'BLOCKED'
    return OperationalReadiness(provider, as_of, total, counts['MAPPED'] + counts['READY'] + counts['STALE_OR_MISSING'],
                                len(covered_ids), counts['READY'], counts['STALE_OR_MISSING'], counts['BLOCKED'],
                                overall, tuple(rows))
