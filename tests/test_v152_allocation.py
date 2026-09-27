from orion.portfolio.allocation import AllocationCandidate, DynamicCapitalAllocationBrain

def test_allocation_respects_constraints_and_produces_actions():
    b=DynamicCapitalAllocationBrain()
    out=b.assess((
        AllocationCandidate('A',.20,.2,.9,.1,.9,.1,.10),
        AllocationCandidate('B',.10,.3,.7,.2,.8,.2,.10),
        AllocationCandidate('C',-.05,.7,.4,.7,.3,.8,.20),
    ), max_weight=.50, cash_floor=.10)
    assert sum(w for _,w in out.target_weights) <= .90 + 1e-9
    assert all(w <= .50 + 1e-9 for _,w in out.target_weights)
    assert out.target_weights
    assert out.lineage_hash and len(out.lineage_hash)==64

def test_low_quality_candidate_gets_no_forced_capital_and_feedback_trigger():
    out=DynamicCapitalAllocationBrain().assess((
        AllocationCandidate('A',.10,.2,.8,.1,.8,.1,.4),
        AllocationCandidate('B',-.8,.9,.1,.9,.2,.9,.1),
    ), max_weight=.8)
    assert dict(out.target_weights)['B'] == 0.0
    assert any(x.startswith('COLLECT_FEEDBACK:B') for x in out.adaptive_triggers)

def test_allocation_is_deterministic():
    args=((AllocationCandidate('A',.2,.2,.8,.1,.8,.1,.2), AllocationCandidate('B',.1,.3,.7,.2,.7,.2,.2)),)
    a=DynamicCapitalAllocationBrain().assess(*args)
    b=DynamicCapitalAllocationBrain().assess(*args)
    assert a == b

def test_api_exposes_allocation_brain():
    from orion.app.api import API, RequestContext
    api=API(rate_limit=100)
    ctx=RequestContext('u1','r2','analyst')
    out=api.allocation_assessment(ctx,(AllocationCandidate('A',.2,.2,.8,.1,.8,.1,.1),),max_weight=.5)
    assert dict(out.target_weights)['A'] == .5
