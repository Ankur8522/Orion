from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping
from .model import CompanyModel
from .valuation import ValuationSnapshot
from ..research.forensics import ForensicFinding

@dataclass(frozen=True)
class ResearchSnapshot:
    security_id:str
    as_of:str
    latest:dict[str,Decimal]
    growth:dict[str,Decimal]
    quality_flags:tuple[str,...]
    forensic_findings:tuple[ForensicFinding,...]
    valuation:ValuationSnapshot|None
    warnings:tuple[str,...]

def build_research_snapshot(model:CompanyModel, *, valuation=None, forensic_findings=()):
    if not model.periods: raise ValueError('NO_COMPANY_PERIODS')
    latest=model.derived[model.periods[-1].period_end]
    growth={k:v for k,v in latest.items() if k.endswith('_growth') and v is not None}
    flags=[]
    if latest.get('cfo_pat') is not None and latest['cfo_pat'] < Decimal('0.70'): flags.append('CASH_CONVERSION_WEAK')
    if latest.get('debt_ebitda') is not None and latest['debt_ebitda'] > Decimal('4'): flags.append('LEVERAGE_ELEVATED')
    if latest.get('fcf') is not None and latest['fcf'] < 0: flags.append('FCF_NEGATIVE')
    if latest.get('receivables_to_revenue') is not None and latest['receivables_to_revenue'] > Decimal('0.25'): flags.append('RECEIVABLE_INTENSITY_HIGH')
    return ResearchSnapshot(model.security_id,model.periods[-1].period_end,dict(latest),growth,tuple(sorted(set(flags))),tuple(forensic_findings),valuation,model.warnings)
