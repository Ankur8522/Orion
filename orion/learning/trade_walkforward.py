from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence

from ..decision.trade_intelligence import TradeIntelligenceEngine, TradeTrainingRow, FEATURES
from .calibration import CalibrationPoint, CalibrationModel
from ..data.time import parse_utc


@dataclass(frozen=True)
class WalkForwardReport:
    model_id: str
    status: str
    train_rows: int
    calibration_rows: int
    test_rows: int
    train_brier: float | None
    calibration_brier: float | None
    test_brier: float | None
    calibration_status: str
    train_end: str | None
    calibration_end: str | None
    test_end: str | None
    lineage_hash: str


class TradeWalkForwardTrainer:
    """Chronological train -> calibration -> untouched test workflow.

    No shuffling. Outcomes used for fitting must have been available by the end of
    the fitting period. Calibration is fitted only on the middle period and test is
    never used to tune coefficients or calibration.
    """

    def run(self, engine: TradeIntelligenceEngine, rows: Sequence[TradeTrainingRow], *, train_fraction: float = 0.60, calibration_fraction: float = 0.20, min_train_rows: int = 12, min_calibration_rows: int = 20, min_test_rows: int = 8) -> WalkForwardReport:
        if not 0 < train_fraction < 1 or not 0 < calibration_fraction < 1 or train_fraction + calibration_fraction >= 1:
            raise ValueError("INVALID_WALK_FORWARD_SPLIT")
        ordered = sorted(rows, key=lambda r: (parse_utc(r.as_of), r.security_id))
        n=len(ordered)
        if n < min_train_rows + min_calibration_rows + min_test_rows:
            raise ValueError("INSUFFICIENT_WALK_FORWARD_ROWS")
        train_end=max(min_train_rows, int(n*train_fraction))
        cal_end=max(train_end+min_calibration_rows, int(n*(train_fraction+calibration_fraction)))
        if cal_end >= n-min_test_rows:
            cal_end=n-min_test_rows
        train=ordered[:train_end]; calibration=ordered[train_end:cal_end]; test=ordered[cal_end:]
        train_cutoff=calibration[0].as_of
        fit_rows=[r for r in train if not r.outcome_available_time or parse_utc(r.outcome_available_time) <= parse_utc(train_cutoff)]
        if len(fit_rows) < min_train_rows:
            return self._empty(engine, train, calibration, test, "INSUFFICIENT_RESOLVED_TRAINING_HISTORY")
        report=engine.fit(fit_rows, validation_fraction=0.20, training_cutoff=train_cutoff)
        calibration_points=[]
        for row in calibration:
            if row.outcome_available_time and parse_utc(row.outcome_available_time) > parse_utc(cal_end_time:=calibration[-1].as_of):
                continue
            vector=engine.build_features(row.security_id,row.as_of,context=row.features)
            raw=engine.score(vector, minimum_completeness=1.0).probability
            calibration_points.append(CalibrationPoint(raw,row.outcome,row.outcome_available_time or row.as_of))
        calibration_model=engine.calibrate(calibration_points,min_observations=min_calibration_rows)
        calibration_brier=self._brier(engine, calibration, calibration_model)
        test_brier=self._brier(engine, test, calibration_model)
        payload={"model_id":engine.model_id,"train":len(fit_rows),"calibration":len(calibration),"test":len(test),"calibration_status":calibration_model.status,"train_brier":report.train_brier,"calibration_brier":calibration_brier,"test_brier":test_brier,"periods":[train[-1].as_of,calibration[-1].as_of,test[-1].as_of]}
        lineage=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        status="READY" if calibration_model.status=="READY" and test_brier is not None else "INSUFFICIENT_CALIBRATION_HISTORY"
        return WalkForwardReport(engine.model_id,status,len(fit_rows),len(calibration),len(test),report.train_brier,calibration_brier,test_brier,calibration_model.status,train[-1].as_of,calibration[-1].as_of,test[-1].as_of,lineage)

    @staticmethod
    def _brier(engine, rows, calibration: CalibrationModel):
        if not rows:
            return None
        total=0.0
        for row in rows:
            vector=engine.build_features(row.security_id,row.as_of,context=row.features)
            score=engine.score(vector,minimum_completeness=1.0)
            p=calibration.transform(score.probability)
            total+=(p-row.outcome)**2
        return round(total/len(rows),12)

    @staticmethod
    def _empty(engine, train, calibration, test, status):
        return WalkForwardReport(engine.model_id,status,len(train),len(calibration),len(test),None,None,None,"INSUFFICIENT_CALIBRATION_HISTORY",train[-1].as_of if train else None,calibration[-1].as_of if calibration else None,test[-1].as_of if test else None,"")
