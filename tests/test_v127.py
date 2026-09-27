import pytest
from orion.data.providers import *
from orion.data.reconcile import Reconciler
from orion.data.pit import *
from orion.research.queue import *
from orion.research.pipeline import Pipeline
from orion.app.api import *
from orion.ops.preflight import *

def obs(provider='nse',h='a'*64): return ProviderObservation(provider,'financial_results','S1','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',h,False)
def test_provider_hash(): assert len(hash_payload(b'x'))==64
def test_provider_contract():
 r=ProviderRegistry(); r.register(ProviderContract('nse',FeedMode.PUBLIC,frozenset({'financial_results'}))); assert len(r.resolve('financial_results',FeedMode.PUBLIC))==1
def test_bad_hash():
 with pytest.raises(ValueError): validate_observation(ProviderObservation('x','d','s','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z','x',False))
def test_bad_time():
 with pytest.raises(ValueError): validate_observation(ProviderObservation('x','d','s','2026-01-02T00:00:00Z','2026-01-01T00:00:00Z','a'*64,False))
def test_reconcile_agreement(): assert Reconciler().reconcile([obs(),obs('b')]).status=='AGREED'
def test_reconcile_disagreement():
 r=Reconciler().reconcile([obs(),obs('b','b'*64)]); assert r.disagreement and r.selected_provider is None

def test_pit():
 p=PITStore(); p.append(Observation('S1','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',1,'e')); assert len(p.as_of('S1','2026-01-03T00:00:00Z'))==1

def test_future_excluded():
 p=PITStore(); p.append(Observation('S1','2026-01-01T00:00:00Z','2026-01-04T00:00:00Z',1,'e')); assert len(p.as_of('S1','2026-01-03T00:00:00Z'))==0

def test_queue_idempotent():
 q=ResearchQueue(); a=q.enqueue(['S2','S1']); b=q.enqueue(['S1','S2']); assert a.key==b.key

def test_queue_retry():
 q=ResearchQueue(); j=q.enqueue(['S1']); q.claim(j.key); q.fail(j.key,'x'); q.retry(j.key); assert q.jobs[j.key].status==Status.READY

def test_api_isolation():
 a=API(); a.research_request(RequestContext('u1','r1','analyst'),['S1'])
 with pytest.raises(PermissionError): a.get_request(RequestContext('u2','r2','analyst'),'r1')

def test_preflight(): assert Preflight(True,True,True,True,'public').validate()
def test_preflight_blocks():
 with pytest.raises(RuntimeError): Preflight(True,False,True,True,'public').validate()

def test_pipeline():
 p=PITStore(); p.append(Observation('S1','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',1,'e')); r=Pipeline(p,ResearchQueue()).run(['S1'],'2026-01-03T00:00:00Z'); assert r[0].status=='EVIDENCE_SUPPORTED'

def test_pipeline_blocks_empty():
 with pytest.raises(RuntimeError): Pipeline(PITStore(),ResearchQueue()).run(['S1'],'2026-01-03T00:00:00Z')
