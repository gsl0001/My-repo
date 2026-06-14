import pytest
from lowcap_short_system.run.session import TradingSession
from lowcap_short_system.execution.paper import PaperBroker
from lowcap_short_system.execution.oms import RiskParams
from lowcap_short_system.risk.breakers import BreakerLimits
from lowcap_short_system.locate.provider import MockLocateProvider
from lowcap_short_system.observability.audit import AuditLog
from lowcap_short_system.live.safety import LiveNotArmed, ARM_FLAG
from lowcap_short_system.microstructure.sim import scenarios

RISK = RiskParams(account_equity=100_000, risk_per_trade_pct=0.5, max_adv_pct=2.0,
                  hard_dollar_cap=20_000, requested_shares=5000)
LIM = BreakerLimits(daily_drawdown_pct=-4.0, max_positions=6, max_gross_short=150_000, consecutive_losses=3)


def make_session(broker, audit, locate=None, mode="paper"):
    return TradingSession(
        symbol="TICK", locate_provider=locate or MockLocateProvider(), broker=broker, audit=audit,
        risk=RISK, breaker_limits=LIM, adv_shares=1_000_000, mode=mode,
    )


def test_paper_session_enters_on_pump_fade(tmp_path):
    broker = PaperBroker()
    audit = AuditLog(str(tmp_path / "a.jsonl"))
    sess = make_session(broker, audit)
    sess.run(scenarios.pump_fade_absorption())
    assert "TICK" in broker.positions                       # a paper short was opened
    assert any(r.ok for r in sess.results)
    assert any(e["kind"] == "ORDER" for e in audit.read())  # audited


def test_no_locate_blocks_entry(tmp_path):
    broker = PaperBroker()
    audit = AuditLog(str(tmp_path / "a.jsonl"))
    sess = make_session(broker, audit, locate=MockLocateProvider({"TICK": 0}))
    sess.run(scenarios.pump_fade_absorption())
    assert broker.positions == {}                            # Reg SHO fail-closed: nothing opened
    assert any(e["kind"] == "REJECT" for e in audit.read())


def test_live_mode_requires_arming(tmp_path, monkeypatch):
    monkeypatch.delenv(ARM_FLAG, raising=False)
    with pytest.raises(LiveNotArmed):
        make_session(PaperBroker(), AuditLog(str(tmp_path / "a.jsonl")), mode="live")
