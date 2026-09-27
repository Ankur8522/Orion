from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from .statement import FinancialFact

@dataclass(frozen=True)
class FactReconciliation:
    security_id: str
    metric: str
    period_end: str
    facts: tuple[FinancialFact,...]
    status: str
    selected: FinancialFact|None
    spread: Decimal|None
    relative_spread: Decimal|None

class FinancialFactReconciler:
    def __init__(self, relative_tolerance: Decimal=Decimal('0.01'), absolute_tolerance: Decimal=Decimal('0.01'), source_precedence: Sequence[str] = ()):
        self.relative_tolerance=relative_tolerance; self.absolute_tolerance=absolute_tolerance; self.source_precedence=tuple(source_precedence)

    def _rank(self, source_id: str) -> tuple[int, str]:
        try: return (self.source_precedence.index(source_id), source_id)
        except ValueError: return (len(self.source_precedence), source_id)
    def reconcile(self, facts: Sequence[FinancialFact]) -> FactReconciliation:
        if not facts: raise ValueError('NO_FINANCIAL_FACTS')
        keys={(f.security_id,f.metric,f.period_end,f.unit,f.currency) for f in facts}
        if len(keys)!=1: raise ValueError('MIXED_FINANCIAL_FACT_KEYS')
        ordered=tuple(sorted(facts,key=lambda x:(x.source_id,x.available_time,x.evidence_id)))
        vals=[f.value for f in ordered]; lo=min(vals); hi=max(vals); spread=hi-lo
        denom=max(abs(hi),abs(lo),Decimal('1'))
        rel=spread/denom
        if spread <= self.absolute_tolerance or rel <= self.relative_tolerance:
            # Deterministic selection: highest evidence source confidence is not available on fact;
            # preserve all facts and select earliest source lexicographically only after agreement.
            selected=min(ordered, key=lambda f: self._rank(f.source_id))
            status='AGREED'
        else:
            selected=None; status='REVIEW'
        s,m,p,_,_=next(iter(keys))
        return FactReconciliation(s,m,p,ordered,status,selected,spread,rel)
