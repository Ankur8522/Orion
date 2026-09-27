from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class DocumentKind(str, Enum):
    FINANCIAL_RESULTS='financial_results'
    AUDITOR_REPORT='auditor_report'
    BOARD_DISCLOSURE='board_disclosure'
    INVESTOR_PRESENTATION='investor_presentation'
    ANNUAL_REPORT='annual_report'
    CORPORATE_ACTION='corporate_action'
    OTHER='other'

class AcquisitionState(str, Enum):
    PLANNED='PLANNED'; FETCHED='FETCHED'; PARSED='PARSED'; PROMOTED='PROMOTED'; BLOCKED='BLOCKED'; FAILED='FAILED'

@dataclass(frozen=True)
class SourceSpec:
    source_id:str
    host:str
    base_url:str
    dataset:str
    mode:str='public'
    priority:int=100
    enabled:bool=True
    content_types:tuple[str,...]=('application/json','text/html','application/pdf')

@dataclass(frozen=True)
class AcquisitionJob:
    job_id:str
    security_id:str
    source_id:str
    dataset:str
    url:str
    event_time:str
    available_time:str
    decision_time:str
    document_kind:DocumentKind|None=None
    metadata:Mapping[str,str]=None

    def __post_init__(self):
        if not self.job_id or not self.security_id or not self.source_id: raise ValueError('INVALID_JOB_IDENTITY')
        if self.metadata is None: object.__setattr__(self,'metadata',{})
