from decimal import Decimal
from orion.company.model import CompanyPeriod, build_company_model
from orion.research.dossier import build_research_dossier


def model():
    return build_company_model('AAA', [
        CompanyPeriod('2025-03-31', revenue=100, ebitda=20, pat=10, cfo=11, capex=4, debt=10, cash=3, receivables=15, equity=50, invested_capital=60),
        CompanyPeriod('2026-03-31', revenue=120, ebitda=27, pat=14, cfo=15, capex=5, debt=12, cash=4, receivables=16, equity=58, invested_capital=65),
    ])


def test_dossier_integrates_layers():
    d=build_research_dossier(model(), as_of='2026-04-01', sector='capital_goods',
        sector_facts={'revenue':120,'ebitda':27,'order_book':300,'receivables':16,'capex':5},
        market_rows=[
            {'event_time':f'2026-03-{24+i:02d}','close':100+i,'volume':10} for i in range(6)
        ] + [{'event_time':'2026-03-31','close':106,'volume':20}],
        valuation_kwargs={'price':103,'shares':10,'pat':14,'equity':58,'ebitda':27,'fcf':10,'debt':12,'cash':4},
        evidence_ids=['e1'], source_ids=['nse'], evidence_states=['EVIDENCE_SUPPORTED'], catalysts=['ORDER_BOOK'], headwinds=['VALUATION'])
    assert d.security_id == 'AAA'
    assert d.market.volume_state == 'EXPANSION'
    assert d.company.valuation.pe is not None
    assert 'CATALYST:ORDER_BOOK' in d.thesis.claims
    assert d.thesis.state.value == 'EVIDENCE_SUPPORTED'


def test_unsupported_evidence_blocks_thesis():
    d=build_research_dossier(model(), as_of='2026-04-01', evidence_ids=['e1'], evidence_states=['REVIEW'])
    assert d.thesis.state.value == 'BLOCKED'
    assert 'EVIDENCE_STATE_NOT_SUPPORTED' in d.thesis.blockers


def test_thesis_delta_tracks_change():
    first=build_research_dossier(model(), as_of='2026-04-01', evidence_ids=['e1'], evidence_states=['EVIDENCE_SUPPORTED'], catalysts=['A'])
    second=build_research_dossier(model(), as_of='2026-04-02', evidence_ids=['e2'], evidence_states=['EVIDENCE_SUPPORTED'], catalysts=['B'], previous_thesis=first.thesis)
    assert second.thesis_delta is not None
    assert 'e2' in second.thesis_delta.added_evidence
    assert 'e1' in second.thesis_delta.removed_evidence
    assert any(x.startswith('ADDED_CLAIM:CATALYST:B') for x in second.change_log)


def test_no_evidence_is_explicit():
    d=build_research_dossier(model(), as_of='2026-04-01')
    assert d.thesis.state.value == 'UNCERTAIN'
    assert 'NO_EVIDENCE_LINKED' in d.warnings
