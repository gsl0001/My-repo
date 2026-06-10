"""End-to-end day in the life of the live engine, on the PaperBroker."""

import copy

from lowcap_short_system.config import SystemConfig
from lowcap_short_system.engine import TradingEngine
from lowcap_short_system.execution.broker import PaperBroker


def build_engine(equity=50_000, inventory=10_000, locate_cost=0.001):
    cfg = SystemConfig()
    broker = PaperBroker(
        locate_inventory={"PUMP": inventory}, locate_cost_per_share=locate_cost
    )
    return cfg, broker, TradingEngine(cfg, broker, account_equity=equity)


def test_full_day_cycle(good_snapshot, good_borrow):
    cfg, broker, engine = build_engine()

    candidates = engine.premarket([good_snapshot], {"PUMP": good_borrow})
    assert [c.symbol for c in candidates] == ["PUMP"]
    assert engine.locates.ledger.remaining_shares("PUMP") > 0

    # intraday trigger -> short entry
    engine.on_snapshot(good_snapshot, good_borrow)
    assert "PUMP" in engine.orders.positions
    pos = engine.orders.positions["PUMP"]
    assert pos.shares <= engine.locates.ledger.located_shares("PUMP")

    # fade plays out -> target reversion exit
    faded = copy.copy(good_snapshot)
    faded.price = pos.target_price * 0.99
    engine.on_snapshot(faded, good_borrow)
    assert "PUMP" not in engine.orders.positions
    assert engine.breakers.realized_pnl_today > 0

    report = engine.end_of_day(marks={"PUMP": faded.price})
    assert report["fees_paid"] >= 0
    assert broker.open_shorts.get("PUMP", 0) == 0


def test_squeeze_force_exit_path(good_snapshot, good_borrow):
    cfg, broker, engine = build_engine()
    engine.premarket([good_snapshot], {"PUMP": good_borrow})
    engine.on_snapshot(good_snapshot, good_borrow)
    pos = engine.orders.positions["PUMP"]

    squeezing = copy.copy(good_snapshot)
    squeezing.price = pos.entry_price * 1.17  # > force_exit_adverse_pct
    engine.on_snapshot(squeezing, good_borrow)
    assert "PUMP" not in engine.orders.positions
    assert engine.breakers.realized_pnl_today < 0


def test_drawdown_breach_engages_kill_switch(good_snapshot, good_borrow):
    cfg, broker, engine = build_engine(equity=10_000)  # small account: 4% = $400
    engine.premarket([good_snapshot], {"PUMP": good_borrow})
    engine.on_snapshot(good_snapshot, good_borrow)
    pos = engine.orders.positions["PUMP"]

    blowout = copy.copy(good_snapshot)
    blowout.price = pos.entry_price * 1.16
    engine.on_snapshot(blowout, good_borrow)  # force exit -> big realized loss
    assert engine.kill_switch.engaged

    # no further entries while killed
    engine.on_snapshot(good_snapshot, good_borrow)
    assert engine.orders.positions == {}


def test_borrow_recall_force_exit(good_snapshot, good_borrow):
    cfg, broker, engine = build_engine()
    engine.premarket([good_snapshot], {"PUMP": good_borrow})
    engine.on_snapshot(good_snapshot, good_borrow)
    assert "PUMP" in engine.orders.positions
    engine.on_borrow_recall("PUMP", good_snapshot.price)
    assert "PUMP" not in engine.orders.positions


def test_no_locate_no_candidate(good_snapshot, good_borrow):
    cfg, broker, engine = build_engine(inventory=0)
    candidates = engine.premarket([good_snapshot], {"PUMP": good_borrow})
    assert candidates == []
    engine.on_snapshot(good_snapshot, good_borrow)
    assert engine.orders.positions == {}
