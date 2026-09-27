from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence
from types import MappingProxyType
import math
from ..data.world_snapshot import WorldSnapshot
from ..data.coverage_contract import CoverageAssessment
from ..research.evidence_graph import EvidenceGraph
from ..data.fabric import DatasetSnapshot

@dataclass(frozen=True)
class DecisionReadiness:
    status: str
    blockers: tuple[str,...]
    completeness: float
    lineage_hash: str

@dataclass(frozen=True)
class DecisionWorld:
    snapshot: WorldSnapshot
    coverage: CoverageAssessment
    evidence: EvidenceGraph
    readiness: DecisionReadiness
    lineage_hash: str
    datasets: tuple[DatasetSnapshot,...] = ()
    features: Mapping[str,float] = None

    def __post_init__(self):
        # Frozen dataclasses do not freeze nested dictionaries; seal the feature map.
        features = dict(self.features or {})
        for key, value in features.items():
            if not key or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError('INVALID_DECISION_FEATURE')
        object.__setattr__(self, 'features', MappingProxyType(features))

class DecisionWorldBuilder:
    """Single decision-time contract joining data, PIT, coverage and evidence."""
    def build(self, snapshot: WorldSnapshot, coverage: CoverageAssessment, evidence: EvidenceGraph, *, datasets: Sequence[DatasetSnapshot] = (), features: Mapping[str,float] | None = None) -> DecisionWorld:
        blockers=list(snapshot.blockers)+list(coverage.blockers)+list(evidence.blockers)
        status='READY' if not blockers and snapshot.usable and coverage.usable and evidence.usable else 'BLOCKED'
        payload={'snapshot':snapshot.lineage_hash,'coverage':coverage.lineage_hash,'evidence':evidence.lineage_hash,'datasets':[d.lineage_hash for d in datasets],'features':sorted((features or {}).keys()),'status':status,'blockers':sorted(set(blockers))}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return DecisionWorld(snapshot,coverage,evidence,DecisionReadiness(status,tuple(sorted(set(blockers))),coverage.completeness,lineage),lineage,tuple(datasets),dict(features or {}))
