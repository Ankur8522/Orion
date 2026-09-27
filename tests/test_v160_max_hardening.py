import json, os, tempfile, urllib.request, threading
from pathlib import Path
from orion.runtime.state_store import RuntimeStateStore
from orion.runtime.persistent_queue import PersistentResearchQueue, PersistentJobStatus
from orion.runtime.control_plane import OrionControlPlane
from orion.app.gateway import RuntimeGateway
from orion.app.copilot import RuntimeCopilot

def test_state_store_persists_cycles_alerts_and_events(tmp_path):
    p=tmp_path/'state.sqlite'; s=RuntimeStateStore(p)
    s.cycle_start('c1','2026-01-01T00:00:00Z',{'x':1}); s.cycle_finish('c1','2026-01-01T00:01:00Z','COMPLETE',{'ok':1})
    s.add_alert('2026-01-01T00:01:00Z','WARN','X','message'); s.event('2026-01-01T00:01:00Z','TEST',{'a':1}); s.close()
    s2=RuntimeStateStore(p); assert s2.cycles()[0]['cycle_id']=='c1'; assert s2.alerts()[0]['code']=='X'; assert s2.events()[0]['kind']=='TEST'; s2.close()

def test_research_queue_restart_safe(tmp_path):
    p=tmp_path/'q.sqlite'; q=PersistentResearchQueue(p); j=q.enqueue(['B','A']); assert j.status is PersistentJobStatus.READY; q.claim(j.key); q.close() if hasattr(q,'close') else None
    q2=PersistentResearchQueue(p); assert q2.get(j.key).status is PersistentJobStatus.RUNNING; assert q2.get(j.key).attempts==1

def test_control_plane_health_has_persistent_ops(tmp_path):
    cp=OrionControlPlane(state_path=tmp_path/'brain.sqlite',journal_path=tmp_path/'journal.sqlite',paper_path=tmp_path/'paper.sqlite')
    h=cp.health(); assert h['live_trading_enabled'] is False; assert 'research_jobs' in h; assert 'cycles' in h; cp.state_store.close(); cp.research_queue._db.close()

def test_gateway_has_runtime_first_contract(tmp_path):
    cp=OrionControlPlane(state_path=tmp_path/'brain.sqlite',journal_path=tmp_path/'journal.sqlite',paper_path=tmp_path/'paper.sqlite')
    d=RuntimeGateway(cp).state(); assert d['version']== 'v190'; assert d['data_boundary']['synthetic_market_data'] is False; assert d['live_trading_enabled'] is False; assert 'operations' in d; cp.state_store.close(); cp.research_queue._db.close()

def test_copilot_never_invents_market_data():
    r=RuntimeCopilot().answer({'health':{'status':'OK'},'journal':{'integrity':True},'live_trading_enabled':False,'paper':{},'brain':{},'data_boundary':{'market_data':'NOT_CONFIGURED'}},'what is market data')
    assert 'NOT_CONFIGURED' in r['answer']

def test_ui_has_no_demo_data_language_and_runtime_endpoints():
    html=Path('orion/ui/index.html').read_text(); js=Path('orion/ui/app.js').read_text()
    assert 'DEMO DATA' not in html; assert '/api/state' in js; assert '/api/copilot' in js; assert 'No fake data' in js or 'no fake data' in js
