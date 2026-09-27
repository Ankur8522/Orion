from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class MetaTrainingRow:
    decision_time: str
    specialist_probabilities: Mapping[str,float]
    outcome: int
    regime: str = 'UNKNOWN'

@dataclass(frozen=True)
class MetaMetrics:
    model_id: str
    train_observations: int
    validation_observations: int
    brier: float | None
    log_loss: float | None
    calibration_error: float | None
    specialist_names: tuple[str,...]
    lineage_hash: str
    trained: bool

@dataclass(frozen=True)
class MetaPrediction:
    probability: float
    uncertainty: float
    specialist_weights: Mapping[str,float]
    metrics: MetaMetrics

class LearnedMetaIntelligence:
    """Chronological meta-learner over specialist probabilities.

    It learns trust weights from outcomes rather than using permanent hand-set
    weights.  Missing specialist probabilities are not silently imputed.
    """
    def __init__(self, model_id='orion-meta-v1', learning_rate=.08, epochs=300, l2=.01):
        self.model_id=model_id; self.lr=learning_rate; self.epochs=epochs; self.l2=l2
        self.names: tuple[str,...]=(); self.weights: list[float]=[]; self.metrics=MetaMetrics(model_id,0,0,None,None,None,(),'',False)

    @staticmethod
    def _sigmoid(z): return 1/(1+math.exp(-max(-40,min(40,z))))
    def fit(self, rows: Sequence[MetaTrainingRow], *, validation_fraction=.25):
        rows=tuple(sorted(rows,key=lambda x:x.decision_time))
        names=tuple(sorted({k for r in rows for k in r.specialist_probabilities}))
        usable=[r for r in rows if r.outcome in (0,1) and all(k in r.specialist_probabilities and 0<=float(r.specialist_probabilities[k])<=1 for k in names)]
        if len(usable)<8 or not names:
            self.metrics=MetaMetrics(self.model_id,len(usable),0,None,None,None,names,'',False); return self.metrics
        split=max(1,min(len(usable)-1,int(len(usable)*(1-validation_fraction))))
        train,test=usable[:split],usable[split:]
        self.names=names; self.weights=[0.0]+[1.0/len(names)]*len(names)
        for _ in range(self.epochs):
            grads=[0.0]*len(self.weights)
            for r in train:
                x=[1.0]+[float(r.specialist_probabilities[n])-.5 for n in names]
                p=self._sigmoid(sum(a*b for a,b in zip(self.weights,x))); err=p-r.outcome
                for j,v in enumerate(x): grads[j]+=err*v
            for j in range(len(self.weights)):
                reg=0 if j==0 else self.l2*self.weights[j]
                self.weights[j]-=self.lr*(grads[j]/len(train)+reg)
        def _raw_predict(probabilities):
            x=[1.0]+[float(probabilities[n])-.5 for n in self.names]
            return self._sigmoid(sum(a*b for a,b in zip(self.weights,x)))
        preds=[_raw_predict(r.specialist_probabilities) for r in test]
        labels=[r.outcome for r in test]
        brier=sum((p-y)**2 for p,y in zip(preds,labels))/len(preds)
        ll=-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in zip(preds,labels))/len(preds)
        cal=abs(sum(preds)/len(preds)-sum(labels)/len(labels))
        payload={'model':self.model_id,'train':len(train),'test':len(test),'brier':brier,'log_loss':ll,'calibration_error':cal,'names':names,'weights':self.weights}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.metrics=MetaMetrics(self.model_id,len(train),len(test),brier,ll,cal,names,lineage,True)
        return self.metrics

    def predict(self, probabilities: Mapping[str,float]) -> MetaPrediction:
        if not self.metrics.trained: raise RuntimeError('META_MODEL_NOT_TRAINED')
        missing=[n for n in self.names if n not in probabilities]
        if missing: raise ValueError('MISSING_SPECIALIST_PROBABILITIES:'+','.join(missing))
        x=[1.0]+[float(probabilities[n])-.5 for n in self.names]
        p=self._sigmoid(sum(a*b for a,b in zip(self.weights,x)))
        raw=[max(0.0,w) for w in self.weights[1:]]; total=sum(raw) or 1.0
        trust={n:w/total for n,w in zip(self.names,raw)}
        uncertainty=min(1.0,0.15+abs(p-.5)*-0.8+0.25/max(1,self.metrics.validation_observations)**.5)
        return MetaPrediction(round(p,12),round(max(0.0,uncertainty),12),trust,self.metrics)
