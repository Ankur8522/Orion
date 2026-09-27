from dataclasses import dataclass
from .time import parse_utc

@dataclass(frozen=True)
class QualityReport:
    security_id:str; decision_time:str; observations:int; evidence:int; missing:tuple[str,...]; status:str
    warnings:tuple[str,...]=()

class DataQualityGate:
    def __init__(self,store): self.store=store
    def check(self,security_id,decision_time,datasets=('results',),min_evidence=0):
        parse_utc(decision_time)
        missing=tuple(d for d in datasets if not self.store.pit(security_id,d,decision_time))
        evidence=self.store.evidence_for(security_id,decision_time)
        obs=sum(len(self.store.pit(security_id,d,decision_time)) for d in datasets)
        warnings=[]
        if len(evidence)<min_evidence: warnings.append('INSUFFICIENT_EVIDENCE')
        status='PASS' if not missing and len(evidence)>=min_evidence else 'BLOCKED'
        return QualityReport(security_id,decision_time,obs,len(evidence),missing,status,tuple(warnings))
