from orion.portfolio.intelligence import Holding, FactorExposure, PortfolioIntelligenceBrain

def test_portfolio_intelligence_assesses_concentration_and_stress():
    brain=PortfolioIntelligenceBrain()
    out=brain.assess(
        (Holding('A',0.70,beta=1.2,volatility=.3),Holding('B',0.20,beta=.9,volatility=.2),Holding('C',0.10,beta=.7,volatility=.1)),
        (FactorExposure('rates',1.2,-.8),FactorExposure('credit',.8,-.5)),
        (-1.4,.3), robustness=.8)
    assert out.gross_exposure == 1.0
    assert out.concentration_hhi > .5
    assert out.scenario_loss == -1.4
    assert 'REDUCE_CONCENTRATION' in out.priority_actions
    assert out.lineage_hash

def test_portfolio_intelligence_is_deterministic():
    args=((Holding('A',.5),Holding('B',.5)),(FactorExposure('x',.2,.1),),(-.2,.2),.7)
    a=PortfolioIntelligenceBrain().assess(*args)
    b=PortfolioIntelligenceBrain().assess(*args)
    assert a == b
