from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from orion.brain.progressive import ProgressiveAssessment, Regime
from orion.brain.progressive_loop import ProgressiveMemory, ProgressiveMemoryState, ReasoningPhase


class PersistentProgressiveMemory(ProgressiveMemory):
    """SQLite-backed append-only thesis memory.

    The in-memory progressive brain remains the reasoning authority; this adapter
    makes its state survive process restarts without changing the reasoning rules.
    """

    def __init__(self, path: str | Path = ":memory:"):
        super().__init__()
        self.path = str(path)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS progressive_memory (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                thesis_id TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                payload TEXT NOT NULL
            )"""
        )
        self._db.commit()
        self._hydrate()

    @staticmethod
    def _encode(state: ProgressiveMemoryState) -> dict:
        return {
            "thesis_id": state.thesis_id,
            "cycle_id": state.cycle_id,
            "phase": state.phase.value,
            "assessment": {
                "thesis_id": state.assessment.thesis_id,
                "regime": state.assessment.regime.value,
                "belief": state.assessment.belief,
                "uncertainty": state.assessment.uncertainty,
                "robustness": state.assessment.robustness,
                "fragility": state.assessment.fragility,
                "challenge_score": state.assessment.challenge_score,
                "scenario_score": state.assessment.scenario_score,
                "calibration_score": state.assessment.calibration_score,
                "confidence_band": state.assessment.confidence_band,
                "next_checks": list(state.assessment.next_checks),
                "lineage_hash": state.assessment.lineage_hash,
            },
            "belief_delta": state.belief_delta,
            "uncertainty_delta": state.uncertainty_delta,
            "robustness_delta": state.robustness_delta,
            "fragility_delta": state.fragility_delta,
            "evidence_delta": state.evidence_delta,
            "scenario_delta": state.scenario_delta,
            "challenge_delta": state.challenge_delta,
            "feedback_quality": state.feedback_quality,
            "next_actions": list(state.next_actions),
            "lineage_hash": state.lineage_hash,
        }

    @staticmethod
    def _decode(payload: dict) -> ProgressiveMemoryState:
        a = payload["assessment"]
        assessment = ProgressiveAssessment(
            a["thesis_id"], Regime(a["regime"]), a["belief"], a["uncertainty"],
            a["robustness"], a["fragility"], a["challenge_score"], a["scenario_score"],
            a["calibration_score"], a["confidence_band"], tuple(a["next_checks"]), a["lineage_hash"]
        )
        return ProgressiveMemoryState(
            payload["thesis_id"], payload["cycle_id"], ReasoningPhase(payload["phase"]),
            assessment, payload["belief_delta"], payload["uncertainty_delta"],
            payload["robustness_delta"], payload["fragility_delta"], payload["evidence_delta"],
            payload["scenario_delta"], payload["challenge_delta"], payload["feedback_quality"],
            tuple(payload["next_actions"]), payload["lineage_hash"]
        )

    def _hydrate(self) -> None:
        rows = self._db.execute("SELECT payload FROM progressive_memory ORDER BY seq").fetchall()
        for (payload,) in rows:
            super().append(self._decode(json.loads(payload)))

    def append(self, state: ProgressiveMemoryState) -> ProgressiveMemoryState:
        payload = json.dumps(self._encode(state), sort_keys=True, separators=(",", ":"))
        self._db.execute(
            "INSERT INTO progressive_memory(thesis_id,cycle_id,payload) VALUES(?,?,?)",
            (state.thesis_id, state.cycle_id, payload),
        )
        self._db.commit()
        return super().append(state)

    def close(self) -> None:
        self._db.close()
