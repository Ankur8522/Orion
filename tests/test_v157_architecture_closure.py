from pathlib import Path

from orion.brain.kernel import IntelligenceCase
from orion.brain.persistence import PersistentProgressiveMemory
from orion.brain.progressive import Belief
from orion.decision.plane import AgentFinding
from orion.execution.paper import PaperExecutionBook
from orion.ops.journal import RunJournal
from orion.runtime.control_plane import OrionControlPlane


def _case(cycle="c1"):
    return IntelligenceCase(
        security_id="ABC", decision_time="2026-09-27T00:00:00Z", thesis="durable growth",
        evidence_ids=("e1",), findings=(AgentFinding("fundamental", "SUPPORT", ("e1",), ("growth",)),),
        belief=Belief("t1", .65, .8, .75), cycle_id=cycle, priority_score=70,
    )


def test_progressive_memory_survives_restart(tmp_path):
    p = tmp_path / "brain.db"
    m1 = PersistentProgressiveMemory(p)
    from orion.brain.progressive_loop import ProgressiveReasoningLoop
    ProgressiveReasoningLoop(memory=m1).run_cycle(cycle_id="c1", belief=Belief("t", .6, .7, .7))
    m1.close()
    m2 = PersistentProgressiveMemory(p)
    assert len(m2.history("t")) == 1
    assert m2.last("t").cycle_id == "c1"
    m2.close()


def test_journal_is_hash_chained_and_persistent(tmp_path):
    p = tmp_path / "journal.log"
    j = RunJournal(p)
    j.append("A", {"x": 1})
    j.append("B", {"x": 2})
    assert j.verify() and len(j.events()) == 2
    j2 = RunJournal(p)
    assert j2.verify() and j2.events()[-1].event_hash == j.events()[-1].event_hash


def test_paper_lifecycle_and_pnl():
    b = PaperExecutionBook()
    o = b.stage(security_id="ABC", target_weight=.2, current_weight=0, allowed=True, reason="RESEARCH_SUPPORTED", lineage_hash="a"*64)
    b.fill(o.order_id, quantity=10, price=100, side="BUY", timestamp="2026-09-27T10:00:00Z")
    p = b.mark("ABC", 110)
    assert p.quantity == 10 and p.unrealized_pnl == 100
    assert b.live_trading_enabled() is False


def test_control_plane_closes_runtime_loop(tmp_path):
    cp = OrionControlPlane(state_path=tmp_path / "brain.db", journal_path=tmp_path / "journal.log")
    result = cp.run_case(_case())
    assert result.health["status"] == "OK"
    assert result.health["journal_integrity"] is True
    assert result.health["live_trading_enabled"] is False
