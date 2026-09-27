from __future__ import annotations
from dataclasses import dataclass
from ..data.time import parse_utc

@dataclass(frozen=True)
class BacktestResult:
    trades: int
    gross_return: float
    net_return: float
    rejected_lookahead: int
    observations_used: int

class PITBacktest:
    def __init__(self, transaction_cost_bps=10, slippage_bps=5):
        self.transaction_cost_bps=float(transaction_cost_bps); self.slippage_bps=float(slippage_bps)
    def run(self, rows, decision_time):
        decision=parse_utc(decision_time); used=[]; rejected=0
        for r in rows:
            available=parse_utc(r['available_time'])
            if available > decision: rejected += 1; continue
            used.append(r)
        if not used: return BacktestResult(0,0.0,0.0,rejected,0)
        gross=0.0
        for r in used: gross += float(r.get('return',0.0))
        trades=len(used); cost=trades*(self.transaction_cost_bps+self.slippage_bps)/10000.0
        return BacktestResult(trades,gross,gross-cost,rejected,len(used))
