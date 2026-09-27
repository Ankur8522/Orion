import json, os, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from orion.app.server import OrionHTTPRequestHandler


def test_ops_endpoint_rejects_role_header_without_configured_token():
    server=ThreadingHTTPServer(('127.0.0.1',0), OrionHTTPRequestHandler)
    t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        base=f'http://127.0.0.1:{server.server_address[1]}'
        req=urllib.request.Request(base+'/api/ops/ack-alert', data=json.dumps({'alert_id':1}).encode(), headers={'Content-Type':'application/json','X-ORION-ROLE':'ADMIN'})
        try:
            urllib.request.urlopen(req,timeout=2)
            assert False, 'expected authorization failure'
        except urllib.error.HTTPError as e:
            assert e.code==403
    finally:
        server.shutdown(); server.server_close()


def test_ops_endpoint_accepts_configured_token(monkeypatch):
    monkeypatch.setenv('ORION_API_TOKENS','ADMIN:test-admin-token')
    server=ThreadingHTTPServer(('127.0.0.1',0), OrionHTTPRequestHandler)
    t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        base=f'http://127.0.0.1:{server.server_address[1]}'
        req=urllib.request.Request(base+'/api/ops/ack-alert', data=json.dumps({'alert_id':999999}).encode(), headers={'Content-Type':'application/json','X-ORION-TOKEN':'test-admin-token'})
        r=urllib.request.urlopen(req,timeout=2); assert r.status==200
    finally:
        server.shutdown(); server.server_close()
