from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Security:
    security_id: str
    exchange: str
    symbol: str
    name: str
    market_cap_cr: float | None
    active: bool = True
    sme: bool = False
    suspended: bool = False

class UniverseBuilder:
    def __init__(self, min_market_cap_cr: float = 3000): self.min_market_cap_cr=min_market_cap_cr
    def build(self, rows: Iterable[Security]):
        out=[]
        for r in rows:
            if not r.active or r.sme or r.suspended: continue
            if r.market_cap_cr is None or r.market_cap_cr < self.min_market_cap_cr: continue
            out.append(r)
        return sorted(out,key=lambda x:x.security_id)
