from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
D=Decimal
@dataclass(frozen=True)
class ValuationSnapshot:
    security_id:str
    price:D|None
    market_cap:D|None
    pe:D|None
    pb:D|None
    ev_ebitda:D|None
    earnings_yield:D|None
    fcf_yield:D|None
    net_debt_ebitda:D|None
    warnings:tuple[str,...]

def derive_valuation(security_id:str, *, price=None, market_cap=None, shares=None, pat=None, equity=None, enterprise_value=None, ebitda=None, fcf=None, debt=None, cash=None):
    vals={k:(None if v is None else D(str(v))) for k,v in locals().items() if k not in ('security_id',)}
    p,mc,sh,pa,eq,ev,eb,fcf,db,ca=[vals[x] for x in ('price','market_cap','shares','pat','equity','enterprise_value','ebitda','fcf','debt','cash')]
    if mc is None and p is not None and sh is not None: mc=p*sh
    if ev is None and mc is not None and db is not None and ca is not None: ev=mc+db-ca
    pe=mc/pa if mc is not None and pa not in (None,D('0')) else None
    pb=mc/eq if mc is not None and eq not in (None,D('0')) else None
    ev_ebitda=ev/eb if ev is not None and eb not in (None,D('0')) else None
    ey=pa/mc if mc is not None and mc != 0 else None
    fy=fcf/mc if mc is not None and mc != 0 else None
    nde=(db-ca)/eb if db is not None and ca is not None and eb not in (None,D('0')) else None
    warnings=[]
    if pa is not None and pa < 0: warnings.append('NEGATIVE_EARNINGS')
    if fcf is not None and fcf < 0: warnings.append('NEGATIVE_FCF')
    return ValuationSnapshot(security_id,p,mc,pe,pb,ev_ebitda,ey,fy,nde,tuple(warnings))
