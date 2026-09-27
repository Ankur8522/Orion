from orion.agents.research_society import EvidenceAuditor, opinion
from orion.research.orchestrator import ResearchOrchestrator
from orion.brain.state import EvidenceState

def ev(eid="e1", available="2026-01-02T00:00:00Z"):
    return {"evidence_id":eid,"available_time":available,"confidence":.9,"content_hash":"a"*64}

def test_future_offset_timestamp_is_rejected():
    r=EvidenceAuditor().audit([ev("e1","2026-01-02T02:00:00+02:00")],"2026-01-02T00:30:00Z")
    assert r.accepted==() and r.rejected==("e1",)

def test_disagreement_blocks_supported_state():
    r=ResearchOrchestrator().run("S1","2026-01-10T00:00:00Z",[ev()], [opinion("bull","S1","growth",["e1"]), opinion("bear","S1","risk",["e1"])])
    assert r.review["status"]=="REVIEW" and r.thesis_state.state==EvidenceState.BLOCKED

def test_unsupported_opinion_does_not_leak_claim():
    r=ResearchOrchestrator().run("S1","2026-01-10T00:00:00Z",[ev()], [opinion("bad","S1","unsupported",["missing"])])
    assert "unsupported" not in r.thesis_state.claims


def test_provider_timezone_order_is_semantic():
    from orion.data.providers import ProviderObservation, validate_observation
    o=ProviderObservation('p','d','S1','2026-01-02T02:00:00+02:00','2026-01-02T00:30:00Z','a'*64,False)
    import pytest
    with pytest.raises(ValueError): validate_observation(o, strict=False)

def test_provider_rejects_bad_hash_chars():
    from orion.data.providers import ProviderObservation, validate_observation
    import pytest
    o=ProviderObservation('p','d','S1','2026-01-01T00:00:00Z','2026-01-01T00:01:00Z','g'*64,False)
    with pytest.raises(ValueError): validate_observation(o)

def test_replay_schema_roundtrip(tmp_path):
    from orion.ops.replay import write_replay, load_replay
    p=tmp_path/'r.json'; write_replay(p, {'security_id':'S1'}); assert load_replay(p)=={'security_id':'S1'}
