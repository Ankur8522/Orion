from orion.decision.trade_intelligence import TradeIntelligenceEngine, TradeTrainingRow


def _vector(engine, sid, as_of, base=0.8):
    return engine.build_features(
        sid, as_of,
        fundamental={"fundamental_quality":base, "earnings_growth":base, "cashflow_quality":base, "valuation_attractiveness":base},
        technical={"technical_trend":base, "technical_momentum":base, "volume_confirmation":base, "breakout_quality":base},
        historical={"historical_setup":base},
        context={"catalyst_strength":base, "business_visibility":base, "forensic_quality":base, "regime_fit":base, "risk_quality":base},
        source_ids=["test-source"],
    )


def test_trade_fusion_ranks_high_quality_candidate():
    e = TradeIntelligenceEngine()
    high = _vector(e, "HIGH", "2026-01-01", 0.9)
    low = _vector(e, "LOW", "2026-01-01", 0.2)
    ranked = e.rank([low, high])
    assert ranked[0].security_id == "HIGH"
    assert ranked[0].score > ranked[1].score


def test_incomplete_or_risky_candidate_is_blocked():
    e = TradeIntelligenceEngine()
    v = e.build_features("X", "2026-01-01", technical={"technical_trend":0.9, "technical_momentum":0.9}, context={"forensic_quality":0.1, "risk_quality":0.2})
    s = e.score(v)
    assert s.action == "BLOCKED"
    assert "FORENSIC_RISK" in s.blockers
    assert "INSUFFICIENT_FEATURE_COMPLETENESS" in s.blockers


def test_training_rejects_future_information():
    e = TradeIntelligenceEngine()
    rows=[]
    for i in range(8):
        rows.append(TradeTrainingRow(f"S{i}", f"2026-01-{i+1:02d}T00:00:00Z", {"fundamental_quality":0.8}, 1 if i % 2 else 0, "2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z" ))
    try:
        e.fit(rows)
    except ValueError as exc:
        assert str(exc) == "FUTURE_TRAINING_OBSERVATION"
    else:
        raise AssertionError("future training observation was accepted")


def test_training_is_chronological_and_returns_validation_metric():
    e = TradeIntelligenceEngine()
    rows=[]
    for i in range(12):
        day=i+1
        rows.append(TradeTrainingRow(f"S{i}", f"2026-01-{day:02d}T00:00:00Z", {k:(0.9 if i % 2 else 0.2) for k in ("fundamental_quality","earnings_growth","cashflow_quality","valuation_attractiveness","technical_trend","technical_momentum","volume_confirmation","breakout_quality","historical_setup","catalyst_strength","business_visibility","forensic_quality","regime_fit","risk_quality")}, 1 if i % 2 else 0, f"2026-01-{day:02d}T00:00:00Z", f"2026-02-{day:02d}T00:00:00Z"))
    report=e.fit(rows, epochs=120)
    assert report.train_rows == 9
    assert report.validation_rows == 3
    assert report.validation_brier is not None
    assert report.lineage_hash


def test_training_rejects_silent_feature_imputation():
    e=TradeIntelligenceEngine()
    rows=[TradeTrainingRow(f"S{i}", f"2026-01-{i+1:02d}T00:00:00Z", {"fundamental_quality":0.8}, i%2, f"2026-01-{i+1:02d}T00:00:00Z", f"2026-02-{i+1:02d}T00:00:00Z") for i in range(8)]
    try:
        e.fit(rows)
    except ValueError as exc:
        assert str(exc)=="MISSING_TRAINING_FEATURE"
    else:
        raise AssertionError("sparse training features were silently imputed")
