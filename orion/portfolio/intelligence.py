from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from math import sqrt

@dataclass(frozen=True)
class Holding:
    security_id: str
    weight: float
    beta: float = 1.0
    volatility: float = 0.0

@dataclass(frozen=True)
class FactorExposure:
    factor: str
    exposure: float
    shock: float = 0.0

@dataclass(frozen=True)
class PortfolioAssessment:
    gross_exposure: float
    concentration_hhi: float
    factor_risk: float
    scenario_loss: float
    scenario_gain: float
    expected_scenario_impact: float
    robustness: float
    fragility: float
    capital_efficiency: float
    priority_actions: tuple[str, ...]
    lineage_hash: str

class PortfolioIntelligenceBrain:
    """Auditable portfolio reasoning layer.

    Combines supplied holdings/factor/scenario impacts; it does not invent prices,
    correlations, returns, or risk estimates. All inputs remain lineage-visible.
    """
    @staticmethod
    def _clip(x, lo=0.0, hi=1.0):
        return max(lo, min(hi, float(x)))

    def assess(self, holdings: tuple[Holding, ...], factors: tuple[FactorExposure, ...] = (),
               scenario_impacts: tuple[float, ...] = (), robustness: float = 0.5) -> PortfolioAssessment:
        if not holdings:
            raise ValueError("NO_HOLDINGS")
        if any(not h.security_id or h.weight < 0 or h.beta < 0 or h.volatility < 0 for h in holdings):
            raise ValueError("INVALID_HOLDING")
        if any(not f.factor or abs(f.exposure) > 10 or abs(f.shock) > 10 for f in factors):
            raise ValueError("INVALID_FACTOR_EXPOSURE")
        weights = [float(h.weight) for h in holdings]
        total = sum(weights)
        if total <= 0:
            raise ValueError("INVALID_TOTAL_WEIGHT")
        norm = [w / total for w in weights]
        hhi = sum(w*w for w in norm)
        gross = sum(weights)
        factor_risk = sum(abs(f.exposure * f.shock) for f in factors)
        scenario_loss = min([x for x in scenario_impacts if x < 0], default=0.0)
        scenario_gain = max([x for x in scenario_impacts if x > 0], default=0.0)
        expected = sum(scenario_impacts) / len(scenario_impacts) if scenario_impacts else 0.0
        vol_proxy = self._clip(sum(w * h.volatility for w,h in zip(norm, holdings)))
        beta_proxy = sum(w * h.beta for w,h in zip(norm, holdings))
        concentration_penalty = self._clip((hhi - 0.10) / 0.40)
        factor_penalty = self._clip(factor_risk / 2.0)
        stress_penalty = self._clip(abs(scenario_loss) / 2.0)
        robustness_score = self._clip(float(robustness) * (1-concentration_penalty) * (1-factor_penalty) * (1-stress_penalty))
        fragility = self._clip(1-robustness_score)
        capital_efficiency = self._clip(1 / max(1.0, beta_proxy + vol_proxy + factor_penalty))
        actions=[]
        if hhi > 0.25: actions.append("REDUCE_CONCENTRATION")
        if factor_penalty >= 0.50: actions.append("REVIEW_FACTOR_CONCENTRATION")
        if abs(scenario_loss) >= 1.0: actions.append("STRESS_LOSS_REVIEW")
        if fragility >= 0.60: actions.append("REASSESS_PORTFOLIO_ROBUSTNESS")
        if not actions: actions.append("MONITOR_MATERIAL_STATE_CHANGES")
        payload={"holdings":[h.__dict__ for h in holdings],"factors":[f.__dict__ for f in factors],"scenarios":list(scenario_impacts),"robustness":robustness}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return PortfolioAssessment(round(gross,12),round(hhi,12),round(factor_risk,12),round(scenario_loss,12),round(scenario_gain,12),round(expected,12),round(robustness_score,12),round(fragility,12),round(capital_efficiency,12),tuple(actions),lineage)
