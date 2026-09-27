from __future__ import annotations
from dataclasses import dataclass
from .contracts import AcquisitionJob, AcquisitionState
from ..data.http_provider import PublicHTTPProvider
from ..documents.ingest import DocumentIngestor
from .classifier import classify_document

@dataclass(frozen=True)
class AcquisitionResult:
    job_id:str
    state:AcquisitionState
    url:str
    payload_hash:str|None
    document_kind:str|None
    confidence:float
    error:str|None=None

class AcquisitionExecutor:
    def __init__(self,provider:PublicHTTPProvider,ingestor=None): self.provider=provider; self.ingestor=ingestor or DocumentIngestor()
    def run(self,job:AcquisitionJob):
        if job.metadata.get('requires_discovery')=='true':
            return AcquisitionResult(job.job_id,AcquisitionState.BLOCKED,job.url,None,None,0.0,'URL_DISCOVERY_REQUIRED')
        try:
            fetched=self.provider.fetch(job.url)
            text=''
            if 'text' in fetched.content_type or 'json' in fetched.content_type:
                text=fetched.payload.decode('utf-8','replace')
            artifact=self.ingestor.ingest_bytes(fetched.payload,job.source_id,job.security_id,fetched.content_type,fetched.fetched_at)
            kind,conf=classify_document(text,fetched.content_type)
            return AcquisitionResult(job.job_id,AcquisitionState.PARSED,fetched.url,fetched.sha256,kind.value,conf)
        except Exception as e:
            return AcquisitionResult(job.job_id,AcquisitionState.FAILED,job.url,None,None,0.0,type(e).__name__+':'+str(e))
