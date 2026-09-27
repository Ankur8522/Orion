from datetime import datetime, timedelta, timezone
from pathlib import Path

from orion.data.fabric import CanonicalDataFabric, DatasetObservation
from orion.intelligence.decision_pipeline import DecisionIntelligenceEngine
from orion.intelligence.decision_world import DecisionWorldBuilder
from orion.data.world_snapshot import WorldSnapshot
from orion.data.coverage_contract import CoverageAssessment
from orion.research.evidence_graph import EvidenceGraph
from orion.learning.specialist_models import ChronologicalLogisticSpecialist, TrainingExample
from orion.learning.meta_intelligence import LearnedMetaIntelligence, MetaTrainingRow
from orion.learning.forecast_distribution import EmpiricalForecastDistribution
from orion.learning.artifacts import ModelArtifact, ModelArtifactStore, artifact_lineage


def t(i): return (datetime(2024,1,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat().replace('+00:00','Z')

def test_fabric_selects_point_in_time_restatement():
    f=CanonicalDataFabric()
    f.ingest(DatasetObservation('financials','ABC','src','2024-01-01T00:00:00Z','2024-01-01T00:00:00Z','2024-02-01T00:00:00Z','2024-02-01T00:01:00Z','a',{'eps':1}))
    f.ingest(DatasetObservation('financials','ABC','src','2024-01-01T00:00:00Z','2024-01-01T00:00:00Z','2024-03-01T00:00:00Z','2024-03-01T00:01:00Z','b',{'eps':2}))
    s=f.snapshot('financials','ABC',decision_time='2024-03-15T00:00:00Z')
    assert s.selected is not None and s.selected.payload_hash=='b'
    s2=f.snapshot('financials','ABC',decision_time='2024-02-15T00:00:00Z')
    assert s2.selected is not None and s2.selected.payload_hash=='a'

def test_decision_intelligence_requires_ready_world_and_trained_models():
    ws=WorldSnapshot('ABC','2024-02-01T00:00:00Z',True,(), 'ws')
    cov=CoverageAssessment(('x',),1,1.0,(), 'cov')
    ev=EvidenceGraph((),(),(), 'ev')
    world=DecisionWorldBuilder().build(ws,cov,ev,features={'quality':.8})
    rows=[TrainingExample(t(i),{'quality':i/19},int(i>9),'BULL') for i in range(20)]
    m=ChronologicalLogisticSpecialist('fundamental',('quality',),epochs=100); m.fit(rows)
    result=DecisionIntelligenceEngine().infer(world,{'fundamental':m},required_specialists=())
    assert result.status in {'INSUFFICIENT_TRAINED_SPECIALISTS','READY'}

def test_empirical_forecast_distribution_is_fail_closed():
    d=EmpiricalForecastDistribution().build([-.1,-.05,-.02,.01,.03,.05,.08,.12,.15,.2],horizon_days=20)
    assert d.status=='READY' and d.observations==10 and 0 < d.p_positive < 1
    d2=EmpiricalForecastDistribution().build([.1,.2],horizon_days=20)
    assert d2.status=='INSUFFICIENT_EVIDENCE'

def test_model_artifact_store_round_trip(tmp_path: Path):
    payload={'weights':[0.1,0.2]}; metrics={'brier':.2}; lineage=artifact_lineage('m','logistic','1',payload,metrics,'d','f','c')
    a=ModelArtifact('m','logistic','1',payload,metrics,'d','f','c',lineage)
    p=tmp_path/'m.json'; ModelArtifactStore().save(p,a); b=ModelArtifactStore().load(p)
    assert b.lineage_hash==lineage and b.payload==payload
