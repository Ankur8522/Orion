from orion.portfolio.performance import PortfolioPerformanceEngine
from orion.research.coverage import build_universe_coverage
from orion.runtime.supervisor import RuntimeSupervisor
from orion.runtime.data_plane import DataPlaneRegistry
from orion.security.access import AccessPolicy,Principal,Role

class R:
    def __init__(self,status,reason=None): self.status=status; self.reason=reason

def test_performance_drawdown_and_reconciliation():
    e=PortfolioPerformanceEngine(); s=e.summarize([('1',100),('2',110),('3',99),('4',120)])
    assert round(s.total_return_pct,4)==20
    assert s.max_drawdown_pct < 0
    assert s.observations==4

def test_coverage_is_explicit():
    s=build_universe_coverage([R('COMPLETE'),R('BLOCKED','NO_EVIDENCE'),R('FAILED','X')])
    assert s.total==3 and s.complete==1 and s.blocked==1 and s.failed==1
    assert s.coverage_pct==33.3333
    assert s.blocker_reasons['NO_EVIDENCE']==1

def test_supervisor_is_bounded_and_degrades():
    r=RuntimeSupervisor(max_steps=2).run([('a',lambda:'ok'),('b',lambda:'ok'),('c',lambda:'ignored')])
    assert len(r.steps)==2 and r.status=='OK'
    r2=RuntimeSupervisor().run([('x',lambda:1/0)])
    assert r2.status=='DEGRADED' and r2.steps[0].status=='FAILED'

def test_provider_boundary_never_implies_live():
    d=DataPlaneRegistry(); d.register('demo',configured=True,authenticated=True,capabilities=['quotes'],reason='AUTHORIZED')
    assert d.ready('demo') is True

def test_access_policy_live_trade_is_impossible():
    p=AccessPolicy(); admin=Principal('a',Role.ADMIN); viewer=Principal('v',Role.VIEWER)
    assert p.allowed(admin,'trade:paper:stage')
    assert not p.allowed(admin,'trade:live:submit')
    assert not p.allowed(viewer,'ops:restart')
    assert p.allowed(viewer,'read:state')
