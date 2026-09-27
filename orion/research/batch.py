from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from .pipeline import Pipeline

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
@dataclass(frozen=True)
class BatchReport:
    total:int; completed:int; blocked:int; failed:int; results:tuple; checkpoint:int
class BatchExecutor:
    def __init__(self,pipeline:Pipeline,batch_size=25,store=None): self.pipeline=pipeline; self.batch_size=batch_size; self.store=store
    def run(self,security_ids,decision_time,job_key='default'):
        ids=list(dict.fromkeys(security_ids)); results=[]; blocked=failed=completed=cursor=0
        old=self.store.job(job_key) if self.store else None; cursor=int(old['cursor']) if old else 0; attempts=((old or {}).get('attempts',0)+1 if old else 1)
        if self.store: self.store.job_upsert(job_key,'RUNNING',ids,cursor,attempts,None,now())
        for i in range(cursor,len(ids),self.batch_size):
            chunk=ids[i:i+self.batch_size]
            try:
                r=self.pipeline.run(chunk,decision_time)
                for item in r:
                    status=getattr(item,'status','')
                    if status=='BLOCKED': blocked+=1
                    else: completed+=1
                results.extend(r); cursor=i+len(chunk)
                if self.store: self.store.job_upsert(job_key,'RUNNING',ids,cursor,attempts,None,now())
            except RuntimeError as e:
                failed+=len(chunk); results.append({'batch_start':i,'security_ids':chunk,'error':str(e)}); cursor=i
                if self.store: self.store.job_upsert(job_key,'FAILED',ids,cursor,attempts,str(e),now())
                break
        status='COMPLETE' if cursor==len(ids) else 'FAILED'
        if self.store: self.store.job_upsert(job_key,status,ids,cursor,attempts,None if status=='COMPLETE' else 'BATCH_FAILED',now())
        return BatchReport(len(ids),completed,blocked,failed,tuple(results),cursor)
