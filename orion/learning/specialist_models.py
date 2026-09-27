from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class TrainingExample:
    decision_time: str
    features: Mapping[str, float]
    outcome: int
    regime: str = 'UNKNOWN'

@dataclass(frozen=True)
class SpecialistModelMetrics:
    model_id: str
    train_observations: int
    validation_observations: int
    brier: float | None
    log_loss: float | None
    calibration_error: float | None
    regimes: tuple[str, ...]
    feature_names: tuple[str, ...]
    trained: bool
    lineage_hash: str

@dataclass(frozen=True)
class SpecialistPrediction:
    model_id: str
    probability: float
    uncertainty: float
    feature_coverage: float
    regime_coverage: int
    metrics: SpecialistModelMetrics

class ChronologicalLogisticSpecialist:
    """Small dependency-free, chronological logistic specialist.

    It is deliberately conservative: no random split, no implicit imputation and
    no prediction when required features are missing.  It is suitable as a
    governed baseline until a richer ML backend is explicitly introduced.
    """
    def __init__(self, model_id: str, feature_names: Sequence[str], *, learning_rate: float = .08, epochs: int = 400, l2: float = .01):
        self.model_id = str(model_id)
        self.feature_names = tuple(dict.fromkeys(feature_names))
        self.learning_rate = float(learning_rate); self.epochs = int(epochs); self.l2 = float(l2)
        self._weights = [0.0] * (len(self.feature_names) + 1)
        self.metrics = SpecialistModelMetrics(self.model_id, 0, 0, None, None, None, (), self.feature_names, False, '')

    @staticmethod
    def _sigmoid(z: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, z))))

    def _vector(self, row: Mapping[str, float]) -> list[float] | None:
        vals=[]
        for name in self.feature_names:
            value=row.get(name)
            if value is None:
                return None
            try: value=float(value)
            except (TypeError, ValueError): return None
            if not math.isfinite(value): return None
            vals.append(max(-8.0, min(8.0, value)))
        return [1.0] + vals

    def _predict_vec(self, x: Sequence[float]) -> float:
        return self._sigmoid(sum(w*v for w,v in zip(self._weights,x)))

    @staticmethod
    def _metrics(model_id, preds, labels, regimes, feature_names, train_n, test_n):
        if not preds:
            brier=ll=cal=None
        else:
            brier=sum((p-y)**2 for p,y in zip(preds,labels))/len(preds)
            ll=-sum(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)) for p,y in zip(preds,labels))/len(preds)
            bins=[]
            for lo in range(0,10):
                rows=[(p,y) for p,y in zip(preds,labels) if lo/10 <= p < (lo+1)/10 or (lo==9 and p<=1)]
                if rows: bins.append(abs(sum(p for p,_ in rows)/len(rows)-sum(y for _,y in rows)/len(rows))*len(rows)/len(preds))
            cal=sum(bins)
        payload={'model_id':model_id,'train':train_n,'test':test_n,'brier':brier,'log_loss':ll,'calibration_error':cal,'regimes':sorted(set(regimes)),'features':feature_names}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return SpecialistModelMetrics(model_id,train_n,test_n,brier,ll,cal,tuple(sorted(set(regimes))),tuple(feature_names),True if train_n>0 else False,lineage)

    def fit(self, examples: Sequence[TrainingExample], *, validation_fraction: float = .25) -> SpecialistModelMetrics:
        rows=tuple(sorted(examples,key=lambda e:e.decision_time))
        valid_rows=[e for e in rows if e.outcome in (0,1) and self._vector(e.features) is not None]
        if len(valid_rows)<8: self.metrics=SpecialistModelMetrics(self.model_id,len(valid_rows),0,None,None,None,(),self.feature_names,False,''); return self.metrics
        split=max(1,min(len(valid_rows)-1,int(len(valid_rows)*(1-validation_fraction))))
        train,test=valid_rows[:split],valid_rows[split:]
        for _ in range(self.epochs):
            grads=[0.0]*len(self._weights)
            for ex in train:
                x=self._vector(ex.features); p=self._predict_vec(x); err=p-ex.outcome
                for j,v in enumerate(x): grads[j]+=err*v
            n=float(len(train))
            for j in range(len(self._weights)):
                reg=0.0 if j==0 else self.l2*self._weights[j]
                self._weights[j]-=self.learning_rate*(grads[j]/n+reg)
        preds=[self._predict_vec(self._vector(e.features)) for e in test]
        self.metrics=self._metrics(self.model_id,preds,[e.outcome for e in test],[e.regime for e in test],self.feature_names,len(train),len(test))
        return self.metrics

    def predict(self, features: Mapping[str,float], *, regime: str = 'UNKNOWN') -> SpecialistPrediction | None:
        if not self.metrics.trained: return None
        x=self._vector(features)
        if x is None: return None
        p=self._predict_vec(x)
        coverage=sum(1 for k in self.feature_names if k in features)/max(1,len(self.feature_names))
        uncertainty=min(1.0, 0.35 + 0.65*abs(p-.5)*-1 + (0.15 if regime not in self.metrics.regimes else 0.0))
        return SpecialistPrediction(self.model_id,p,uncertainty,coverage,1 if regime in self.metrics.regimes else 0,self.metrics)
