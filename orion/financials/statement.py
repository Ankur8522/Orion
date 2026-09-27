from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from ..data.time import parse_utc

@dataclass(frozen=True)
class FinancialFact:
    security_id: str
    metric: str
    period_end: str
    value: Decimal
    unit: str
    currency: str
    source_id: str
    available_time: str
    evidence_id: str

    def validate(self, decision_time: str | None = None):
        if not self.security_id or not self.metric or not self.evidence_id:
            raise ValueError('INVALID_FINANCIAL_FACT')
        parse_utc(self.available_time)
        if decision_time and parse_utc(self.available_time) > parse_utc(decision_time):
            raise ValueError('FUTURE_FINANCIAL_FACT')
        return True

class StatementMapper:
    DEFAULT_MAP = {
        'revenue': 'revenue', 'sales': 'revenue', 'total income': 'revenue',
        'ebitda': 'ebitda', 'operating profit': 'ebitda', 'pat': 'pat',
        'profit after tax': 'pat', 'net profit': 'pat', 'cfo': 'cfo',
        'cash from operations': 'cfo', 'receivables': 'receivables',
        'inventory': 'inventory', 'debt': 'debt', 'cash': 'cash',
    }
    def __init__(self, mapping=None):
        self.mapping = {**self.DEFAULT_MAP, **(mapping or {})}
    def map_row(self, row: dict) -> FinancialFact:
        label = str(row.get('label','')).strip().lower()
        metric = self.mapping.get(label)
        if not metric: raise ValueError('UNMAPPED_FINANCIAL_LABEL')
        required=('security_id','period_end','value','unit','currency','source_id','available_time','evidence_id')
        missing=[k for k in required if k not in row]
        if missing: raise ValueError('MISSING_FINANCIAL_FIELDS:'+','.join(missing))
        fact=FinancialFact(row['security_id'],metric,row['period_end'],Decimal(str(row['value'])),row['unit'],row['currency'],row['source_id'],row['available_time'],row['evidence_id'])
        fact.validate(); return fact
