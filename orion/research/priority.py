from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ResearchPriority:
    security_id: str; score: float; reasons: tuple[str,...]

class PriorityEngine:
    """Information-value prioritization; all inputs are evidence/context signals."""
    def score(self, security_id, *, data_gap=0, thesis_change=0, event_urgency=0,
              portfolio_exposure=0, evidence_risk=0, market_signal=0,
              forecast_failure=0, model_disagreement=0, risk_change=0,
              valuation_regime_change=0, catalyst_approaching=0, regime_change=0,
              data_quality_improvement=0, evidence_conflict=0, uncertainty=0):
        names=('DATA_GAP','THESIS_CHANGE','EVENT_URGENCY','PORTFOLIO_EXPOSURE','EVIDENCE_RISK','MARKET_SIGNAL',
               'FORECAST_FAILURE','MODEL_DISAGREEMENT','RISK_CHANGE','VALUATION_REGIME_CHANGE','CATALYST_APPROACHING',
               'REGIME_CHANGE','DATA_QUALITY_IMPROVEMENT','EVIDENCE_CONFLICT','UNCERTAINTY')
        vals=[data_gap,thesis_change,event_urgency,portfolio_exposure,evidence_risk,market_signal,
              forecast_failure,model_disagreement,risk_change,valuation_regime_change,catalyst_approaching,
              regime_change,data_quality_improvement,evidence_conflict,uncertainty]
        if any(float(v)<0 for v in vals): raise ValueError('NEGATIVE_SIGNAL')
        weights=[20,25,25,20,10,5,9,8,8,4,4,4,3,7,7]
        contributions=[w*min(1,float(v)) for w,v in zip(weights,vals)]
        score=min(100.0,sum(contributions))
        reasons=tuple(n for n,v in zip(names,vals) if float(v)>0)
        return ResearchPriority(security_id,score,reasons)
