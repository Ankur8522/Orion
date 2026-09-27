from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json

D=Decimal

@dataclass(frozen=True)
class ExecutionCostModel:
    slippage_bps: float = 5.0
    impact_bps: float = 0.0
    brokerage_bps: float = 0.0
    exchange_bps: float = 0.0
    gst_bps: float = 0.0
    stt_bps_buy: float = 0.0
    stt_bps_sell: float = 0.0
    stamp_bps_buy: float = 0.0
    sebi_bps: float = 0.0
    def __post_init__(self):
        vals=(self.slippage_bps,self.impact_bps,self.brokerage_bps,self.exchange_bps,self.gst_bps,self.stt_bps_buy,self.stt_bps_sell,self.stamp_bps_buy,self.sebi_bps)
        if any(float(x)<0 for x in vals): raise ValueError('INVALID_COST_MODEL')

@dataclass(frozen=True)
class CostedFill:
    gross_value: float
    execution_price: float
    slippage_cost: float
    impact_cost: float
    brokerage: float
    exchange_cost: float
    gst: float
    stt: float
    stamp_duty: float
    sebi_fee: float
    total_cost: float
    net_cash_flow: float
    lineage_hash: str

class RealisticPaperCostEngine:
    """Applies explicit supplied assumptions to a paper fill; never invents market price."""
    def apply(self, *, quantity: float, reference_price: float, side: str, model: ExecutionCostModel|None=None) -> CostedFill:
        if quantity<=0 or reference_price<=0 or side not in {'BUY','SELL'}: raise ValueError('INVALID_FILL')
        m=model or ExecutionCostModel(); q=D(str(quantity)); px=D(str(reference_price)); sign=D(1 if side=='BUY' else -1)
        slip=(D(str(m.slippage_bps))+D(str(m.impact_bps)))/D(10000)
        exec_px=px*(D(1)+slip*sign)
        gross=q*exec_px
        brokerage=gross*D(str(m.brokerage_bps))/D(10000)
        exchange=gross*D(str(m.exchange_bps))/D(10000)
        gst=(brokerage+exchange)*D(str(m.gst_bps))/D(10000)
        stt=gross*D(str(m.stt_bps_buy if side=='BUY' else m.stt_bps_sell))/D(10000)
        stamp=(gross*D(str(m.stamp_bps_buy))/D(10000)) if side=='BUY' else D(0)
        sebi=gross*D(str(m.sebi_bps))/D(10000)
        slip_cost=q*px*D(str(m.slippage_bps))/D(10000)
        impact_cost=q*px*D(str(m.impact_bps))/D(10000)
        total=brokerage+exchange+gst+stt+stamp+sebi+slip_cost+impact_cost
        cash=-(gross+brokerage+exchange+gst+stt+stamp+sebi) if side=='BUY' else (gross-brokerage-exchange-gst-stt-stamp-sebi)
        r=lambda x: float(x.quantize(D('0.00000001'),rounding=ROUND_HALF_UP))
        payload={'quantity':r(q),'reference_price':r(px),'side':side,'execution_price':r(exec_px),'total_cost':r(total),'cash':r(cash),'model':m.__dict__}
        h=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return CostedFill(r(q*px),r(exec_px),r(slip_cost),r(impact_cost),r(brokerage),r(exchange),r(gst),r(stt),r(stamp),r(sebi),r(total),r(cash),h)
