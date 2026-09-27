from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field

@dataclass
class Metrics:
    counters: dict[str,int] = field(default_factory=dict)
    gauges: dict[str,float] = field(default_factory=dict)
    timings_ms: dict[str,list[float]] = field(default_factory=dict)
    def inc(self,name,n=1): self.counters[name]=self.counters.get(name,0)+n
    def gauge(self,name,value): self.gauges[name]=float(value)
    def observe_ms(self,name,value): self.timings_ms.setdefault(name,[]).append(float(value))
    def snapshot(self):
        return {'counters':dict(self.counters),'gauges':dict(self.gauges),
                'timings_ms':{k:{'count':len(v),'avg':sum(v)/len(v)} for k,v in self.timings_ms.items() if v}}

class AuditLogger:
    def __init__(self, logger=None): self.logger=logger or logging.getLogger('orion.audit')
    def emit(self, actor, action, object_id, **details):
        self.logger.info(json.dumps({'ts':time.time(),'actor':actor,'action':action,'object_id':object_id,'details':details},sort_keys=True))
