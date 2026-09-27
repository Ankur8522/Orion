from dataclasses import dataclass
from .queue import ResearchQueue
from ..data.pit import PITStore
from .sector import SectorMetricEngine
from .forensics import ForensicEngine
from .market_signals import analyze as market_analyze
from .priority import PriorityEngine
@dataclass
class ResearchResult:
    security_id:str; evidence_count:int; status:str; metrics:dict|None=None; forensic:tuple=(); priority:object=None; market:object=None
class Pipeline:
    def __init__(self,pit:PITStore,queue:ResearchQueue,quality_gate=None,orchestrator=None,sector_engine=None,forensic_engine=None,priority_engine=None):
        self.pit=pit; self.queue=queue; self.quality_gate=quality_gate; self.orchestrator=orchestrator; self.sector_engine=sector_engine or SectorMetricEngine(); self.forensic_engine=forensic_engine or ForensicEngine(); self.priority_engine=priority_engine or PriorityEngine()
    def run_one(self,security_id,decision_time,opinions=(),blockers=(),sector='generic',facts=None):
        if self.quality_gate:
            q=self.quality_gate.check(security_id,decision_time)
            if q.status!='PASS': raise RuntimeError('RESEARCH_BLOCKED_DATA_QUALITY')
        ev=self.pit.as_of(security_id,decision_time)
        if not ev: raise RuntimeError('RESEARCH_BLOCKED_NO_EVIDENCE')
        rows=[]
        for x in ev:
            if isinstance(x,dict): rows.append(x)
            else: rows.append({'evidence_id':getattr(x,'evidence_id',None),'available_time':getattr(x,'available_time',None),'confidence':getattr(x,'confidence',0),'content_hash':getattr(x,'content_hash','')})
        if self.orchestrator: decision=self.orchestrator.run(security_id,decision_time,rows,opinions,blockers)
        else:
            class F: pass
            decision=F(); decision.status='EVIDENCE_SUPPORTED'; decision.review={'evidence_ids':tuple(r.get('evidence_id') for r in rows)}
        fs=facts or {}
        metric=self.sector_engine.run(security_id,sector,fs); forensic=self.forensic_engine.inspect(metric.metrics)
        price_rows=[r for r in ev if isinstance(r,dict) and 'close' in r]
        market=market_analyze(security_id,price_rows)
        pr=self.priority_engine.score(security_id,data_gap=min(1,len(metric.warnings)/5),evidence_risk=1 if forensic else 0,market_signal=float(market.score)/100)
        return ResearchResult(security_id,len(rows),decision.status,metric.metrics,forensic,pr,market)
    def run(self,security_ids,decision_time):
        job=self.queue.enqueue(security_ids)
        if job.status.name=='READY': self.queue.claim(job.key)
        out=[]
        for sid in security_ids: out.append(self.run_one(sid,decision_time))
        self.queue.complete(job.key); return out
