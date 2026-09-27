from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Mapping, Sequence

from ..data.time import parse_utc


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value))))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    out = _mean(values[:period])
    for value in values[period:]:
        out = alpha * value + (1.0 - alpha) * out
    return out


def _rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for a, b in zip(values[-(period + 1):-1], values[-period:]):
        delta = b - a
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = _mean(gains)
    avg_loss = _mean(losses)
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(rows: Sequence[Mapping[str, object]], period: int = 14) -> float | None:
    if len(rows) <= period:
        return None
    trs: list[float] = []
    previous_close: float | None = None
    for row in rows:
        high = row.get("high")
        low = row.get("low")
        close = row.get("close")
        if high is None or low is None or close is None:
            continue
        h, l, c = float(high), float(low), float(close)
        if h < l or c < 0:
            raise ValueError("INVALID_OHLC")
        tr = h - l if previous_close is None else max(h - l, abs(h - previous_close), abs(l - previous_close))
        trs.append(tr)
        previous_close = c
    return _mean(trs[-period:]) if len(trs) >= period else None


def _realized_vol(values: Sequence[float], period: int = 20) -> float | None:
    if len(values) <= period:
        return None
    returns = [values[i] / values[i - 1] - 1.0 for i in range(1, len(values)) if values[i - 1] > 0]
    returns = returns[-period:]
    if len(returns) < period:
        return None
    mean = _mean(returns)
    return math.sqrt(_mean([(x - mean) ** 2 for x in returns])) * math.sqrt(252.0)


@dataclass(frozen=True)
class TechnicalFeatureSnapshot:
    security_id: str
    as_of: str
    features: tuple[tuple[str, float], ...]
    diagnostics: tuple[tuple[str, float | str | bool], ...]
    missing: tuple[str, ...]
    source_ids: tuple[str, ...]
    lineage_hash: str

    @property
    def mapping(self) -> dict[str, float]:
        return dict(self.features)


class TechnicalFeatureEngine:
    """Derives PIT-safe normalized technical features from supplied OHLCV rows.

    The engine never fetches data. Rows are rejected when event/available timestamps
    violate the requested decision boundary. Missing history remains missing; it is
    never converted into a neutral synthetic feature.
    """

    def build(self, security_id: str, rows: Sequence[Mapping[str, object]], *, as_of: str, source_ids: Sequence[str] = ()) -> TechnicalFeatureSnapshot:
        decision = parse_utc(as_of)
        normalized = []
        seen: set[str] = set()
        for row in rows:
            event_time = str(row.get("event_time", ""))
            available_time = str(row.get("available_time", event_time))
            if not event_time:
                raise ValueError("MISSING_EVENT_TIME")
            event_dt = parse_utc(event_time)
            available_dt = parse_utc(available_time)
            if event_dt > decision or available_dt > decision:
                raise ValueError("FUTURE_TECHNICAL_OBSERVATION")
            if available_dt < event_dt:
                raise ValueError("INVALID_TECHNICAL_TIME_ORDER")
            if event_time in seen:
                raise ValueError("DUPLICATE_TECHNICAL_EVENT_TIME")
            seen.add(event_time)
            if row.get("close") is not None and float(row["close"]) <= 0:
                raise ValueError("INVALID_CLOSE")
            if row.get("volume") is not None and float(row["volume"]) < 0:
                raise ValueError("INVALID_VOLUME")
            normalized.append(dict(row))
        normalized.sort(key=lambda r: str(r["event_time"]))
        closes = [float(r["close"]) for r in normalized if r.get("close") is not None]
        volumes = [float(r["volume"]) for r in normalized if r.get("volume") is not None]
        features: dict[str, float] = {}
        diagnostics: dict[str, float | str | bool] = {"observations": float(len(normalized)), "close_observations": float(len(closes))}
        missing: list[str] = []
        last = closes[-1] if closes else None

        sma20 = _mean(closes[-20:]) if len(closes) >= 20 else None
        sma50 = _mean(closes[-50:]) if len(closes) >= 50 else None
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        rsi14 = _rsi(closes, 14)
        atr14 = _atr(normalized, 14)
        rv20 = _realized_vol(closes, 20)

        if last is not None and sma20 is not None:
            distance20 = last / sma20 - 1.0
            trend20 = _sigmoid(distance20 / 0.08)
            features["technical_trend"] = trend20
            diagnostics["distance_sma20"] = distance20
        else:
            missing.append("technical_trend")

        if last is not None and sma50 is not None:
            diagnostics["distance_sma50"] = last / sma50 - 1.0
            diagnostics["sma20_vs_sma50"] = (sma20 / sma50 - 1.0) if sma20 else 0.0
        if rsi14 is not None and len(closes) >= 21:
            roc20 = last / closes[-21] - 1.0
            macd_hist = 0.0
            if ema12 is not None and ema26 is not None:
                macd_hist = (ema12 - ema26) / last
            momentum = 0.45 * _sigmoid(roc20 / 0.10) + 0.35 * _sigmoid(macd_hist / 0.025) + 0.20 * _clip01(rsi14 / 100.0)
            features["technical_momentum"] = _clip01(momentum)
            diagnostics["rsi14"] = rsi14
            diagnostics["roc20"] = roc20
            diagnostics["macd_hist_norm"] = macd_hist
        else:
            missing.append("technical_momentum")

        if len(volumes) >= 21:
            avg_volume = _mean(volumes[-21:-1])
            ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
            features["volume_confirmation"] = _clip01(_sigmoid((ratio - 1.0) / 0.45))
            diagnostics["relative_volume20"] = ratio
        else:
            missing.append("volume_confirmation")

        if len(closes) >= 21:
            prior_high = max(closes[-21:-1])
            breakout_distance = (last - prior_high) / prior_high if prior_high > 0 else 0.0
            breakout = _sigmoid(breakout_distance / 0.025)
            if len(volumes) >= 21 and _mean(volumes[-21:-1]) > 0:
                breakout *= _clip01(_sigmoid(((volumes[-1] / _mean(volumes[-21:-1])) - 1.0) / 0.35))
            features["breakout_quality"] = _clip01(breakout)
            diagnostics["prior_high20"] = prior_high
            diagnostics["breakout_distance"] = breakout_distance
        else:
            missing.append("breakout_quality")

        if atr14 is not None and last is not None and last > 0:
            diagnostics["atr14_pct"] = atr14 / last
        else:
            diagnostics["atr14_pct"] = "INSUFFICIENT_HISTORY"
        if rv20 is not None:
            diagnostics["realized_vol20"] = rv20
        else:
            diagnostics["realized_vol20"] = "INSUFFICIENT_HISTORY"

        payload = {
            "security_id": security_id,
            "as_of": as_of,
            "features": sorted(features.items()),
            "diagnostics": sorted(diagnostics.items()),
            "missing": sorted(set(missing)),
            "source_ids": sorted(set(source_ids)),
        }
        lineage = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        return TechnicalFeatureSnapshot(
            security_id,
            as_of,
            tuple(sorted(features.items())),
            tuple(sorted(diagnostics.items())),
            tuple(sorted(set(missing))),
            tuple(sorted(set(source_ids))),
            lineage,
        )
