from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    security_id: str
    target_weight: float
    current_weight: float
    delta_weight: float
    state: str
    reason: str
    lineage_hash: str


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    security_id: str
    quantity: float
    price: float
    side: str
    timestamp: str


@dataclass(frozen=True)
class PaperPosition:
    security_id: str
    quantity: float
    average_price: float
    mark_price: float
    market_value: float
    unrealized_pnl: float


class PaperExecutionBook:
    """Paper-only order, fill and mark-to-market lifecycle. No broker routing."""

    def __init__(self):
        self._orders = {}
        self._fills = {}
        self._positions = {}
        self._cash = 0.0
        self._fees = 0.0
        self._realized_pnl = 0.0

    def stage(self, *, security_id: str, target_weight: float, current_weight: float,
              allowed: bool, reason: str, lineage_hash: str) -> PaperOrder:
        if not security_id or not 0 <= target_weight <= 1 or not 0 <= current_weight <= 1:
            raise ValueError("INVALID_PAPER_ORDER")
        state = "STAGED" if allowed else "BLOCKED"
        delta = round(target_weight - current_weight, 12)
        payload = {"security_id": security_id, "target_weight": target_weight,
                   "current_weight": current_weight, "delta": delta, "state": state,
                   "reason": reason, "lineage_hash": lineage_hash}
        oid = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        order = PaperOrder(oid, security_id, target_weight, current_weight, delta, state, reason, lineage_hash)
        self._orders[oid] = order
        return order

    def fill(self, order_id: str, *, quantity: float, price: float, side: str, timestamp: str, total_cost: float = 0.0) -> PaperFill:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError("PAPER_ORDER_NOT_FOUND")
        if order.state != "STAGED":
            raise ValueError("PAPER_ORDER_NOT_FILLABLE")
        if quantity <= 0 or price <= 0 or side not in {"BUY", "SELL"} or total_cost < 0:
            raise ValueError("INVALID_PAPER_FILL")
        old = self._positions.get(order.security_id)
        q = old.quantity if old else 0.0
        avg = old.average_price if old else 0.0
        signed = quantity if side == "BUY" else -quantity
        new_q = q + signed
        if new_q < -1e-12:
            raise ValueError("PAPER_SHORT_NOT_ALLOWED")
        gross=float(quantity)*float(price)
        if side == "SELL":
            self._realized_pnl += float(quantity) * (float(price) - avg)
        self._cash += (-gross-total_cost) if side == "BUY" else (gross-total_cost)
        self._fees += float(total_cost)
        payload = {"order_id": order_id, "security_id": order.security_id,
                   "quantity": quantity, "price": price, "side": side, "timestamp": timestamp,
                   "total_cost": float(total_cost)}
        fid = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        fill = PaperFill(fid, order_id, order.security_id, float(quantity), float(price), side, timestamp)
        self._fills[fid] = fill
        new_avg = ((q * avg) + (quantity * price)) / new_q if new_q > 0 and side == "BUY" else (avg if new_q > 0 else 0.0)
        mark = old.mark_price if old else price
        self._positions[order.security_id] = PaperPosition(order.security_id, new_q, new_avg, mark,
                                                            new_q * mark, new_q * (mark - new_avg))
        self._orders[order_id] = PaperOrder(order.order_id, order.security_id, order.target_weight,
                                            order.current_weight, order.delta_weight, "FILLED", order.reason,
                                            order.lineage_hash)
        return fill

    def mark(self, security_id: str, price: float) -> PaperPosition:
        if price <= 0:
            raise ValueError("INVALID_MARK_PRICE")
        old = self._positions.get(security_id)
        if old is None:
            return PaperPosition(security_id, 0.0, 0.0, float(price), 0.0, 0.0)
        position = PaperPosition(security_id, old.quantity, old.average_price, float(price),
                                 old.quantity * price, old.quantity * (price - old.average_price))
        self._positions[security_id] = position
        return position

    def orders(self):
        return tuple(self._orders[k] for k in sorted(self._orders))

    def fills(self):
        return tuple(self._fills[k] for k in sorted(self._fills))

    def positions(self):
        return tuple(self._positions[k] for k in sorted(self._positions))

    def snapshot(self) -> dict:
        positions = self.positions()
        return {
            "positions": positions,
            "gross_market_value": round(sum(p.market_value for p in positions), 12),
            "unrealized_pnl": round(sum(p.unrealized_pnl for p in positions), 12),
            "orders": len(self._orders),
            "fills": len(self._fills),
            "cash": round(self._cash, 12),
            "fees": round(self._fees, 12),
            "realized_pnl": round(self._realized_pnl, 12),
            "net_realized_pnl": round(self._realized_pnl - self._fees, 12),
            "nav": round(self._cash + sum(p.market_value for p in positions), 12),
        }

    @staticmethod
    def live_trading_enabled() -> bool:
        return False
