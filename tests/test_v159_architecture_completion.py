import json
from urllib.request import urlopen
from threading import Thread
from http.server import ThreadingHTTPServer
from orion.execution.persistent import PersistentPaperExecutionBook
from orion.runtime.universe import UniverseOperatingRuntime
from orion.runtime.health import evaluate_health
from orion.app.server import OrionHTTPRequestHandler


def test_persistent_paper_book_survives_restart(tmp_path):
    p=tmp_path/'paper.db'
    b=PersistentPaperExecutionBook(p)
    o=b.stage(security_id='ABC',target_weight=.2,current_weight=0,allowed=True,reason='RESEARCH_SUPPORTED',lineage_hash='a'*64)
    b.fill(o.order_id,quantity=10,price=100,side='BUY',timestamp='2026-09-27T10:00:00Z')
    b.mark('ABC',110); b.close()
    b2=PersistentPaperExecutionBook(p)
    assert b2.positions()[0].unrealized_pnl==100
    assert len(b2.orders())==1 and len(b2.fills())==1


def test_universe_runtime_blocks_missing_data_cleanly():
    rt=UniverseOperatingRuntime()
    report=rt.research_cycle(['A','B'],as_of='2026-09-27T00:00:00Z')
    assert report.research.blocked==2 and report.status=='BLOCKED'


def test_runtime_health_preserves_live_trading_boundary():
    from orion.runtime.control_plane import OrionControlPlane
    h=evaluate_health(OrionControlPlane())
    assert h.status=='OK' and h.live_trading_enabled is False and h.brain_ready


def test_gateway_state_is_runtime_oriented():
    from orion.app.gateway import RuntimeGateway
    s=RuntimeGateway().state()
    assert s['mode']=='RUNTIME' and s['live_trading_enabled'] is False
    assert s['brain']['closed_loop'] is True


def test_http_cockpit_exposes_runtime_contract():
    from orion.app.server import OrionHTTPRequestHandler
    from http.server import ThreadingHTTPServer
    from threading import Thread
    import time
    server=ThreadingHTTPServer(('127.0.0.1',0),OrionHTTPRequestHandler)
    t=Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        with urlopen(f'http://127.0.0.1:{server.server_port}/api/state') as r:
            data=json.loads(r.read().decode())
        assert data['mode']=='RUNTIME' and data['live_trading_enabled'] is False
        with urlopen(f'http://127.0.0.1:{server.server_port}/') as r:
            html=r.read().decode()
        assert 'Operations' in html and 'runtimeRefresh' in html
    finally:
        server.shutdown(); t.join(timeout=2); server.server_close()
