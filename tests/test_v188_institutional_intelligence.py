from datetime import datetime, timedelta, timezone

from orion.data.fabric import CanonicalDataFabric, DatasetObservation, DatasetState
from orion.learning.specialist_models import ChronologicalLogisticSpecialist, TrainingExample
from orion.learning.meta_intelligence import LearnedMetaIntelligence, MetaTrainingRow
from orion.decision.specialists import DEFAULT_SPECIALISTS, specialist_feature_union
from orion.decision.trade_ensemble import TradeIntelligenceEnsemble, SpecialistOutput


def ts(i):
    return (datetime(2024,1,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat().replace('+00:00','Z')


def test_catalog_has_fifteen_specialists():
    assert len(DEFAULT_SPECIALISTS) == 15
    assert len(specialist_feature_union()) > 30


def test_data_fabric_rejects_future_and_marks_stale():
    f=CanonicalDataFabric()
    f.ingest(DatasetObservation('ohlcv','ABC','p','2024-01-01T00:00:00Z','2024-01-01T00:00:00Z','2024-01-01T00:01:00Z','2024-01-01T00:02:00Z','h',{'close':1}))
    try:
        f.ingest(DatasetObservation('ohlcv','ABC','p',None,None,'2024-02-01T00:00:00Z','2024-02-01T00:01:00Z','future',{}), decision_time='2024-01-15T00:00:00Z')
        assert False
    except ValueError as e:
        assert str(e) == 'FUTURE_OBSERVATION'
    snap=f.snapshot('ohlcv','ABC',decision_time='2024-02-01T00:00:00Z',max_age_seconds=1)
    assert snap.state is DatasetState.STALE


def test_chronological_specialist_trains_and_scores_oos():
    rows=[]
    for i in range(20):
        x=i/19
        rows.append(TrainingExample(ts(i), {'quality':x}, 1 if x>.5 else 0, 'BULL' if i%2 else 'BEAR'))
    m=ChronologicalLogisticSpecialist('fundamental-v1',('quality',),epochs=250)
    metrics=m.fit(rows)
    assert metrics.trained and metrics.validation_observations > 0
    pred=m.predict({'quality':.9}, regime='BULL')
    assert pred and 0 < pred.probability < 1
    assert pred.metrics.brier is not None


def test_meta_intelligence_learns_specialist_trust_and_ensemble_uses_it():
    rows=[]
    for i in range(24):
        a=.8 if i%3 else .2
        b=.55
        y=1 if a>.5 else 0
        rows.append(MetaTrainingRow(ts(i), {'fundamental':a,'technical':b}, y, 'BULL'))
    meta=LearnedMetaIntelligence(epochs=250)
    metrics=meta.fit(rows)
    assert metrics.trained and metrics.brier is not None
    ensemble=TradeIntelligenceEnsemble(meta_model=meta, min_specialists=2)
    out=ensemble.combine((
        SpecialistOutput('fundamental',.85,30,'fund-v1',True,.1,.05,3,1.0),
        SpecialistOutput('technical',.55,30,'tech-v1',True,.2,.08,3,1.0),
    ))
    assert out.status=='READY'
    assert out.probability is not None
