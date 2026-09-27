from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib,json,sqlite3
from threading import RLock

class PersistentJobStatus(str,Enum): READY='READY'; RUNNING='RUNNING'; COMPLETE='COMPLETE'; FAILED='FAILED'
@dataclass(frozen=True)
class PersistentJob:
    key:str; security_ids:tuple[str,...]; status:PersistentJobStatus; attempts:int; error:str|None
class PersistentResearchQueue:
    """Restart-safe research queue; deterministic job identity and explicit lifecycle."""
    def __init__(self,path=':memory:'):
        self.path=str(path); self._lock=RLock(); self._db=sqlite3.connect(self.path,check_same_thread=False)
        self._db.execute('CREATE TABLE IF NOT EXISTS research_queue(key TEXT PRIMARY KEY,security_ids_json TEXT,status TEXT,attempts INTEGER,error TEXT)'); self._db.commit()
    @staticmethod
    def key(security_ids): return hashlib.sha256(json.dumps(sorted(tuple(security_ids))).encode()).hexdigest()
    def enqueue(self,security_ids):
        ids=tuple(dict.fromkeys(security_ids)); k=self.key(ids)
        with self._lock:
            self._db.execute('INSERT OR IGNORE INTO research_queue VALUES(?,?,?,?,?)',(k,json.dumps(ids),PersistentJobStatus.READY.value,0,None)); self._db.commit()
        return self.get(k)
    def get(self,k):
        r=self._db.execute('SELECT * FROM research_queue WHERE key=?',(k,)).fetchone();
        return None if r is None else PersistentJob(r[0],tuple(json.loads(r[1])),PersistentJobStatus(r[2]),int(r[3]),r[4])
    def jobs(self): return tuple(PersistentJob(r[0],tuple(json.loads(r[1])),PersistentJobStatus(r[2]),int(r[3]),r[4]) for r in self._db.execute('SELECT * FROM research_queue ORDER BY key'))
    def claim(self,k):
        with self._lock:
            j=self.get(k)
            if j is None: raise KeyError('JOB_NOT_FOUND')
            if j.status is not PersistentJobStatus.READY: raise ValueError('JOB_NOT_READY')
            self._db.execute('UPDATE research_queue SET status=?,attempts=? WHERE key=?',(PersistentJobStatus.RUNNING.value,j.attempts+1,k)); self._db.commit(); return self.get(k)
    def complete(self,k):
        with self._lock: self._db.execute('UPDATE research_queue SET status=?,error=NULL WHERE key=?',(PersistentJobStatus.COMPLETE.value,k)); self._db.commit()
    def fail(self,k,error):
        with self._lock: self._db.execute('UPDATE research_queue SET status=?,error=? WHERE key=?',(PersistentJobStatus.FAILED.value,str(error),k)); self._db.commit()
    def retry(self,k):
        with self._lock: self._db.execute('UPDATE research_queue SET status=?,error=NULL WHERE key=? AND status=?',(PersistentJobStatus.READY.value,k,PersistentJobStatus.FAILED.value)); self._db.commit()
