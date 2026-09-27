import json, threading, urllib.request
from http.server import ThreadingHTTPServer
from orion.app.server import OrionHTTPRequestHandler

def test_v162_capability_and_readiness_surfaces():
    server=ThreadingHTTPServer(('127.0.0.1',0), OrionHTTPRequestHandler)
    t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        base=f'http://127.0.0.1:{server.server_address[1]}'
        for path in ('/api/capabilities','/api/readiness','/api/learning','/api/state','/'):
            r=urllib.request.urlopen(base+path,timeout=2); assert r.status==200
            body=r.read(); assert body
        caps=json.loads(urllib.request.urlopen(base+'/api/capabilities').read())
        assert caps['live_trading_enabled'] is False
        assert 'RESEARCH_FACTORY' in caps['architecture']
    finally:
        server.shutdown(); server.server_close()
