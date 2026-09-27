from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from .providers import ProviderObservation, validate_observation
from .reconcile import Reconciliation, Reconciler

@dataclass(frozen=True)
class IntegrityReport:
    dataset: str
    security_id: str
    observations: int
    validation_status: str
    reconciliation_status: str
    selected_provider: str | None
    disagreement: bool
    status: str

class DataIntegrityPipeline:
    """One governed validation/reconciliation boundary for provider observations.

    It never chooses a provider when observations disagree and never mutates the
    PIT store with unvalidated observations. Persisting the actual value remains
    the responsibility of the normalized/PIT ingestion layer.
    """
    def __init__(self, reconciler: Reconciler | None = None):
        self.reconciler = reconciler or Reconciler()

    def validate_and_reconcile(self, observations: Sequence[ProviderObservation], *, strict: bool = True) -> IntegrityReport:
        if not observations:
            raise ValueError("NO_OBSERVATIONS")
        for obs in observations:
            validate_observation(obs, strict=strict)
        rec: Reconciliation = self.reconciler.reconcile(observations)
        status = "PASS" if rec.status == "AGREED" else "REVIEW"
        return IntegrityReport(rec.dataset, rec.security_id, len(observations), "VALID", rec.status, rec.selected_provider, rec.disagreement, status)
