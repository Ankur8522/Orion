from orion.data.integrity import DataIntegrityPipeline
from orion.data.providers import ProviderObservation


def obs(provider, h):
    return ProviderObservation(provider,'market_price','ABC','2026-09-27T00:00:00Z','2026-09-27T01:00:00Z',h,False)


def test_integrity_pipeline_accepts_agreement():
    r=DataIntegrityPipeline().validate_and_reconcile([obs('p1','a'*64),obs('p2','a'*64)])
    assert r.status=='PASS' and r.selected_provider is None or r.selected_provider in {'p1','p2'}
    assert not r.disagreement


def test_integrity_pipeline_surfaces_disagreement():
    r=DataIntegrityPipeline().validate_and_reconcile([obs('p1','a'*64),obs('p2','b'*64)])
    assert r.status=='REVIEW' and r.disagreement and r.selected_provider is None
