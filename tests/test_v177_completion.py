from pathlib import Path
import sqlite3
from orion.learning.probabilistic import ForecastEvidence, ProbabilisticForecastEngine
from orion.execution.realistic import ExecutionCostModel, RealisticPaperCostEngine
from orion.learning.feedback import ForecastLedger
from orion.validation.empirical import EmpiricalValidationLab
from orion.app.gateway import RuntimeGateway

def test_probabilistic_forecast_is_bounded_and_lineaged():
    r=ProbabilisticForecastEngine().generate(base_rate=.50,evidence=[ForecastEvidence('e1',.8,.9),ForecastEvidence('e2',-.2,.5)])
    assert 0<r.probability<1
    assert 0<=r.uncertainty<=1
    assert len(r.lineage_hash)==64 and len(r.thesis_fingerprint)==64

def test_probabilistic_forecast_requires_real_evidence_contract():
    try: ProbabilisticForecastEngine().generate(base_rate=.5,evidence=[])
    except ValueError as e: assert str(e)=='FORECAST_REQUIRES_EVIDENCE'
    else: raise AssertionError('missing evidence accepted')

def test_realistic_paper_costs_are_explicit_and_deterministic():
    m=ExecutionCostModel(slippage_bps=5,impact_bps=2,brokerage_bps=1,exchange_bps=1,gst_bps=18,stt_bps_sell=10,sebi_bps=.01)
    a=RealisticPaperCostEngine().apply(quantity=100,reference_price=100,side='SELL',model=m)
    b=RealisticPaperCostEngine().apply(quantity=100,reference_price=100,side='SELL',model=m)
    assert a==b and a.total_cost>0 and a.execution_price<100
    assert len(a.lineage_hash)==64

def test_empirical_lab_accepts_past_resolved_outcome_with_explicit_evaluation_time():
    f=ForecastLedger.make_forecast(security_id='X',event_key='RET_1D',decision_time='2026-01-01T10:00:00Z',horizon_end='2026-01-02T10:00:00Z',probability=.7,evidence_ids=('e1',),thesis_fingerprint='t')
    o=__import__('orion.learning.feedback',fromlist=['OutcomeRecord']).OutcomeRecord(f.forecast_id,True,'2026-01-03T10:00:00Z','src',('e1',),'a'*64)
    r=EmpiricalValidationLab().run(forecasts=(f,),outcomes=(o,),decision_time=f.decision_time,evaluation_time='2026-01-03T10:00:00Z')
    assert r.forecast_report['resolved']==1

def test_gateway_exposes_new_code_completable_surfaces():
    from orion.app.gateway import RuntimeGateway
    g=RuntimeGateway()
    r=g.probabilistic_forecast(base_rate=.5,evidence=[{'evidence_id':'e1','signal':.2,'reliability':.8}])
    assert 0<r['probability']<1 and len(r['lineage_hash'])==64
    c=g.paper_cost(quantity=10,reference_price=100,side='BUY',model={'slippage_bps':5})
    assert c['total_cost']>0 and c['execution_price']>100

def test_server_has_new_post_routes():
    from pathlib import Path
    s=Path('orion/app/server.py').read_text()
    assert "/api/forecast/probabilistic" in s and "/api/paper/cost" in s
