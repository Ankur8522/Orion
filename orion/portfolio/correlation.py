from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math

@dataclass(frozen=True)
class CorrelationMatrix:
    securities: tuple[str,...]
    matrix: tuple[tuple[float,...],...]
    average_pairwise: float
    high_correlation_pairs: tuple[tuple[str,str,float],...]
    lineage_hash: str

class CorrelationEngine:
    def calculate(self, returns: dict[str, list[float]], threshold: float=0.70) -> CorrelationMatrix:
        ids=tuple(sorted(returns));
        if len(ids)<2: raise ValueError('CORRELATION_REQUIRES_TWO_SECURITIES')
        n=min(len(returns[i]) for i in ids)
        if n<2: raise ValueError('CORRELATION_REQUIRES_TWO_OBSERVATIONS')
        xs={i:[float(v) for v in returns[i][-n:]] for i in ids}
        def corr(a,b):
            ma=sum(a)/n; mb=sum(b)/n; da=sum((x-ma)**2 for x in a); db=sum((y-mb)**2 for y in b)
            if da==0 or db==0: return 0.0
            return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(da*db)**0.5
        m=[]; pairs=[]
        for i in ids:
            row=[]
            for j in ids:
                v=1.0 if i==j else corr(xs[i],xs[j]); row.append(round(v,8))
                if i<j and abs(v)>=threshold: pairs.append((i,j,round(v,8)))
            m.append(tuple(row))
        vals=[m[i][j] for i in range(len(ids)) for j in range(i+1,len(ids))]
        avg=sum(vals)/len(vals) if vals else 0.0
        payload={'securities':ids,'matrix':m,'threshold':threshold}
        return CorrelationMatrix(ids,tuple(m),round(avg,8),tuple(sorted(pairs)),sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest())
