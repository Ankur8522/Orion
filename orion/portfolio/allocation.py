from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class AllocationCandidate:
    security_id: str
    expected_return: float
    uncertainty: float = 0.5
    robustness: float = 0.5
    fragility: float = 0.5
    calibration: float = 0.5
    factor_overlap: float = 0.0
    current_weight: float = 0.0

@dataclass(frozen=True)
class AllocationAssessment:
    scores: tuple[tuple[str, float], ...]
    target_weights: tuple[tuple[str, float], ...]
    max_additions: tuple[tuple[str, float], ...]
    max_reductions: tuple[tuple[str, float], ...]
    portfolio_expected_return: float
    portfolio_uncertainty: float
    diversification_score: float
    adaptive_triggers: tuple[str, ...]
    cash_weight: float = 0.0
    lineage_hash: str = ""

class DynamicCapitalAllocationBrain:
    """Constrained, explainable capital-allocation layer.

    It converts caller-supplied thesis/portfolio signals into relative allocation
    candidates. It does not fetch prices, predict returns, or place orders.
    Scores are bounded and target weights are normalized to 100%.
    """
    @staticmethod
    def _clip(x, lo=0.0, hi=1.0):
        return max(lo, min(hi, float(x)))

    def assess(self, candidates: tuple[AllocationCandidate, ...], *, max_weight: float = 0.25,
               cash_floor: float = 0.0, min_weight: float = 0.0) -> AllocationAssessment:
        if not candidates:
            raise ValueError("NO_ALLOCATION_CANDIDATES")
        if not 0 < max_weight <= 1 or not 0 <= cash_floor < 1 or not 0 <= min_weight <= max_weight:
            raise ValueError("INVALID_ALLOCATION_CONSTRAINTS")
        if len({c.security_id for c in candidates}) != len(candidates):
            raise ValueError("DUPLICATE_ALLOCATION_SECURITY")
        if any(not c.security_id or not -1 <= c.expected_return <= 1 or
               not 0 <= c.uncertainty <= 1 or not 0 <= c.robustness <= 1 or
               not 0 <= c.fragility <= 1 or not 0 <= c.calibration <= 1 or
               not 0 <= c.factor_overlap <= 1 or c.current_weight < 0
               for c in candidates):
            raise ValueError("INVALID_ALLOCATION_SIGNAL")
        if sum(c.current_weight for c in candidates) > 1.0000001:
            raise ValueError("CURRENT_WEIGHTS_EXCEED_ONE")

        raw = []
        for c in candidates:
            return_score = self._clip((c.expected_return + 1) / 2)
            score = (0.34 * return_score + 0.20 * c.robustness +
                     0.16 * c.calibration + 0.15 * (1 - c.uncertainty) +
                     0.10 * (1 - c.fragility) + 0.05 * (1 - c.factor_overlap))
            raw.append((c.security_id, self._clip(score)))

        # Conservative constrained normalization. Low/negative-quality candidates
        # receive zero rather than forced capital; remaining capital can stay cash.
        positive = [(sid, s) for sid, s in raw if s >= 0.45]
        investable = max(0.0, 1.0 - cash_floor)
        weights = {sid: 0.0 for sid, _ in raw}
        remaining = investable
        active = set(sid for sid, _ in positive)
        for _ in range(len(raw) + 2):
            if not active or remaining <= 1e-12:
                break
            denom = sum(s for sid, s in positive if sid in active)
            changed = False
            for sid, s in positive:
                if sid not in active:
                    continue
                proposed = remaining * s / denom
                if proposed > max_weight:
                    weights[sid] = max_weight
                    remaining -= max_weight
                    active.remove(sid)
                    changed = True
            if not changed:
                for sid, s in positive:
                    if sid in active:
                        weights[sid] = remaining * s / denom
                remaining = 0.0
                break
        if min_weight > 0:
            for sid, _ in raw:
                if 0 < weights[sid] < min_weight:
                    weights[sid] = 0.0

        target = tuple(sorted((sid, round(w, 12)) for sid, w in weights.items()))
        score_map = dict(raw)
        additions = tuple(sorted((c.security_id, round(max(0.0, weights[c.security_id] - c.current_weight), 12)) for c in candidates if weights[c.security_id] > c.current_weight))
        reductions = tuple(sorted((c.security_id, round(max(0.0, c.current_weight - weights[c.security_id]), 12)) for c in candidates if c.current_weight > weights[c.security_id]))
        total_target = sum(weights.values())
        exp = sum(weights[c.security_id] * c.expected_return for c in candidates)
        unc = sum(weights[c.security_id] * c.uncertainty for c in candidates) / max(total_target, 1e-12)
        hhi = sum((w / max(total_target, 1e-12)) ** 2 for w in weights.values() if w > 0)
        diversification = self._clip(1 - (hhi - 0.1) / 0.4)
        triggers = []
        for c in candidates:
            if c.fragility >= 0.65: triggers.append(f"REVIEW_FRAGILITY:{c.security_id}")
            if c.calibration < 0.45: triggers.append(f"COLLECT_FEEDBACK:{c.security_id}")
            if c.factor_overlap >= 0.75: triggers.append(f"REVIEW_FACTOR_OVERLAP:{c.security_id}")
        if unc >= 0.60: triggers.append("REDUCE_AGGREGATE_UNCERTAINTY")
        if not triggers: triggers.append("MONITOR_MATERIAL_STATE_CHANGES")
        cash_weight = round(max(0.0, 1.0 - total_target), 12)
        payload = {"candidates":[c.__dict__ for c in candidates],"max_weight":max_weight,"cash_floor":cash_floor,"min_weight":min_weight,"target":target}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return AllocationAssessment(tuple(sorted((k, round(v,12)) for k,v in score_map.items())), target, additions, reductions,
                                    round(exp,12), round(unc,12), round(diversification,12), tuple(triggers), cash_weight, lineage)
