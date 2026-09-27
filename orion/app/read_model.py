from __future__ import annotations
from dataclasses import asdict
from typing import Any

def build_read_model(gateway):
    state=gateway.state(); h=state.get('health',{}); b=state.get('brain',{}); p=state.get('paper',{})
    return {
        'runtime': {'version':state.get('version'),'mode':state.get('mode'),'health':h},
        'brain': b,
        'portfolio': p,
        'operations': state.get('operations',{}),
        'data_boundary': state.get('data_boundary',{}),
        'capabilities': state.get('operations',{}).get('capabilities',[]),
        'safety': {'live_trading_enabled':False,'synthetic_market_data':False},
        'learning': state.get('learning',{}),
        'replay': state.get('replay',{}),
        'research': state.get('research',{}),
    }
