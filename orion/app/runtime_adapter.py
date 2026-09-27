"""
ORION UI runtime adapter.
The UI is intentionally decoupled from the core API. In production, serve
ui/index.html and connect these JSON shapes to an authenticated HTTP gateway.
Demo mode is explicit in the frontend and never represents demo values as live.
"""
from dataclasses import asdict
from typing import Any

def allocation_to_ui(assessment: Any) -> dict:
    return {
        "scores": dict(assessment.scores),
        "target_weights": dict(assessment.target_weights),
        "max_additions": dict(assessment.max_additions),
        "max_reductions": dict(assessment.max_reductions),
        "portfolio_expected_return": assessment.portfolio_expected_return,
        "portfolio_uncertainty": assessment.portfolio_uncertainty,
        "diversification_score": assessment.diversification_score,
        "adaptive_triggers": list(assessment.adaptive_triggers),
        "lineage_hash": assessment.lineage_hash,
    }

def health_payload() -> dict:
    return {"status":"ready","data_mode":"runtime","evidence":"PIT-protected","trading":"disabled-by-design"}
