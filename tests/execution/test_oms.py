from lowcap_short_system.execution.oms import ShortDecision, RiskParams, submit_short
from lowcap_short_system.execution.paper import PaperBroker
from lowcap_short_system.locate.provider import MockLocateProvider

DEC = ShortDecision(symbol="TICK", entry_price=5.0, stop_price=5.5, adv_shares=1_000_000)
RISK = RiskParams(account_equity=100_000, risk_per_trade_pct=0.5, max_adv_pct=2.0,
                  hard_dollar_cap=20_000, requested_shares=5000)


def test_happy_path_places_short_with_stop():
    broker = PaperBroker()
    res = submit_short(DEC, RISK, MockLocateProvider(), broker)
    assert res.ok and res.position is not None
    assert res.position.stop_price == 5.5
    assert "TICK" in broker.positions
    assert res.located == 5000 and res.locate_cost > 0


def test_reg_sho_fails_closed_without_locate():
    broker = PaperBroker()
    res = submit_short(DEC, RISK, MockLocateProvider({"TICK": 0}), broker)
    assert res.ok is False and "locate" in res.reason
    assert broker.positions == {}  # no position opened


def test_halt_blocks_submission():
    broker = PaperBroker()
    res = submit_short(DEC, RISK, MockLocateProvider(), broker, halted=True)
    assert res.ok is False and res.reason == "trading halted"
    assert broker.positions == {}


def test_size_capped_by_partial_locate():
    broker = PaperBroker()
    res = submit_short(DEC, RISK, MockLocateProvider({"TICK": 300}), broker)
    assert res.ok and res.position is not None
    assert res.position.qty <= 300  # cannot short more than located
