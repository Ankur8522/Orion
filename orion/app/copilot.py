from __future__ import annotations
class RuntimeCopilot:
    """Deterministic read-only copilot over verified runtime state; no invented market claims."""
    def answer(self, state, question: str):
        q=(question or '').strip().lower()
        if not q: return {'status':'EMPTY','answer':'Ask about runtime, brain, paper portfolio, audit, or data readiness.'}
        h=state.get('health',{}); p=state.get('paper',{}); b=state.get('brain',{})
        if any(x in q for x in ('health','status','runtime')):
            return {'status':'OK','answer':f"Runtime is {h.get('status','UNKNOWN')}; audit integrity={state.get('journal',{}).get('integrity')}; live trading={state.get('live_trading_enabled')} ."}
        if any(x in q for x in ('p&l','pnl','portfolio','position')):
            return {'status':'OK','answer':f"Paper portfolio: {p.get('position_count',0)} positions, unrealized P&L={p.get('unrealized_pnl',0)}, gross market value={p.get('gross_market_value',0)}."}
        if any(x in q for x in ('brain','thesis','reasoning')):
            return {'status':'OK','answer':f"Brain memory states={b.get('memory_states',0)}, latest cycle={b.get('latest_cycle')}, phase={b.get('phase')}, uncertainty={b.get('uncertainty')}, fragility={b.get('fragility')}."}
        if any(x in q for x in ('audit','journal','integrity')):
            return {'status':'OK','answer':f"Audit events={state.get('journal',{}).get('events',0)}; journal integrity={state.get('journal',{}).get('integrity')}."}
        if any(x in q for x in ('data','market','feed','provider')):
            return {'status':'OK','answer':f"Market data boundary={state.get('data_boundary',{}).get('market_data')}; PIT protection={state.get('data_boundary',{}).get('pit')}."}
        return {'status':'UNSUPPORTED','answer':'I can answer verified runtime questions about health, brain state, paper portfolio, audit integrity and data readiness. I will not invent market facts.'}
