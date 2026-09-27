from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
@dataclass(frozen=True)
class ForensicFinding:
    code:str; severity:str; message:str; evidence_metrics:tuple[str,...]
class ForensicEngine:
    def __init__(self,cfo_pat_min='0.70',receivables_revenue_max='0.25',debt_ebitda_max='4'):
        self.cfo_pat_min=Decimal(str(cfo_pat_min)); self.receivables_revenue_max=Decimal(str(receivables_revenue_max)); self.debt_ebitda_max=Decimal(str(debt_ebitda_max))
    def inspect(self,facts):
        f={k:Decimal(str(v)) for k,v in facts.items()}; out=[]
        if 'cfo_pat' in f and f['cfo_pat']<self.cfo_pat_min: out.append(ForensicFinding('LOW_CFO_PAT','HIGH','Operating cash flow is materially below reported PAT.',('cfo','pat')))
        if 'receivables_to_revenue' in f and f['receivables_to_revenue']>self.receivables_revenue_max: out.append(ForensicFinding('RECEIVABLE_INTENSITY','MEDIUM','Receivables are elevated relative to revenue.',('receivables','revenue')))
        if 'debt_ebitda' in f and f['debt_ebitda']>self.debt_ebitda_max: out.append(ForensicFinding('HIGH_LEVERAGE','HIGH','Debt/EBITDA exceeds the configured forensic threshold.',('debt','ebitda')))
        if 'inventory' in f and 'revenue' in f and f['revenue'] and f['inventory']/f['revenue']>Decimal('0.30'): out.append(ForensicFinding('INVENTORY_INTENSITY','MEDIUM','Inventory is elevated relative to revenue.',('inventory','revenue')))
        return tuple(out)
