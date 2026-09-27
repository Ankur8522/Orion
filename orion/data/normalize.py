from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class FinancialObservation:
    security_id:str; metric:str; period_end:str; value:Decimal; unit:str; currency:str; source_id:str; available_time:str

class FinancialNormalizer:
    ALLOWED_UNITS={'INR','USD','PERCENT','COUNT'}
    def normalize(self, row:dict):
        required=('security_id','metric','period_end','value','unit','currency','source_id','available_time')
        missing=[x for x in required if x not in row]
        if missing: raise ValueError('MISSING_FIELDS:'+','.join(missing))
        if row['unit'] not in self.ALLOWED_UNITS: raise ValueError('UNSUPPORTED_UNIT')
        value=Decimal(str(row['value']))
        return FinancialObservation(row['security_id'],row['metric'],row['period_end'],value,row['unit'],row['currency'],row['source_id'],row['available_time'])
