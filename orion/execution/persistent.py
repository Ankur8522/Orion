from __future__ import annotations
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from orion.execution.paper import PaperExecutionBook, PaperFill, PaperOrder, PaperPosition


class PersistentPaperExecutionBook(PaperExecutionBook):
    """Restart-safe paper execution state. Never routes to a live broker."""
    def __init__(self, path=':memory:'):
        super().__init__()
        self.path = str(path)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_orders (order_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_fills (fill_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_positions (security_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_nav (timestamp TEXT PRIMARY KEY, cash REAL NOT NULL, nav REAL NOT NULL, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_ledger (entry_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS paper_account (key TEXT PRIMARY KEY, value REAL NOT NULL)')
        self._db.commit(); self._hydrate()

    @staticmethod
    def _json(obj): return json.dumps(asdict(obj), sort_keys=True, separators=(',', ':'))

    def _hydrate(self):
        for (payload,) in self._db.execute('SELECT payload FROM paper_orders'):
            self._orders_obj(json.loads(payload))
        for (payload,) in self._db.execute('SELECT payload FROM paper_fills'):
            x=json.loads(payload); self._fills[x['fill_id']]=PaperFill(**x)
        for key, value in self._db.execute("SELECT key,value FROM paper_account"):
            if key == 'cash': self._cash = float(value)
            elif key == 'fees': self._fees = float(value)
            elif key == 'realized_pnl': self._realized_pnl = float(value)
        for (payload,) in self._db.execute('SELECT payload FROM paper_positions'):
            x=json.loads(payload); self._positions[x['security_id']]=PaperPosition(**x)

    def _orders_obj(self, x): self._orders[x['order_id']]=PaperOrder(**x)

    def stage(self, **kwargs):
        order=super().stage(**kwargs); self._db.execute('INSERT OR REPLACE INTO paper_orders VALUES(?,?)',(order.order_id,self._json(order))); self._db.commit(); return order
    def fill(self, order_id, **kwargs):
        fill=super().fill(order_id, **kwargs)
        order=self._orders[order_id]
        self._db.execute('INSERT OR REPLACE INTO paper_orders VALUES(?,?)',(order_id,self._json(order)))
        self._db.execute('INSERT OR REPLACE INTO paper_fills VALUES(?,?)',(fill.fill_id,self._json(fill)))
        self._db.execute('INSERT OR REPLACE INTO paper_positions VALUES(?,?)',(fill.security_id,self._json(self._positions[fill.security_id])))
        self._db.execute('INSERT OR REPLACE INTO paper_account VALUES(?,?)', ('cash', self._cash))
        self._db.execute('INSERT OR REPLACE INTO paper_account VALUES(?,?)', ('fees', self._fees))
        self._db.execute('INSERT OR REPLACE INTO paper_account VALUES(?,?)', ('realized_pnl', self._realized_pnl))
        ledger_payload = {'fill_id':fill.fill_id,'order_id':fill.order_id,'security_id':fill.security_id,
                          'quantity':fill.quantity,'price':fill.price,'side':fill.side,'timestamp':fill.timestamp,
                          'cash_after':self._cash,'fees_cumulative':self._fees,'realized_pnl_cumulative':self._realized_pnl}
        self._db.execute('INSERT OR REPLACE INTO paper_ledger VALUES(?,?)',(fill.fill_id,json.dumps(ledger_payload,sort_keys=True,separators=(',',':'))))
        self._db.commit(); return fill
    def mark(self, security_id, price):
        position=super().mark(security_id, price)
        self._db.execute('INSERT OR REPLACE INTO paper_positions VALUES(?,?)',(security_id,self._json(position))); self._db.commit(); return position
    def record_nav(self, timestamp: str, *, cash: float | None = None):
        if cash is not None:
            if float(cash) < 0: raise ValueError("INVALID_CASH")
            self._cash = float(cash)
            self._db.execute('INSERT OR REPLACE INTO paper_account VALUES(?,?)', ('cash', self._cash))
        nav=float(self._cash)+sum(p.market_value for p in self.positions())
        payload=json.dumps({"positions":[asdict(x) for x in self.positions()]}, sort_keys=True, separators=(",", ":"))
        self._db.execute('INSERT OR REPLACE INTO paper_nav VALUES(?,?,?,?)',(timestamp,float(self._cash),nav,payload)); self._db.commit()
        return {"timestamp":timestamp,"cash":float(self._cash),"nav":nav,"position_count":len(self.positions()),"fees":self._fees,"realized_pnl":self._realized_pnl}
    def nav_history(self):
        return tuple({"timestamp":r[0],"cash":r[1],"nav":r[2],"payload":json.loads(r[3])} for r in self._db.execute('SELECT timestamp,cash,nav,payload FROM paper_nav ORDER BY timestamp'))
    def ledger(self):
        return tuple(json.loads(r[1]) for r in self._db.execute('SELECT entry_id,payload FROM paper_ledger ORDER BY entry_id'))
    def close(self): self._db.close()
