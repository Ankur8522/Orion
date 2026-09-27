from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Mapping, Sequence


def _clip(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        raise ValueError("NON_FINITE_FUNDAMENTAL_INPUT")
    if high == low:
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _quality_positive(value: float | None, low: float, high: float) -> float | None:
    return None if value is None else _clip(float(value), low, high)


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


@dataclass(frozen=True)
class FundamentalFeatureSnapshot:
    security_id: str
    as_of: str
    features: tuple[tuple[str, float], ...]
    diagnostics: tuple[tuple[str, float | str], ...]
    missing: tuple[str, ...]
    source_ids: tuple[str, ...]
    lineage_hash: str

    @property
    def mapping(self) -> dict[str, float]:
        return dict(self.features)


class FundamentalFeatureEngine:
    """Builds transparent normalized fundamental features from PIT-safe company facts.

    Inputs are derived metrics already reconciled by the data/financial layer. No
    market value or missing observation is invented. Thresholds are configuration,
    not claims of empirical superiority.
    """

    def build(self, security_id: str, *, as_of: str, latest: Mapping[str, object], history: Sequence[Mapping[str, object]] = (), source_ids: Sequence[str] = ()) -> FundamentalFeatureSnapshot:
        values = {k: (None if v is None else float(v)) for k, v in latest.items()}
        history_rows = tuple(history)
        features: dict[str, float] = {}
        diagnostics: dict[str, float | str] = {}
        missing: list[str] = []

        growth_keys = ("revenue_growth", "ebitda_growth", "pat_growth", "eps_growth", "fcf_growth")
        growth = [values[k] for k in growth_keys if values.get(k) is not None]
        if growth:
            # Bounded normalization: -20% to +40% is an explicit engineering range.
            features["earnings_growth"] = _mean([_clip(g, -0.20, 0.40) for g in growth]) or 0.5
            diagnostics["growth_observations"] = float(len(growth))
        else:
            missing.append("earnings_growth")

        quality_components = []
        for key, low, high in (("roe", -0.05, 0.30), ("roic_proxy", -0.05, 0.30), ("ebitda_margin", -0.10, 0.40), ("net_margin", -0.10, 0.30)):
            q = _quality_positive(values.get(key), low, high)
            if q is not None:
                quality_components.append(q)
        if quality_components:
            features["fundamental_quality"] = _mean(quality_components) or 0.5
        else:
            missing.append("fundamental_quality")

        cfo_pat = values.get("cfo_pat")
        fcf = values.get("fcf")
        pat = values.get("pat")
        cash_quality = []
        if cfo_pat is not None:
            cash_quality.append(_clip(cfo_pat, 0.40, 1.50))
        if fcf is not None and pat is not None and pat != 0:
            cash_quality.append(_clip(fcf / abs(pat), -1.0, 1.5))
        if cash_quality:
            features["cashflow_quality"] = _mean(cash_quality) or 0.5
        else:
            missing.append("cashflow_quality")

        valuation = []
        if values.get("pe") is not None and values["pe"] > 0:
            valuation.append(1.0 - _clip(values["pe"], 5.0, 80.0))
        if values.get("pb") is not None and values["pb"] > 0:
            valuation.append(1.0 - _clip(values["pb"], 0.5, 12.0))
        if values.get("ev_ebitda") is not None and values["ev_ebitda"] > 0:
            valuation.append(1.0 - _clip(values["ev_ebitda"], 4.0, 50.0))
        if values.get("earnings_yield") is not None:
            valuation.append(_clip(values["earnings_yield"], -0.02, 0.15))
        if values.get("fcf_yield") is not None:
            valuation.append(_clip(values["fcf_yield"], -0.02, 0.15))
        if valuation:
            features["valuation_attractiveness"] = _mean(valuation) or 0.5
        else:
            missing.append("valuation_attractiveness")

        debt_quality = []
        if values.get("debt_ebitda") is not None:
            debt_quality.append(1.0 - _clip(values["debt_ebitda"], 0.0, 8.0))
        if values.get("net_debt") is not None and values.get("ebitda") not in (None, 0):
            debt_quality.append(1.0 - _clip(values["net_debt"] / values["ebitda"], -3.0, 8.0))
        features["risk_quality"] = _mean(debt_quality) if debt_quality else 0.5
        if not debt_quality:
            diagnostics["risk_quality_status"] = "LIMITED_BALANCE_SHEET_EVIDENCE"

        # Business visibility and forensic quality are deliberately conservative:
        # absence is missing, not positive evidence.
        if values.get("order_book_to_revenue") is not None:
            features["business_visibility"] = _clip(values["order_book_to_revenue"], 0.0, 5.0)
        else:
            missing.append("business_visibility")
        forensic = []
        if cfo_pat is not None:
            forensic.append(_clip(cfo_pat, 0.0, 1.5))
        if values.get("receivables_to_revenue") is not None:
            forensic.append(1.0 - _clip(values["receivables_to_revenue"], 0.0, 0.60))
        if values.get("debt_ebitda") is not None:
            forensic.append(1.0 - _clip(values["debt_ebitda"], 0.0, 8.0))
        if forensic:
            features["forensic_quality"] = _mean(forensic) or 0.5
        else:
            missing.append("forensic_quality")

        diagnostics["history_periods"] = float(len(history_rows))
        payload = {"security_id": security_id, "as_of": as_of, "features": sorted(features.items()), "diagnostics": sorted(diagnostics.items()), "missing": sorted(set(missing)), "source_ids": sorted(set(source_ids))}
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        return FundamentalFeatureSnapshot(security_id, as_of, tuple(sorted(features.items())), tuple(sorted(diagnostics.items())), tuple(sorted(set(missing))), tuple(sorted(set(source_ids))), lineage)
