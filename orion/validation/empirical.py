from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping, Sequence

from orion.learning.feedback import ForecastLedger, ForecastRecord, OutcomeRecord
from orion.learning.diagnostics import LearningDiagnosticsEngine
from orion.quant.safe_backtest import PITBacktest, BacktestResult


@dataclass(frozen=True)
class EmpiricalValidationReport:
    status: str
    forecast_report: Mapping[str, object]
    diagnostics: Mapping[str, object]
    backtest: BacktestResult
    leakage_rejections: int
    observations_used: int
    lineage_hash: str


class EmpiricalValidationLab:
    """Evidence-bound validation surface combining forecast and PIT backtest evidence.

    This class never creates observations. It only scores supplied historical/PIT
    inputs and makes look-ahead rejection visible as a first-class metric.
    """
    def __init__(self, backtest: PITBacktest | None = None):
        self.backtest = backtest or PITBacktest()
        self.diagnostics = LearningDiagnosticsEngine()

    def run(
        self,
        *,
        forecasts: Iterable[ForecastRecord] = (),
        outcomes: Iterable[OutcomeRecord] = (),
        backtest_rows: Sequence[Mapping[str, object]] = (),
        decision_time: str,
        evaluation_time: str | None = None,
        ledger: ForecastLedger | None = None,
    ) -> EmpiricalValidationReport:
        fs = tuple(forecasts)
        os = tuple(outcomes)
        ledger = ledger or ForecastLedger()
        for f in fs:
            ledger.issue(f)
        if os:
            eval_time = evaluation_time or decision_time
            for o in os:
                ledger.resolve(o, evaluation_time=eval_time)
        feedback = ledger.report()
        diagnostics = self.diagnostics.analyze(ledger.forecasts(), ledger.outcomes())
        bt = self.backtest.run(backtest_rows, decision_time)
        status = "READY" if (feedback.resolved > 0 or bt.observations_used > 0) else "NO_OBSERVED_HISTORY"
        payload = {
            "status": status,
            "feedback": feedback.__dict__,
            "diagnostics": diagnostics.__dict__,
            "backtest": bt.__dict__,
            "decision_time": decision_time,
            "evaluation_time": evaluation_time,
        }
        lineage = sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
        return EmpiricalValidationReport(
            status=status,
            forecast_report=payload["feedback"],
            diagnostics=payload["diagnostics"],
            backtest=bt,
            leakage_rejections=bt.rejected_lookahead,
            observations_used=bt.observations_used,
            lineage_hash=lineage,
        )
