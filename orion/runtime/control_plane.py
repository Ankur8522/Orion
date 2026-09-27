from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from orion.app.service import OrionService, ServiceRun
from orion.brain.kernel import IntelligenceCase, InvestmentIntelligenceKernel
from orion.brain.persistence import PersistentProgressiveMemory
from orion.ops.journal import RunJournal
from orion.ops.observability import AuditLogger, Metrics
from orion.execution.persistent import PersistentPaperExecutionBook
from orion.runtime.state_store import RuntimeStateStore
from orion.runtime.persistent_queue import PersistentResearchQueue
from orion.learning.persistence import PersistentForecastLedger
from orion.learning.model_registry import ChampionChallengerRegistry
from orion.ops.time_machine import TimeMachine
from orion.institutional.operating_cycle import InstitutionalOperatingCycle


@dataclass(frozen=True)
class RuntimeResult:
    service_run: ServiceRun
    journal_hash: str
    health: dict


class OrionControlPlane:
    """Production-shaped control plane over ORION's research-to-paper spine.

    It owns lifecycle concerns—durable brain memory, audit journal, metrics and
    paper execution—while domain engines remain responsible for their decisions.
    """

    def __init__(self, *, state_path: str | Path = ":memory:", journal_path: str | Path = ":memory:", paper_path: str | Path = ":memory:", forecast_path: str | Path | None = None, model_path: str | Path | None = None, replay_path: str | Path | None = None):
        memory = PersistentProgressiveMemory(state_path)
        kernel = InvestmentIntelligenceKernel()
        kernel.progressive_memory = memory
        kernel.progressive_loop.memory = memory
        root = Path(state_path).parent if str(state_path) != ":memory:" else Path(".")
        forecast_path = forecast_path or (root / "forecasts.sqlite" if str(state_path) != ":memory:" else ":memory:")
        model_path = model_path or (root / "models.sqlite" if str(state_path) != ":memory:" else ":memory:")
        replay_path = replay_path or (root / "time_machine.jsonl" if str(state_path) != ":memory:" else ":memory:")
        kernel.forecast_ledger = PersistentForecastLedger(forecast_path)
        kernel.model_registry = ChampionChallengerRegistry(path=model_path)
        kernel.time_machine = TimeMachine(replay_path)
        self.service = OrionService(kernel, paper=PersistentPaperExecutionBook(paper_path))
        self.journal = RunJournal(journal_path)
        self.metrics = Metrics()
        self.audit = AuditLogger()
        self.state_store = RuntimeStateStore(state_path if str(state_path) != ":memory:" else ":memory:")
        queue_path = str(Path(state_path).with_name("research_queue.sqlite")) if str(state_path) != ":memory:" else ":memory:"
        self.research_queue = PersistentResearchQueue(queue_path)
        self.institutional_cycle = InstitutionalOperatingCycle(time_machine=kernel.time_machine)
        self._forecast_path = str(forecast_path); self._model_path = str(model_path); self._replay_path = str(replay_path)

    def run_case(self, case: IntelligenceCase) -> RuntimeResult:
        self.metrics.inc("intelligence_runs")
        result = self.service.analyze(case)
        self.state_store.cycle_start(case.cycle_id, case.decision_time, {"security_id": case.security_id})
        event = self.journal.append("INTELLIGENCE_RUN", {
            "security_id": case.security_id,
            "cycle_id": case.cycle_id,
            "run_hash": result.intelligence.run_hash,
            "decision": result.intelligence.decision.state.value,
            "progressive_phase": result.intelligence.progressive_cycle.phase.value,
            "paper_orders": len(result.paper_orders),
        })
        self.audit.emit("orion", "INTELLIGENCE_RUN", case.security_id,
                        cycle_id=case.cycle_id, run_hash=result.intelligence.run_hash)
        self.metrics.gauge("progressive_belief", result.intelligence.progressive.belief)
        self.metrics.gauge("progressive_uncertainty", result.intelligence.progressive.uncertainty)
        self.metrics.gauge("progressive_fragility", result.intelligence.progressive.fragility)
        self.state_store.cycle_finish(case.cycle_id, case.decision_time, "COMPLETE", {"run_hash": result.intelligence.run_hash, "decision": result.intelligence.decision.state.value})
        # Persist a deterministic, point-in-time operating snapshot for replay.
        snapshot_id = f"{case.cycle_id}:{result.intelligence.run_hash[:12]}"
        self.service.kernel.time_machine.record(snapshot_id, case.decision_time, {
            "security_id": case.security_id, "cycle_id": case.cycle_id,
            "decision": result.intelligence.decision.state.value,
            "run_hash": result.intelligence.run_hash,
            "progressive": {"phase": result.intelligence.progressive_cycle.phase.value, "belief": result.intelligence.progressive.belief,
                            "uncertainty": result.intelligence.progressive.uncertainty, "fragility": result.intelligence.progressive.fragility,
                            "robustness": result.intelligence.progressive.robustness},
            "risk_blocked": result.intelligence.risk_gate.blocked,
            "allocation": result.intelligence.allocation.target_weights if result.intelligence.allocation else {},
        })
        return RuntimeResult(result, event.event_hash, self.health())

    def issue_forecast(self, forecast):
        return self.service.kernel.forecast_ledger.issue(forecast)

    def resolve_forecasts(self, observations, evaluation_time: str):
        from orion.learning.outcome_resolver import ForecastOutcomeResolver
        return ForecastOutcomeResolver().resolve(self.service.kernel.forecast_ledger, observations, evaluation_time=evaluation_time)

    def learning_report(self):
        return self.service.kernel.forecast_ledger.report()

    def replay(self, start_cycle=None, end_cycle=None):
        return self.service.kernel.time_machine.replay(start_cycle=start_cycle, end_cycle=end_cycle)


    def feedback_cycle(self, *, memberships, observations, evaluation_time, model_scores=(), attribution_rows=(), nav_rows=(), state=None):
        """Run the bounded cross-domain feedback cycle over durable domain stores."""
        report = self.institutional_cycle.run(
            memberships=memberships,
            ledger=self.service.kernel.forecast_ledger,
            observations=observations,
            evaluation_time=evaluation_time,
            model_registry=self.service.kernel.model_registry,
            model_scores=model_scores,
            attribution_rows=attribution_rows,
            nav_rows=nav_rows,
            state=state,
        )
        self.metrics.inc("feedback_cycles")
        self.state_store.event(evaluation_time, "FEEDBACK_CYCLE", {"status": report.status, "resolved_forecasts": report.resolved_forecasts, "universe_coverage_pct": report.universe.coverage_pct})
        return report

    def close(self):
        for obj in (self.service.kernel.progressive_memory, self.service.kernel.forecast_ledger, self.service.kernel.model_registry, self.service.kernel.time_machine, self.service.paper):
            close = getattr(obj, "close", None)
            if callable(close):
                close()
        self.journal.close()
        self.state_store.close()
        self.research_queue._db.close()

    def health(self) -> dict:
        return {
            "status": "OK" if self.journal.verify() and not self.service.paper.live_trading_enabled() else "DEGRADED",
            "journal_integrity": self.journal.verify(),
            "live_trading_enabled": self.service.paper.live_trading_enabled(),
            "journal_events": len(self.journal.events()),
            "metrics": self.metrics.snapshot(),
            "cycles": self.state_store.cycles(limit=20),
            "alerts": self.state_store.alerts(limit=20),
            "research_jobs": len(self.research_queue.jobs()),
            "active_research_jobs": sum(j.status.value == "RUNNING" for j in self.research_queue.jobs()),
            "forecast_records": len(self.service.kernel.forecast_ledger.forecasts()),
            "resolved_forecasts": len(self.service.kernel.forecast_ledger.outcomes()),
            "champion_model": self.service.kernel.model_registry.champion,
            "replay_snapshots": len(self.service.kernel.time_machine.snapshots()),
        }
