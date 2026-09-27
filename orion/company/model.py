from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

D=Decimal

def _d(v): return D(str(v))

def _growth(cur, prev):
    if prev in (None, D('0')): return None
    return (cur-prev)/abs(prev)

@dataclass(frozen=True)
class CompanyPeriod:
    period_end: str
    revenue: D|None=None
    ebitda: D|None=None
    pat: D|None=None
    cfo: D|None=None
    capex: D|None=None
    debt: D|None=None
    cash: D|None=None
    receivables: D|None=None
    inventory: D|None=None
    equity: D|None=None
    invested_capital: D|None=None
    shares: D|None=None
    eps: D|None=None

@dataclass(frozen=True)
class CompanyModel:
    security_id: str
    periods: tuple[CompanyPeriod,...]
    derived: dict[str,dict[str,D|None]]
    warnings: tuple[str,...]


def build_company_model(security_id: str, periods: Sequence[CompanyPeriod]) -> CompanyModel:
    ps=tuple(sorted(periods,key=lambda x:x.period_end))
    out={}; warnings=[]
    prev=None
    for p in ps:
        m={}
        for name in ('revenue','ebitda','pat','cfo','capex','debt','cash','receivables','inventory','equity','invested_capital','shares','eps'):
            val=getattr(p,name)
            if val is not None: m[name]=_d(val)
        if p.revenue is not None and p.revenue != 0:
            if p.ebitda is not None: m['ebitda_margin']=_d(p.ebitda)/_d(p.revenue)
            if p.pat is not None: m['net_margin']=_d(p.pat)/_d(p.revenue)
            if p.receivables is not None: m['receivables_to_revenue']=_d(p.receivables)/_d(p.revenue)
            if p.inventory is not None: m['inventory_to_revenue']=_d(p.inventory)/_d(p.revenue)
        if p.pat is not None and p.cfo is not None and p.pat != 0: m['cfo_pat']=_d(p.cfo)/_d(p.pat)
        if p.debt is not None and p.ebitda is not None and p.ebitda != 0: m['debt_ebitda']=_d(p.debt)/_d(p.ebitda)
        if p.debt is not None and p.cash is not None: m['net_debt']=_d(p.debt)-_d(p.cash)
        if p.cfo is not None and p.capex is not None: m['fcf']=_d(p.cfo)-_d(p.capex)
        if p.pat is not None and p.equity is not None and p.equity != 0: m['roe']=_d(p.pat)/_d(p.equity)
        if p.ebitda is not None and p.invested_capital is not None and p.invested_capital != 0:
            m['roic_proxy']=_d(p.ebitda)/_d(p.invested_capital)
        if prev is not None:
            for base in ('revenue','ebitda','pat','cfo','capex','debt','cash','receivables','inventory','fcf'):
                if base in m and hasattr(prev,base) and getattr(prev,base) is not None:
                    g=_growth(m[base],_d(getattr(prev,base)))
                    if g is not None: m[base+'_growth']=g
        out[p.period_end]=m
        prev=p
    if len(ps)<2: warnings.append('HISTORICAL_COMPARISON_LIMITED')
    if any('cfo_pat' in x and x['cfo_pat'] < D('0') for x in out.values()): warnings.append('NEGATIVE_CFO_TO_PAT')
    return CompanyModel(security_id,ps,out,tuple(sorted(set(warnings))))
