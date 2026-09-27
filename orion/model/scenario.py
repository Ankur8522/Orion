from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from math import sqrt

@dataclass(frozen=True)
class Shock:
    node: str
    magnitude: float
    confidence: float = 1.0

@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    probability: float
    shocks: tuple[Shock, ...]
    horizon_days: int
    rationale: str = ""

@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    impacts: tuple[tuple[str, float], ...]
    expected_impact: float
    downside_tail: float
    upside_tail: float
    dispersion: float
    lineage_hash: str

class ScenarioEngine:
    """Deterministic counterfactual propagation over an evidence-defined WorldModel.

    It deliberately does not manufacture market probabilities. Scenario probabilities and
    shock magnitudes must be supplied by the caller and remain part of the lineage.
    """
    def __init__(self, world_model):
        self.world = world_model

    def _propagate(self, shocks, depth):
        scores = {}
        for shock in shocks:
            scores[shock.node] = scores.get(shock.node, 0.0) + shock.magnitude * shock.confidence
            frontier = {shock.node: shock.magnitude * shock.confidence}
            seen = {shock.node}
            for _ in range(depth):
                nxt = {}
                for edge in self.world._edges:
                    if edge.source in frontier and edge.target not in seen:
                        propagated = frontier[edge.source] * edge.weight
                        scores[edge.target] = scores.get(edge.target, 0.0) + propagated
                        nxt[edge.target] = nxt.get(edge.target, 0.0) + propagated
                seen |= set(nxt)
                frontier = nxt
        return tuple(sorted((k, round(v, 12)) for k, v in scores.items()))

    def run(self, scenarios, depth=3):
        scenarios = tuple(scenarios)
        if not scenarios: raise ValueError("NO_SCENARIOS")
        if depth < 1: raise ValueError("INVALID_DEPTH")
        total = sum(float(s.probability) for s in scenarios)
        if abs(total - 1.0) > 1e-9: raise ValueError("SCENARIO_PROBABILITIES_MUST_SUM_TO_ONE")
        for s in scenarios:
            if not s.scenario_id or not s.name or not 0 <= s.probability <= 1 or s.horizon_days <= 0:
                raise ValueError("INVALID_SCENARIO")
            for sh in s.shocks:
                if not sh.node or not 0 <= sh.confidence <= 1:
                    raise ValueError("INVALID_SHOCK")
        rows=[]
        for s in scenarios:
            impacts=self._propagate(s.shocks, depth)
            total_impact=sum(v for _,v in impacts)
            rows.append((s, impacts, total_impact))
        expected=sum(s.probability * impact for s,_,impact in rows)
        negatives=sorted([impact for s,_,impact in rows if impact < 0])
        positives=sorted([impact for s,_,impact in rows if impact > 0], reverse=True)
        downside=sum(s.probability * impact for s,_,impact in rows if impact < 0)
        upside=sum(s.probability * impact for s,_,impact in rows if impact > 0)
        variance=sum(s.probability * (impact-expected)**2 for s,_,impact in rows)
        payload={"scenarios":[{"id":s.scenario_id,"p":s.probability,"h":s.horizon_days,"shocks":[sh.__dict__ for sh in s.shocks]} for s,_,_ in rows],"depth":depth,"expected":round(expected,12)}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
        return tuple(ScenarioResult(s.scenario_id, impacts, round(s.probability*total_impact,12), round(downside,12), round(upside,12), round(sqrt(max(variance,0)),12), lineage) for s,impacts,total_impact in rows)
