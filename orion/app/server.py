from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from orion.app.gateway import RuntimeGateway
from orion.app.copilot import RuntimeCopilot
from orion.security.access import AccessPolicy, Principal, Role
from orion.app.read_model import build_read_model

class OrionHTTPRequestHandler(BaseHTTPRequestHandler):
    gateway=RuntimeGateway(); copilot=RuntimeCopilot(); policy=AccessPolicy(); ui_root=Path(__file__).resolve().parent.parent/'ui'
    @classmethod
    def _principal(cls, handler):
        from os import environ
        token=handler.headers.get('X-ORION-TOKEN','')
        role_header=handler.headers.get('X-ORION-ROLE','VIEWER').upper()
        configured=environ.get('ORION_API_TOKENS','')
        if configured:
            mapping={}
            for item in configured.split(','):
                if ':' in item:
                    role,tok=item.split(':',1); mapping[tok]=role.upper()
            role_name=mapping.get(token,'VIEWER')
        else:
            role_name='VIEWER'
        try: role=Role(role_name)
        except ValueError: role=Role.VIEWER
        return Principal(handler.client_address[0],role)

    def _send(self,status,ctype,body):
        if isinstance(body,str): body=body.encode('utf-8')
        self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.send_header('X-ORION-Live-Trading','disabled'); self.end_headers(); self.wfile.write(body)
    def _json(self,status,payload): return self._send(status,'application/json; charset=utf-8',json.dumps(payload,sort_keys=True,default=str))
    def do_GET(self):
        u=urlparse(self.path); path=u.path; qs=parse_qs(u.query)
        if path=='/api/health': return self._json(200,self.gateway.health())
        if path=='/api/state': return self._json(200,self.gateway.state())
        if path=='/api/brain/history': return self._json(200,self.gateway.brain_history(qs.get('thesis_id',[None])[0]))
        if path=='/api/acquisition/operational-readiness':
            ids=[x for x in qs.get('security_id',[]) if x]
            provider=qs.get('provider',['upstox'])[0]
            as_of=qs.get('as_of',[None])[0]
            dataset=qs.get('dataset',['ohlcv'])[0]
            return self._json(200,self.gateway.acquisition_operational_readiness(ids, provider=provider, as_of=as_of, dataset=dataset))
        if path=='/api/audit': return self._json(200,self.gateway.audit(int(qs.get('limit',['100'])[0])))
        if path=='/api/performance': return self._json(200,self.gateway.state().get('performance',{}))
        if path=='/api/capabilities': return self._json(200,self.gateway.capabilities())
        if path=='/api/data/providers': return self._json(200,self.gateway.state().get('data_boundary',{}).get('providers',[]))
        if path=='/api/data/freshness': return self._json(200,self.gateway.state().get('provider_freshness',[]))
        if path=='/api/learning': return self._json(200,self.gateway.state().get('learning_diagnostics',{}))
        if path=='/api/learning/advanced': return self._json(200,self.gateway.advanced_learning_snapshot(int(qs.get('min_sample',['10'])[0])))
        if path=='/api/validation': return self._json(200,self.gateway.state().get('empirical_validation',{}))
        if path=='/api/readiness': return self._json(200,self.gateway.state().get('system_readiness',{}))
        if path=='/api/research/requirements': return self._json(200,{'datasets': self.gateway.state().get('research',{}).get('required_datasets',[])})
        if path=='/api/paper/nav': return self._json(200,{'history': list(getattr(self.gateway.control_plane.service.paper,'nav_history',lambda:())())})
        if path=='/api/overview': return self._json(200,build_read_model(self.gateway))
        if path=='/api/explorer/company':
            sid=qs.get('security_id',[''])[0].strip()
            if not sid: return self._json(400,{'error':'MISSING_SECURITY_ID'})
            as_of=qs.get('as_of',[None])[0]
            if not as_of:
                from datetime import datetime, timezone
                as_of=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            plan=self.gateway.research_readiness(sid,as_of,{})
            return self._json(200,{'security_id':sid,'as_of':as_of,'status':'READY' if plan.readiness.ready else 'BLOCKED','coverage_pct':plan.readiness.coverage_pct,'blockers':plan.readiness.blockers,'next_actions':plan.next_actions,'lineage_hash':plan.readiness.lineage_hash})
        if path=='/api/explorer/sector':
            sector=qs.get('sector',[''])[0].strip()
            if not sector: return self._json(400,{'error':'MISSING_SECTOR'})
            return self._json(200,{'sector':sector,'status':'DEPENDENCY','message':'Sector facts require an authorized sector/macro source. ORION will not synthesize them.','supported_layers':['sector_metrics','macro_sensitivity','peer_context','headwinds','catalysts']})
        if path=='/api/acquisition/coverage':
            ids=[x for x in qs.get('security_id',[]) if x]
            return self._json(200,self.gateway.acquisition_coverage(ids, qs.get('decision_time',[None])[0]))
        if path=='/api/acquisition/schedule':
            mid=qs.get('manifest_id',[''])[0].strip()
            if not mid: return self._json(400,{'error':'MISSING_MANIFEST_ID'})
            return self._json(200,self.gateway.acquisition_schedule(mid))
        if path=='/api/acquisition/readiness':
            ids=[x for x in qs.get('security_id',[]) if x]
            provider=qs.get('provider',['upstox'])[0]
            as_of=qs.get('as_of',[None])[0]
            return self._json(200,self.gateway.acquisition_readiness(ids, provider=provider, as_of=as_of))
        if path=='/api/acquisition/mappings':
            return self._json(200,{'provider':qs.get('provider',[None])[0],'mappings':self.gateway.acquisition_instrument_mappings(provider=qs.get('provider',[None])[0])})
        if path=='/api/acquisition/manifest':
            mid=qs.get('manifest_id',[''])[0].strip()
            if not mid: return self._json(400,{'error':'MISSING_MANIFEST_ID'})
            return self._json(200,self.gateway.acquisition_manifest_coverage(mid, qs.get('decision_time',[None])[0]))
        if path=='/api/data/integrity':
            return self._json(200, self.gateway.state().get('integrity',{}))
        if path=='/api/universe/historical':
            as_of=qs.get('as_of',[''])[0].strip()
            if not as_of: return self._json(400,{'error':'MISSING_AS_OF'})
            return self._json(200,self.gateway.historical_universe_snapshot(as_of))
        if path=='/api/portfolio/stress':
            return self._json(400,{'error':'POST_REQUIRED_FOR_PORTFOLIO_STRESS'})
        if path=='/api/universe/contract':
            return self._json(200,{'targets':self.gateway.universe_contract.targets,'target_size':self.gateway.universe_contract.target_size,'status':'READY_CONTRACT','note':'Constituents require an authorized membership source; ORION does not synthesize them.'})
        if path=='/api/risk/overview':
            return self._json(200,{'status':'READY','live_trading_enabled':False,'layers':['exposure','concentration','sector_overlap','liquidity','valuation_stretch','catalyst_timing','contagion','scenario_loss','drawdown_budget'],'note':'Portfolio-specific risk requires a governed portfolio state.'})
        if path=='/api/replay':
            r=self.gateway.control_plane.replay(qs.get('start',[None])[0], qs.get('end',[None])[0]); return self._json(200,r.__dict__)
        if path=='/api/learning/report': return self._json(200,self.gateway.control_plane.learning_report().__dict__)
        rel='index.html' if path in ('/','') else path.lstrip('/'); target=(self.ui_root/rel).resolve()
        if self.ui_root not in target.parents and target!=self.ui_root/'index.html': return self._send(403,'text/plain','FORBIDDEN')
        if not target.exists() or not target.is_file(): return self._send(404,'text/plain','NOT_FOUND')
        ctype={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8'}.get(target.suffix,'application/octet-stream')
        return self._send(200,ctype,target.read_bytes())
    def do_POST(self):
        u=urlparse(self.path); length=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(length) if length else b'{}'
        try: payload=json.loads(raw.decode('utf-8'))
        except Exception: return self._json(400,{'error':'INVALID_JSON'})
        if u.path=='/api/forecast/probabilistic':
            try:
                return self._json(200,self.gateway.probabilistic_forecast(base_rate=payload.get('base_rate'), evidence=payload.get('evidence',()), model_id=payload.get('model_id','orion-bounded-logistic'), temperature=payload.get('temperature',1.0), prior_strength=payload.get('prior_strength',1.0)))
            except (TypeError,ValueError,KeyError) as exc:
                return self._json(400,{'error':str(exc)})
        if u.path=='/api/paper/cost':
            try:
                return self._json(200,self.gateway.paper_cost(quantity=payload.get('quantity'), reference_price=payload.get('reference_price'), side=payload.get('side'), model=payload.get('model')))
            except (TypeError,ValueError,KeyError) as exc:
                return self._json(400,{'error':str(exc)})
        if u.path=='/api/portfolio/stress':
            try:
                return self._json(200,self.gateway.portfolio_stress(payload.get('weights',{}),payload.get('correlations'),payload.get('shocks'),payload.get('gross_exposure')))
            except (TypeError,ValueError) as exc:
                return self._json(400,{'error':str(exc)})
        if u.path=='/api/research/scenarios':
            try:
                return self._json(200,self.gateway.research_scenarios(payload))
            except (TypeError,ValueError,KeyError) as exc:
                return self._json(400,{'error':str(exc)})
        if u.path=='/api/portfolio/correlation':
            try:
                return self._json(200,self.gateway.portfolio_correlation(payload.get('returns',{}),payload.get('threshold',0.70)))
            except (TypeError,ValueError,KeyError) as exc:
                return self._json(400,{'error':str(exc)})
        if u.path=='/api/copilot':
            return self._json(200,self.copilot.answer(self.gateway.state(), str(payload.get('question',''))))
        if u.path=='/api/ops/ack-alert':
            principal=self._principal(self)
            if not self.policy.allowed(principal,'ops:ack_alert'): return self._json(403,{'error':'FORBIDDEN'})
            aid=payload.get('alert_id');
            if aid is None: return self._json(400,{'error':'MISSING_ALERT_ID'})
            self.gateway.control_plane.state_store.acknowledge(aid); return self._json(200,{'status':'ACKNOWLEDGED','alert_id':aid})
        return self._json(404,{'error':'NOT_FOUND'})
    def log_message(self,*_): pass

def serve(host='127.0.0.1',port=8787): ThreadingHTTPServer((host,port),OrionHTTPRequestHandler).serve_forever()
if __name__=='__main__': serve()
