from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Mapping, Sequence

@dataclass(frozen=True)
class SpecialistResult:
    name: str
    score: float|None
    status: str
    feature_count: int
    required_features: tuple[str,...]
    missing_features: tuple[str,...]
    evidence_count: int
    lineage_hash: str
    probability: float|None = None
    uncertainty: float = 1.0
    model_id: str = 'deterministic-domain-baseline'
    trained: bool = False

class Specialist:
    name='base'; required: tuple[str,...]=()
    def evaluate(self, features: Mapping[str,float], *, evidence_count:int=0) -> SpecialistResult:
        missing=tuple(k for k in self.required if k not in features or not math.isfinite(float(features[k])))
        score=None if missing else max(0.0,min(1.0,self._score(features)))
        status='READY' if score is not None else 'INSUFFICIENT_FEATURES'
        payload={'name':self.name,'score':score,'features':sorted((k,features.get(k)) for k in self.required),'evidence_count':evidence_count}
        return SpecialistResult(self.name,score,status,len(self.required)-len(missing),self.required,missing,evidence_count,sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest(),score,1.0 if score is None else max(.05,1-min(1,evidence_count/50)),self.name,False)
    def _score(self, f): raise NotImplementedError

class MeanSpecialist(Specialist):
    def _score(self,f): return sum(float(f[x]) for x in self.required)/len(self.required)

class FundamentalSpecialist(MeanSpecialist):
    name='fundamental_quality'; required=('fundamental_quality','earnings_growth','cashflow_quality','risk_quality')
class EarningsSpecialist(MeanSpecialist):
    name='earnings'; required=('earnings_growth','earnings_revision','margin_quality','cashflow_quality')
class ValuationSpecialist(MeanSpecialist):
    name='valuation'; required=('valuation_attractiveness','fundamental_quality','earnings_growth','historical_valuation_percentile')
class BalanceSheetSpecialist(MeanSpecialist):
    name='balance_sheet'; required=('balance_sheet_quality','leverage_quality','interest_coverage','liquidity_quality')
class ForensicSpecialist(MeanSpecialist):
    name='forensic'; required=('forensic_quality','accrual_quality','cash_conversion','governance_quality')
class BusinessSpecialist(MeanSpecialist):
    name='business_visibility'; required=('business_visibility','earnings_growth','cashflow_quality','order_book_quality')
class TechnicalSpecialist(MeanSpecialist):
    name='technical'; required=('technical_trend','technical_momentum','volume_confirmation','volatility_quality')
class MomentumSpecialist(MeanSpecialist):
    name='momentum'; required=('technical_momentum','relative_strength','volume_confirmation','earnings_momentum')
class HistoricalSpecialist(MeanSpecialist):
    name='historical_pattern'; required=('historical_similarity','historical_success_rate','historical_downside_quality','historical_mfe')
class RegimeSpecialist(MeanSpecialist):
    name='regime'; required=('regime_fit','technical_trend','risk_quality','macro_regime_fit')
class CatalystSpecialist(MeanSpecialist):
    name='catalyst'; required=('catalyst_strength','catalyst_quality','estimate_revision','business_visibility')
class RiskSpecialist(MeanSpecialist):
    name='risk'; required=('risk_quality','liquidity_quality','drawdown_quality','event_risk_quality')
class MacroSpecialist(MeanSpecialist):
    name='macro'; required=('macro_regime_fit','rate_sensitivity','currency_sensitivity','commodity_sensitivity')
class SectorSpecialist(MeanSpecialist):
    name='sector'; required=('sector_momentum','sector_earnings_momentum','sector_valuation','relative_strength')
class EvidenceSentimentSpecialist(MeanSpecialist):
    name='evidence_sentiment'; required=('evidence_quality','sentiment_quality','news_catalyst_quality','counter_evidence_quality')

SPECIALIST_CATALOG=(
    FundamentalSpecialist(), EarningsSpecialist(), ValuationSpecialist(), BalanceSheetSpecialist(),
    ForensicSpecialist(), BusinessSpecialist(), TechnicalSpecialist(), MomentumSpecialist(),
    HistoricalSpecialist(), RegimeSpecialist(), CatalystSpecialist(), RiskSpecialist(),
    MacroSpecialist(), SectorSpecialist(), EvidenceSentimentSpecialist(),
)
DEFAULT_SPECIALISTS=SPECIALIST_CATALOG

def evaluate_specialists(features: Mapping[str,float], *, evidence_count:int=0, specialists:Sequence[Specialist]=DEFAULT_SPECIALISTS):
    return tuple(s.evaluate(features,evidence_count=evidence_count) for s in specialists)

def specialist_feature_union(specialists: Sequence[Specialist]=DEFAULT_SPECIALISTS) -> tuple[str,...]:
    return tuple(sorted({f for s in specialists for f in s.required}))
