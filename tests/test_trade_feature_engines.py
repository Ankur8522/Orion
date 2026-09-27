from orion.decision.technical_features import TechnicalFeatureEngine
from orion.decision.fundamental_features import FundamentalFeatureEngine


def _rows(n=70):
    rows=[]
    for i in range(n):
        close=100.0+i*0.5
        rows.append({
            "event_time": f"2026-01-{(i%28)+1:02d}T00:00:00Z" if i < 28 else f"2026-02-{(i-28)+1:02d}T00:00:00Z" if i < 56 else f"2026-03-{(i-56)+1:02d}T00:00:00Z",
            "available_time": f"2026-01-{(i%28)+1:02d}T01:00:00Z" if i < 28 else f"2026-02-{(i-28)+1:02d}T01:00:00Z" if i < 56 else f"2026-03-{(i-56)+1:02d}T01:00:00Z",
            "open": close-0.2, "high": close+0.8, "low": close-0.8, "close": close,
            "volume": 1000.0 + (300.0 if i == n-1 else 0.0), "source_id": "fixture"
        })
    return rows


def test_technical_features_are_pit_safe_and_derived():
    snap=TechnicalFeatureEngine().build("X", _rows(), as_of="2026-03-15T00:00:00Z", source_ids=["fixture"])
    assert "technical_trend" in snap.mapping
    assert "technical_momentum" in snap.mapping
    assert "volume_confirmation" in snap.mapping
    assert "breakout_quality" in snap.mapping
    assert all(0 <= v <= 1 for v in snap.mapping.values())
    assert snap.lineage_hash


def test_technical_engine_rejects_future_rows():
    rows=_rows()
    rows.append({"event_time":"2026-04-01T00:00:00Z","available_time":"2026-04-01T00:00:00Z","close":200,"volume":1000})
    try:
        TechnicalFeatureEngine().build("X", rows, as_of="2026-03-15T00:00:00Z")
    except ValueError as exc:
        assert str(exc)=="FUTURE_TECHNICAL_OBSERVATION"
    else:
        raise AssertionError("future technical observation accepted")


def test_fundamental_features_do_not_invent_missing_visibility():
    snap=FundamentalFeatureEngine().build(
        "X", as_of="2026-03-15T00:00:00Z",
        latest={"revenue_growth":0.20,"pat_growth":0.25,"roe":0.18,"roic_proxy":0.16,"ebitda_margin":0.22,"net_margin":0.12,"cfo_pat":1.05,"fcf":100,"pat":120,"pe":18,"pb":3,"ev_ebitda":12,"debt_ebitda":1.2,"net_debt":120,"ebitda":100},
    )
    assert "earnings_growth" in snap.mapping
    assert "business_visibility" in snap.missing
    assert "business_visibility" not in snap.mapping
    assert all(0 <= v <= 1 for v in snap.mapping.values())
