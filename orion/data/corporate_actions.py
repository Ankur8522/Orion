from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
from ..data.time import parse_utc

@dataclass(frozen=True)
class CorporateAction:
    security_id: str
    action_id: str
    action_type: str
    effective_time: str
    available_time: str
    ratio: Decimal = Decimal('1')
    cash_amount: Decimal = Decimal('0')
    source_id: str = ''
    content_hash: str = ''
    source_time: str | None = None
    ingestion_time: str | None = None

class CorporateActionLedger:
    """PIT-safe corporate-action normalization. It never invents adjustments."""
    VALID={'SPLIT','BONUS','RIGHTS','DIVIDEND','BUYBACK','MERGER','DEMERGER'}
    def normalize(self, row: dict) -> CorporateAction:
        required=('security_id','action_id','action_type','effective_time','available_time','source_id','content_hash')
        missing=[x for x in required if not row.get(x)]
        if missing: raise ValueError('MISSING_CORPORATE_ACTION_FIELDS:'+','.join(missing))
        typ=str(row['action_type']).upper()
        if typ not in self.VALID: raise ValueError('UNSUPPORTED_CORPORATE_ACTION')
        eff=parse_utc(row['effective_time']); avail=parse_utc(row['available_time'])
        source=parse_utc(row.get('source_time', row['available_time']))
        ingestion=parse_utc(row.get('ingestion_time', row['available_time']))
        if avail < eff: raise ValueError('CORPORATE_ACTION_AVAILABLE_BEFORE_EFFECTIVE')
        if avail < source: raise ValueError('CORPORATE_ACTION_AVAILABLE_BEFORE_SOURCE_TIME')
        if ingestion < avail: raise ValueError('CORPORATE_ACTION_INGESTION_BEFORE_AVAILABLE')
        if len(row['content_hash'])!=64 or any(c not in '0123456789abcdefABCDEF' for c in row['content_hash']): raise ValueError('INVALID_CORPORATE_ACTION_HASH')
        ratio=Decimal(str(row.get('ratio','1'))); cash=Decimal(str(row.get('cash_amount','0')))
        if ratio<=0: raise ValueError('INVALID_CORPORATE_ACTION_RATIO')
        return CorporateAction(str(row['security_id']),str(row['action_id']),typ,row['effective_time'],row['available_time'],ratio,cash,str(row['source_id']),row['content_hash'].lower(),row.get('source_time'),row.get('ingestion_time'))
    def as_of(self, actions, decision_time: str):
        d=parse_utc(decision_time); rows=[]
        for a in actions:
            if parse_utc(a.available_time)<=d and parse_utc(a.effective_time)<=d: rows.append(a)
        return tuple(sorted(rows,key=lambda x:(parse_utc(x.effective_time),x.action_id)))
    def adjustment_factor(self, actions, decision_time: str) -> Decimal:
        factor=Decimal('1')
        for a in self.as_of(actions,decision_time):
            if a.action_type in {'SPLIT','BONUS','RIGHTS'}: factor*=a.ratio
        return factor
    @staticmethod
    def lineage(actions, decision_time: str) -> str:
        payload={'decision_time':decision_time,'actions':[a.__dict__ for a in actions]}
        return sha256(json.dumps(payload,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
