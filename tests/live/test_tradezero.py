import pytest
from lowcap_short_system.live.tradezero import TradeZeroClient, TradeZeroLocate, TradeZeroOrderRouter
from lowcap_short_system.live.transport import RecordingTransport
from lowcap_short_system.live.safety import LiveNotArmed, ARM_FLAG
from lowcap_short_system.observability.audit import AuditLog


def test_locate_dry_run_simulates_and_logs_but_never_networks(tmp_path):
    audit = AuditLog(str(tmp_path / "a.jsonl"))
    transport = RecordingTransport()
    client = TradeZeroClient(dry_run=True, transport=transport, audit=audit)
    r = TradeZeroLocate(client).locate("TICK", 5000)
    assert r.ok and r.located_shares == 5000 and r.reason == "dry-run simulated"
    assert transport.calls == []  # nothing sent
    kinds = [e["kind"] for e in audit.read()]
    assert kinds and all(k == "DRYRUN_API" for k in kinds)  # all calls logged as dry-run


def test_order_dry_run_returns_simulated_fill_and_sends_nothing(tmp_path):
    audit = AuditLog(str(tmp_path / "a.jsonl"))
    transport = RecordingTransport()
    client = TradeZeroClient(dry_run=True, transport=transport, audit=audit)
    pos = TradeZeroOrderRouter(client).place_short("TICK", 1000, 4.20, 4.55)
    assert pos.qty == 1000 and pos.stop_price == 4.55
    assert transport.calls == []  # no order transmitted
    assert any(e.get("path") == "/orders" for e in audit.read())


def test_live_order_refuses_unless_armed(monkeypatch):
    monkeypatch.delenv(ARM_FLAG, raising=False)  # not armed
    transport = RecordingTransport()
    client = TradeZeroClient(dry_run=False, transport=transport)
    with pytest.raises(LiveNotArmed):
        TradeZeroOrderRouter(client).place_short("TICK", 1000, 4.20, 4.55)
    assert transport.calls == []  # cannot trade by accident — nothing sent


def test_router_is_usable_as_oms_order_router():
    # structural check: the live router satisfies the OMS OrderRouter seam
    from lowcap_short_system.execution.oms import submit_short, ShortDecision, RiskParams
    from lowcap_short_system.locate.provider import MockLocateProvider

    router = TradeZeroOrderRouter(TradeZeroClient(dry_run=True))
    res = submit_short(
        ShortDecision("TICK", 5.0, 5.5, 1_000_000),
        RiskParams(100_000, 0.5, 2.0, 20_000, 5000),
        MockLocateProvider(),
        router,
    )
    assert res.ok and res.position is not None and res.position.symbol == "TICK"
