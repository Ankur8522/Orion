from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class Cluster:
    members: tuple[str,...]
    weight: float
    average_correlation: float

@dataclass(frozen=True)
class StressReport:
    hhi: float
    clusters: tuple[Cluster,...]
    stressed_loss: float
    stressed_gain: float
    fragility: float
    capital_efficiency: float
    actions: tuple[str,...]
    lineage_hash: str

class PortfolioStressEngine:
    """Uses supplied returns/correlations only; no correlation is inferred from absent data."""
    def analyze(self, weights: Mapping[str,float], *, correlations: Mapping[tuple[str,str],float] | None=None,
                shocks: Mapping[str,float] | None=None, gross_exposure: float|None=None) -> StressReport:
        if not weights or any(float(w)<0 for w in weights.values()): raise ValueError('INVALID_WEIGHTS')
        total=sum(float(w) for w in weights.values()); norm={k:float(v)/total for k,v in weights.items()}
        hhi=sum(v*v for v in norm.values()); corr=correlations or {}; clusters=[]; used=set()
        for sid in sorted(norm):
            if sid in used: continue
            members=[sid]
            for other in sorted(norm):
                if other==sid or other in used: continue
                c=float(corr.get((sid,other),corr.get((other,sid),0.0)))
                if c>=.70: members.append(other)
            used.update(members)
            pairs=[]
            for i,a in enumerate(members):
                for b in members[i+1:]: pairs.append(float(corr.get((a,b),corr.get((b,a),0.0))))
            clusters.append(Cluster(tuple(members),round(sum(norm[x] for x in members),8),round(sum(pairs)/len(pairs),8) if pairs else 0.0))
        sh=shocks or {}; stressed=sum(norm.get(k,0)*float(v) for k,v in sh.items())
        gain=max(stressed,0.0); loss=min(stressed,0.0)
        corr_pen=max((c.average_correlation-.70)/.30 for c in clusters if len(c.members)>1) if clusters else 0
        fragility=min(1,max(0,.45*min(hhi/.30,1)+.35*min(max(corr_pen,0),1)+.20*min(abs(loss)/.20,1)))
        gross=1.0 if gross_exposure is None else max(float(gross_exposure),0.0)
        efficiency=min(1.0,1.0/(1.0+fragility*max(gross,1.0)))
        actions=[]
        if hhi>.25: actions.append('REDUCE_HHI')
        if any(len(c.members)>1 and c.average_correlation>=.70 for c in clusters): actions.append('REVIEW_CORRELATED_CLUSTERS')
        if loss < -.05: actions.append('RUN_DOWNSIDE_STRESS_REVIEW')
        if not actions: actions.append('MONITOR_CLUSTER_AND_STRESS_STATE')
        payload={'weights':norm,'correlations':{f'{a}|{b}':v for (a,b),v in sorted(corr.items(), key=lambda x:str(x[0]))},'shocks':sh,'gross_exposure':gross}
        h=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return StressReport(round(hhi,8),tuple(clusters),round(loss,8),round(gain,8),round(fragility,8),round(efficiency,8),tuple(actions),h)
