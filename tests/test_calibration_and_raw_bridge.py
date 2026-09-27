from orion.decision.trade_intelligence import TradeIntelligenceEngine
from orion.learning.calibration import CalibrationPoint, IsotonicCalibrationEngine


def _market(n=70):
    rows=[]
    for i in range(n):
        month=i//28+1; day=i%28+1
        ts=f"2026-{month:02d}-{day:02d}T00:00:00Z"
        rows.append({"event_time":ts,"available_time":f"2026-{month:02d}-{day:02d}T01:00:00Z","open":100+i*0.5,"high":101+i*0.5,"low":99+i*0.5,"close":100+i*0.5,"volume":1000+i})
    return rows


def test_raw_bridge_derives_features_without_fabrication():
    e=TradeIntelligenceEngine()
    v=e.build_from_raw(
        "X","2026-03-15T00:00:00Z",
        fundamental_latest={"revenue_growth":0.2,"pat_growth":0.25,"roe":0.18,"roic_proxy":0.16,"ebitda_margin":0.22,"net_margin":0.12,"cfo_pat":1.05,"fcf":100,"pat":120,"pe":18,"pb":3,"ev_ebitda":12,"debt_ebitda":1.2,"net_debt":120,"ebitda":100},
        market_rows=_market(),
        historical_features={"historical_setup":0.8},
        context_features={"catalyst_strength":0.7,"business_visibility":0.8,"forensic_quality":0.8,"regime_fit":0.8,"risk_quality":0.8},
        source_ids=["fixture"],
    )
    assert v.completeness >= 0.7
    assert "technical_trend" in v.mapping
    assert "fundamental_quality" in v.mapping


def test_isotonic_calibration_requires_real_observation_count():
    points=[CalibrationPoint(0.1,0,"2026-01-01T00:00:00Z"),CalibrationPoint(0.9,1,"2026-01-02T00:00:00Z")]
    model=IsotonicCalibrationEngine().fit(points,min_observations=20)
    assert model.status=="INSUFFICIENT_CALIBRATION_HISTORY"


def test_isotonic_calibration_is_monotonic_when_ready():
    points=[]
    for i in range(20):
        p=i/20
        points.append(CalibrationPoint(p,1 if i>=10 else 0,f"2026-01-{i+1:02d}T00:00:00Z"))
    model=IsotonicCalibrationEngine().fit(points,min_observations=20)
    assert model.status=="READY"
    vals=[model.transform(x/20) for x in range(20)]
    assert vals==sorted(vals)
