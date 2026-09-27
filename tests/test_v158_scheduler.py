from orion.runtime.scheduler import UniverseResearchScheduler

def test_scheduler_priority_order_and_chunks():
    s=UniverseResearchScheduler(); p=s.plan(['B','A','C'],priorities={'C':10,'A':5},chunk_size=2)
    assert p.security_order==('C','A','B') and len(p.job_keys)==2
