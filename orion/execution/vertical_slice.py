from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from ..documents.ingest import DocumentIngestor
from ..evidence.ledger import EvidenceRecord
from ..financials.statement import StatementMapper
from ..research.orchestrator import ResearchOrchestrator
from ..data.providers import hash_payload
from ..learning.feedback import ForecastLedger, ForecastRecord, OutcomeRecord, FeedbackReport

@dataclass(frozen=True)
class Capture:
    source_id: str
    url: str
    security_id: str | None
    payload: bytes
    captured_at: str
    content_type: str

@dataclass(frozen=True)
class MarketObservation:
    security_id: str
    dataset: str
    event_time: str
    available_time: str
    source_id: str
    payload: object
    payload_hash: str
    captured_at: str

class ResearchExecution:
    """End-to-end deterministic acquisition -> PIT -> evidence -> research runtime."""
    def __init__(self, store, *, document_ingestor=None, mapper=None, orchestrator=None):
        self.store=store
        self.documents=document_ingestor or DocumentIngestor()
        self.mapper=mapper or StatementMapper()
        self.orchestrator=orchestrator or ResearchOrchestrator()
        self.feedback=ForecastLedger()
        self._hydrate_feedback()

    def capture(self, capture: Capture):
        if not capture.payload: raise ValueError('EMPTY_PAYLOAD')
        artifact=self.documents.ingest_bytes(capture.payload,capture.source_id,capture.security_id,capture.content_type,capture.captured_at)
        capture_id=sha256(f'{capture.source_id}|{capture.url}|{artifact.content_hash}'.encode()).hexdigest()
        self.store.source_capture(capture_id,capture.source_id,capture.url,artifact.content_hash,capture.captured_at,capture.content_type,artifact.byte_size)
        return artifact

    def ingest_market_observations(self, rows, *, decision_time: str):
        """Persist provider-normalized observations only after PIT temporal validation."""
        out=[]
        for r in rows:
            event_time=str(r['event_time']); available=str(r['available_time']); captured=str(r.get('captured_at',available))
            ph=str(r.get('payload_hash') or hash_payload(r))
            payload=dict(r)
            self.store.insert_observation(security_id=r['security_id'],dataset=r['dataset'],event_time=event_time,available_time=available,source_id=r['source_id'],payload_hash=ph,payload=payload,captured_at=captured)
            out.append(MarketObservation(r['security_id'],r['dataset'],event_time,available,r['source_id'],payload,ph,captured))
        return tuple(out)

    def ingest_text(self, artifact, text: str, available_time: str):
        chunks=self.documents.text_chunks(artifact,text,available_time)
        for c in chunks:
            claim=c.text[:500]
            eid=EvidenceRecord.id_for(c.document_id,c.locator,claim,c.content_hash)
            rec=EvidenceRecord(eid,c.security_id,artifact.source_id,c.document_id,c.locator,claim,None,c.confidence,c.available_time,c.content_hash)
            rec.validate()
            self.store.evidence(eid,rec.security_id or '',rec.source_id,rec.document_id,rec.locator,rec.claim,rec.extracted_value,rec.confidence,rec.available_time,rec.content_hash)
        return chunks

    def ingest_financial_facts(self, rows, decision_time: str):
        facts=[]
        for row in rows:
            fact=self.mapper.map_row(row); fact.validate(decision_time)
            self.store.normalized_financial({'security_id':fact.security_id,'metric':fact.metric,'period_end':fact.period_end,'value':fact.value,'unit':fact.unit,'currency':fact.currency,'source_id':fact.source_id,'available_time':fact.available_time})
            facts.append(fact)
        return tuple(facts)

    def _hydrate_feedback(self):
        from ..learning.feedback import ForecastRecord, OutcomeRecord
        forecasts=[]
        for r in self.store.forecasts_for_all():
            forecasts.append(ForecastRecord(
                r['forecast_id'],r['security_id'],r['event_key'],r['decision_time'],r['horizon_end'],
                float(r['probability']),tuple(json.loads(r['evidence_ids_json'])),r['thesis_fingerprint'],
                r['model_id'],r['created_at']))
        outcomes=[]
        for r in self.store.forecast_outcomes_for_all():
            outcomes.append(OutcomeRecord(r['forecast_id'],bool(r['occurred']),r['available_time'],
                r['source_id'],tuple(json.loads(r['evidence_ids_json'])),r['content_hash']))
        self.feedback.load(forecasts,outcomes)

    def record_forecast(self, forecast: ForecastRecord):
        self.feedback.issue(forecast)
        self.store.forecast(forecast)
        return forecast

    def resolve_forecast(self, outcome: OutcomeRecord, *, evaluation_time: str):
        score=self.feedback.resolve(outcome, evaluation_time=evaluation_time)
        self.store.forecast_outcome(outcome)
        return score

    def feedback_report(self, bins: int = 10) -> FeedbackReport:
        return self.feedback.report(bins=bins)

    def research(self, security_id: str, decision_time: str, opinions=(), blockers=()):
        rows=self.store.evidence_for(security_id,decision_time)
        evidence=[{'evidence_id':r['evidence_id'],'available_time':r['available_time'],'confidence':r['confidence'],'content_hash':r['content_hash']} for r in rows]
        market=self.store.pit(security_id,'ohlcv',decision_time)
        result=self.orchestrator.run(security_id,decision_time,evidence,opinions,blockers)
        self.store.thesis_state(result.thesis_state)
        return result, {'evidence_count':len(evidence),'market_observation_count':len(market)}
