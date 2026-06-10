import pytest

from lowcap_short_system.config import LocateConfig, SystemConfig
from lowcap_short_system.execution.broker import (
    BrokerError,
    LocateQuote,
    Order,
    OrderSide,
    PaperBroker,
    TradeZeroBroker,
)
from lowcap_short_system.locate.orchestrator import LocateOrchestrator, LocateOutcome


def make_orchestrator(broker, **overrides):
    cfg = LocateConfig(**overrides) if overrides else LocateConfig()
    return LocateOrchestrator(broker, cfg)


def test_locate_reserved_when_cheap():
    broker = PaperBroker(locate_inventory={"PUMP": 50_000}, locate_cost_per_share=0.005)
    orch = make_orchestrator(broker)
    result = orch.secure_locate("PUMP", price=5.0, shares_wanted=1_000)
    assert result.outcome == LocateOutcome.RESERVED
    assert result.reservation.shares == 1_000
    assert orch.ledger.remaining_shares("PUMP") == 1_000


def test_locate_cost_gate_drops_expensive():
    # edge: 5.0 * 10% * 1000 * 0.55 = $275; gate at 20% = $55; cost = $100
    broker = PaperBroker(locate_inventory={"PUMP": 50_000}, locate_cost_per_share=0.10)
    orch = make_orchestrator(broker)
    result = orch.secure_locate("PUMP", price=5.0, shares_wanted=1_000)
    assert result.outcome == LocateOutcome.TOO_EXPENSIVE
    assert orch.ledger.located_shares("PUMP") == 0


def test_no_availability_drops_symbol():
    broker = PaperBroker(locate_inventory={})
    result = make_orchestrator(broker).secure_locate("PUMP", 5.0, 1_000)
    assert result.outcome == LocateOutcome.NO_AVAILABILITY


def test_partial_locate_caps_shares():
    broker = PaperBroker(locate_inventory={"PUMP": 300}, locate_cost_per_share=0.001)
    orch = make_orchestrator(broker)
    result = orch.secure_locate("PUMP", 5.0, 1_000)
    assert result.outcome == LocateOutcome.RESERVED
    assert result.reservation.shares == 300


def test_api_failure_fails_closed():
    class FlakyBroker(PaperBroker):
        def quote_locate(self, symbol, shares):
            raise BrokerError("auth failure")

    orch = make_orchestrator(FlakyBroker(), locate_retry_budget=1)
    result = orch.secure_locate("PUMP", 5.0, 1_000)
    assert result.outcome == LocateOutcome.FAILED


def test_unused_locate_fee_is_sunk_cost():
    broker = PaperBroker(locate_inventory={"PUMP": 50_000}, locate_cost_per_share=0.01)
    orch = make_orchestrator(broker)
    orch.secure_locate("PUMP", 5.0, 1_000)
    orch.ledger.use("PUMP", 400)
    report = orch.end_of_day_reconcile()
    assert report["fees_paid"] == pytest.approx(10.0)
    assert report["unused_fee_sunk_cost"] == pytest.approx(6.0)


def test_tradezero_skeleton_fails_closed():
    tz = TradeZeroBroker()
    with pytest.raises(BrokerError):
        tz.quote_locate("PUMP", 100)
    with pytest.raises(BrokerError):
        tz.submit_order(Order(symbol="PUMP", side=OrderSide.SELL_SHORT, shares=1, limit_price=None))


# ---- order manager Reg SHO + kill-switch gates ----------------------------------


def build_order_stack(locate_inventory=None):
    from lowcap_short_system.execution.order_manager import OrderManager
    from lowcap_short_system.risk.circuit_breakers import AccountCircuitBreakers
    from lowcap_short_system.risk.kill_switch import KillSwitch

    cfg = SystemConfig()
    broker = PaperBroker(locate_inventory=locate_inventory or {"PUMP": 10_000},
                         locate_cost_per_share=0.001)
    broker.set_price("PUMP", 5.0)
    locates = LocateOrchestrator(broker, cfg.locate)
    breakers = AccountCircuitBreakers(cfg.risk, starting_equity=50_000)
    ks = KillSwitch()
    om = OrderManager(broker, locates, breakers, ks, cfg.risk)
    return cfg, broker, locates, breakers, ks, om


def test_no_locate_no_short():
    *_, om = build_order_stack()
    result = om.enter_short("PUMP", 5.0, 500)
    assert not result.accepted
    assert "Reg SHO" in result.reason


def test_entry_capped_to_located_shares():
    cfg, broker, locates, breakers, ks, om = build_order_stack()
    locates.secure_locate("PUMP", 5.0, 300)
    result = om.enter_short("PUMP", 5.0, 500)
    assert result.accepted
    assert result.position.shares == 300


def test_kill_switch_blocks_entries():
    cfg, broker, locates, breakers, ks, om = build_order_stack()
    locates.secure_locate("PUMP", 5.0, 500)
    ks.engage("test")
    result = om.enter_short("PUMP", 5.0, 500)
    assert not result.accepted
    assert "kill switch" in result.reason


def test_stop_and_target_exits():
    cfg, broker, locates, breakers, ks, om = build_order_stack()
    locates.secure_locate("PUMP", 5.0, 1_000)
    om.enter_short("PUMP", 5.0, 1_000)

    broker.set_price("PUMP", 4.2)  # below 15% target
    closed = om.manage("PUMP", 4.2)
    assert closed is not None
    assert closed.realized_pnl > 0
    assert breakers.realized_pnl_today > 0
    assert "PUMP" not in om.positions


def test_stop_hit_records_loss():
    cfg, broker, locates, breakers, ks, om = build_order_stack()
    locates.secure_locate("PUMP", 5.0, 1_000)
    om.enter_short("PUMP", 5.0, 1_000)
    broker.set_price("PUMP", 6.0)  # 20% adverse, past 15% stop
    closed = om.manage("PUMP", 6.0)
    assert closed is not None
    assert closed.realized_pnl < 0


def test_flatten_all_covers_everything():
    cfg, broker, locates, breakers, ks, om = build_order_stack()
    locates.secure_locate("PUMP", 5.0, 1_000)
    om.enter_short("PUMP", 5.0, 1_000)
    om.flatten_all("eod")
    assert om.positions == {}
    assert broker.open_shorts.get("PUMP", 0) == 0
