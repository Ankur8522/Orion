from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Iterable
from .statement import FinancialFact, StatementMapper

@dataclass(frozen=True)
class ExtractedFact:
    fact: FinancialFact
    label: str
    raw_value: str
    locator: str
    confidence: float

class FinancialFactExtractor:
    """Deterministic text/row extractor; never invents missing facts."""
    DEFAULT_PATTERNS = {
        'revenue': r'(?:revenue|sales|total\s+income)\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'ebitda': r'(?:ebitda|operating\s+profit)\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'pat': r'(?:profit\s+after\s+tax|net\s+profit|pat)\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'cfo': r'(?:cash\s+from\s+operations|cash\s+flow\s+from\s+operating|cfo)\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'receivables': r'(?:trade\s+)?receivables\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'inventory': r'inventory\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'debt': r'(?:total\s+)?debt\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
        'cash': r'(?:cash\s+and\s+cash\s+equivalents|cash)\s*(?:[:\-]|is)?\s*(?:rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
    }
    def __init__(self, mapper: StatementMapper|None=None, patterns=None):
        self.mapper=mapper or StatementMapper()
        self.patterns={**self.DEFAULT_PATTERNS, **(patterns or {})}
    def extract_rows(self, rows: Iterable[dict]) -> list[ExtractedFact]:
        out=[]
        for i,row in enumerate(rows):
            fact=self.mapper.map_row(row)
            out.append(ExtractedFact(fact,str(row.get('label','')),str(row['value']),str(row.get('locator',f'row:{i}')),float(row.get('confidence',1.0))))
        return out
    def extract_text(self, text:str, *, security_id:str, period_end:str, unit='INR', currency='INR', source_id:str, available_time:str, evidence_id_factory):
        out=[]
        for metric, pattern in self.patterns.items():
            for m in re.finditer(pattern,text,re.I):
                raw=m.group(1).replace(',','')
                try: value=Decimal(raw)
                except InvalidOperation: continue
                start=max(0,m.start()-80); end=min(len(text),m.end()+80)
                locator=f'char:{m.start()}-{m.end()-1}'
                eid=evidence_id_factory(locator,metric, text[start:end])
                fact=FinancialFact(security_id,metric,period_end,value,unit,currency,source_id,available_time,eid)
                fact.validate()
                out.append(ExtractedFact(fact,metric,raw,locator,0.75))
        return out
