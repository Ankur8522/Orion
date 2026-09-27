from dataclasses import dataclass
from enum import Enum
import hashlib, json
from threading import RLock

class Status(str,Enum):
    READY='READY'; RUNNING='RUNNING'; COMPLETE='COMPLETE'; FAILED='FAILED'

@dataclass
class Job:
    key: str
    security_ids: tuple[str,...]
    status: Status=Status.READY
    attempts: int=0
    error: str|None=None

class ResearchQueue:
    def __init__(self): self.jobs={}; self._lock=RLock()
    def key(self, security_ids):
        return hashlib.sha256(json.dumps(sorted(security_ids)).encode()).hexdigest()
    def enqueue(self, security_ids):
        k=self.key(security_ids)
        with self._lock:
            if k not in self.jobs: self.jobs[k]=Job(k,tuple(sorted(security_ids)))
            return self.jobs[k]
    def claim(self,k):
        with self._lock:
            j=self.jobs[k]
            if j.status!=Status.READY: raise ValueError('JOB_NOT_READY')
            j.status=Status.RUNNING; j.attempts+=1; return j
    def complete(self,k):
        with self._lock: self.jobs[k].status=Status.COMPLETE
    def fail(self,k,error):
        with self._lock: self.jobs[k].status=Status.FAILED; self.jobs[k].error=error
    def retry(self,k):
        with self._lock:
            j=self.jobs[k]
            if j.status!=Status.FAILED: raise ValueError('JOB_NOT_FAILED')
            j.status=Status.READY; j.error=None
