from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class ResearchScenario:
    name: str
    probability: float
    impact: float
    drivers: tuple[str, ...]
    invalidators: tuple[str, ...]

@dataclass(frozen=True)
class ScenarioSet:
    base: ResearchScenario
    bull: ResearchScenario
    bear: ResearchScenario
    counter_thesis: tuple[str, ...]
    causal_chains: tuple[tuple[str, ...], ...]
    research_ready: bool
    blockers: tuple[str, ...]
    lineage_hash: str

class ResearchScenarioEngine:
    """Builds explicit, bounded scenarios from supplied evidence only."""
    def build(self, *, catalysts=(), headwinds=(), evidence_ids=(), counter_thesis=(), base_impact=0.0,
              bull_impact=0.0, bear_impact=0.0, probabilities=(0.5,0.25,0.25), causal_chains=()):
        if len(probabilities)!=3 or any(float(p)<0 for p in probabilities) or abs(sum(map(float,probabilities))-1)>1e-9:
            raise ValueError('INVALID_SCENARIO_PROBABILITIES')
        if not evidence_ids: raise ValueError('SCENARIO_REQUIRES_EVIDENCE')
        c=tuple(dict.fromkeys(str(x) for x in catalysts if x)); h=tuple(dict.fromkeys(str(x) for x in headwinds if x)); ct=tuple(dict.fromkeys(str(x) for x in counter_thesis if x))
        chains=tuple(tuple(str(x) for x in chain if x) for chain in causal_chains if chain)
        blockers=[]
        if not ct: blockers.append('MISSING_COUNTER_THESIS')
        if not chains: blockers.append('MISSING_CAUSAL_CHAIN')
        if not c: blockers.append('MISSING_CATALYSTS')
        if not h: blockers.append('MISSING_HEADWINDS')
        p=list(map(float,probabilities))
        def s(name,prob,impact,drivers,invalidators): return ResearchScenario(name,prob,float(impact),tuple(drivers),tuple(invalidators))
        base=s('BASE',p[0],base_impact,c,h); bull=s('BULL',p[1],bull_impact,c,ct); bear=s('BEAR',p[2],bear_impact,h,ct)
        payload={'base':base.__dict__,'bull':bull.__dict__,'bear':bear.__dict__,'counter_thesis':ct,'causal_chains':chains,'evidence_ids':tuple(sorted(set(evidence_ids))),'blockers':blockers}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return ScenarioSet(base,bull,bear,ct,chains,not blockers,tuple(blockers),lineage)
