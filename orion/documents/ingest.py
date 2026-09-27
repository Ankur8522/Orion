from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
import re

@dataclass(frozen=True)
class DocumentArtifact:
    document_id:str
    source_id:str
    security_id:str|None
    content_hash:str
    captured_at:str
    media_type:str
    byte_size:int

@dataclass(frozen=True)
class EvidenceChunk:
    evidence_id:str
    document_id:str
    security_id:str|None
    locator:str
    text:str
    content_hash:str
    available_time:str
    confidence:float

class DocumentIngestor:
    def ingest_bytes(self, data:bytes, source_id:str, security_id:str|None=None, media_type='application/octet-stream', captured_at=None):
        captured_at=captured_at or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        h=sha256(data).hexdigest()
        document_id=sha256((source_id+'|'+h).encode()).hexdigest()
        return DocumentArtifact(document_id,source_id,security_id,h,captured_at,media_type,len(data))

    def text_chunks(self, artifact:DocumentArtifact, text:str, available_time:str, chunk_chars=1800):
        if chunk_chars<100: raise ValueError('INVALID_CHUNK_SIZE')
        chunks=[]
        clean=re.sub(r'\s+',' ',text).strip()
        for i in range(0,len(clean),chunk_chars):
            body=clean[i:i+chunk_chars]
            eid=sha256(f'{artifact.document_id}:{i}:{body}'.encode()).hexdigest()
            chunks.append(EvidenceChunk(eid,artifact.document_id,artifact.security_id,f'char:{i}-{i+len(body)-1}',body,sha256(body.encode()).hexdigest(),available_time,0.8))
        return chunks
