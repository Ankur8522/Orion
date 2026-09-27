from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
@dataclass(frozen=True)
class CausalScenario:
    name:str; assumptions:tuple[str,...]; effects:tuple[str,...]; vulnerabilities:tuple[str,...]
class CausalEngine:
    def build(self, trigger, direct=(), second_order=(), competitive=(), capital=(), portfolio=()):
        return {'trigger':trigger,'direct_effects':tuple(direct),'second_order_effects':tuple(second_order),'competitive_response':tuple(competitive),'capital_response':tuple(capital),'portfolio_effects':tuple(portfolio)}
    def counterfactuals(self, *, growth_shock=0.0, margin_shock=0.0, multiple_shock=0.0, catalyst_removed=False):
        if any(abs(float(x))>1 for x in (growth_shock,margin_shock,multiple_shock)): raise ValueError('SHOCK_OUT_OF_RANGE')
        effects=[]
        if growth_shock: effects.append(f'GROWTH_SHOCK:{float(growth_shock):.4f}')
        if margin_shock: effects.append(f'MARGIN_SHOCK:{float(margin_shock):.4f}')
        if multiple_shock: effects.append(f'MULTIPLE_SHOCK:{float(multiple_shock):.4f}')
        if catalyst_removed: effects.append('CATALYST_REMOVED')
        return tuple(effects)
