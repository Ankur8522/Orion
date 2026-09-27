from types import SimpleNamespace
from orion.research.coverage import build_coverage

def test_coverage_complete_and_blocked():
    report=build_coverage([
        SimpleNamespace(security_id='A',status='COMPLETE',stage='COMPLETE',reason=None),
        SimpleNamespace(security_id='B',status='BLOCKED',stage='EVIDENCE',reason='NO_EVIDENCE_LINKED'),
        SimpleNamespace(security_id='C',status='FAILED',stage='DOSSIER',reason='ValueError:x'),
    ])
    assert report.total==3
    assert report.complete==1 and report.blocked==1 and report.failed==1
    assert report.average_coverage_pct==40.0
    assert report.stocks[1].missing==('NO_EVIDENCE_LINKED',)
