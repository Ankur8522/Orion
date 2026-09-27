from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence


def _clip(p: float) -> float:
    return max(1e-6, min(1.0 - 1e-6, float(p)))


@dataclass(frozen=True)
class CalibrationPoint:
    prediction: float
    outcome: int
    available_time: str


@dataclass(frozen=True)
class CalibrationModel:
    status: str
    breakpoints: tuple[float, ...]
    fitted: tuple[float, ...]
    observations: int
    lineage_hash: str

    def transform(self, probability: float) -> float:
        if self.status != "READY" or not self.breakpoints:
            return _clip(probability)
        p = _clip(probability)
        for i, bp in enumerate(self.breakpoints):
            if p <= bp:
                return _clip(self.fitted[i])
        return _clip(self.fitted[-1])


class IsotonicCalibrationEngine:
    """Small dependency-free isotonic calibrator using PAVA.

    Calibration observations must be out-of-sample predictions with outcomes already
    verified as available. The caller owns PIT/outcome validation; this layer never
    creates observations or future outcomes.
    """

    def fit(self, points: Sequence[CalibrationPoint], *, min_observations: int = 20) -> CalibrationModel:
        if min_observations < 2:
            raise ValueError("INVALID_CALIBRATION_MINIMUM")
        rows = sorted(points, key=lambda p: (p.available_time, p.prediction))
        if len(rows) < min_observations:
            payload = {"status": "INSUFFICIENT_CALIBRATION_HISTORY", "observations": len(rows)}
            return CalibrationModel("INSUFFICIENT_CALIBRATION_HISTORY", (), (), len(rows), sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
        if any(p.outcome not in (0, 1) or not 0 <= float(p.prediction) <= 1 for p in rows):
            raise ValueError("INVALID_CALIBRATION_POINT")

        # PAVA over individual observations; tied predictions are aggregated after fitting.
        blocks: list[list[float]] = []
        counts: list[int] = []
        for point in sorted(rows, key=lambda p: p.prediction):
            blocks.append([float(point.outcome)])
            counts.append(1)
            while len(blocks) >= 2:
                left = sum(blocks[-2]) / counts[-2]
                right = sum(blocks[-1]) / counts[-1]
                if left <= right:
                    break
                blocks[-2].extend(blocks[-1])
                counts[-2] += counts[-1]
                blocks.pop()
                counts.pop()
        fitted = [sum(block) / len(block) for block in blocks]
        # Map each block to the largest prediction it contains.
        ordered = sorted(rows, key=lambda p: p.prediction)
        breakpoints=[]
        idx=0
        for count in counts:
            idx += count
            breakpoints.append(float(ordered[idx-1].prediction))
        payload={"status":"READY","observations":len(rows),"breakpoints":breakpoints,"fitted":fitted}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return CalibrationModel("READY",tuple(breakpoints),tuple(fitted),len(rows),lineage)
