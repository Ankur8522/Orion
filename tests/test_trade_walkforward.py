from orion.decision.trade_intelligence import TradeIntelligenceEngine, TradeTrainingRow, FEATURES
from orion.learning.trade_walkforward import TradeWalkForwardTrainer


def test_walk_forward_is_chronological_and_holds_out_test():
    rows=[]
    for i in range(50):
        as_of=f"2026-01-{i+1:02d}T00:00:00Z" if i<28 else f"2026-02-{i-27:02d}T00:00:00Z"
        features={k:(0.8 if i%2 else 0.2) for k in FEATURES}
        rows.append(TradeTrainingRow(f"S{i}",as_of,features,i%2,as_of,f"2026-03-{(i%20)+1:02d}T00:00:00Z"))
    report=TradeWalkForwardTrainer().run(TradeIntelligenceEngine(),rows,min_train_rows=12,min_calibration_rows=10,min_test_rows=8)
    assert report.train_rows > 0
    assert report.calibration_rows > 0
    assert report.test_rows >= 8
    assert report.train_end < report.calibration_end < report.test_end
