import pytest
from orion.model.world import WorldModel
from orion.model.scenario import Shock, Scenario, ScenarioEngine

def engine():
    w=WorldModel(); w.add('rates','hits','banks',0.8); w.add('banks','hits','credit',0.5); return ScenarioEngine(w)

def test_counterfactual_propagates_through_graph():
    r=engine().run([Scenario('s1','rate shock',1.0,(Shock('rates',-1.0),),180)])
    assert dict(r[0].impacts)['rates']==-1.0
    assert dict(r[0].impacts)['banks']==-0.8
    assert dict(r[0].impacts)['credit']==-0.4
    assert r[0].downside_tail < 0
    assert len(r[0].lineage_hash)==64

def test_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match='SCENARIO_PROBABILITIES'):
        engine().run([Scenario('a','a',.6,(),30)])

def test_positive_negative_scenarios_produce_dispersion():
    r=engine().run([
        Scenario('bull','bull',.5,(Shock('rates',.5),),90),
        Scenario('bear','bear',.5,(Shock('rates',-.5),),90),
    ])
    assert r[0].dispersion == r[1].dispersion
    assert r[0].upside_tail > 0
    assert r[1].downside_tail < 0
