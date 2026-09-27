from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Edge:
    source: str
    relation: str
    target: str
    weight: float = 1.0

class WorldModel:
    def __init__(self): self._edges=[]
    def add(self, source, relation, target, weight=1.0):
        if not source or not relation or not target: raise ValueError('INVALID_EDGE')
        if not 0 <= weight <= 1: raise ValueError('INVALID_WEIGHT')
        edge=Edge(source,relation,target,float(weight))
        if edge not in self._edges: self._edges.append(edge)
        return edge
    def related(self, node, depth=1):
        if depth<1: return ()
        frontier={node}; seen=set(); out=[]
        for _ in range(depth):
            nxt=set()
            for e in self._edges:
                if e.source in frontier and e.target not in seen:
                    out.append(e); nxt.add(e.target)
            seen |= frontier; frontier=nxt
        return tuple(out)
    def shock_path(self, source, max_depth=3): return self.related(source,max_depth)
