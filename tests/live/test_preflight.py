from lowcap_short_system.live.preflight import preflight
from lowcap_short_system.live.safety import ARM_FLAG, ARM_VALUE

SECRETS = ("TRADEZERO_API_KEY", "TRADEZERO_API_SECRET", "POLYGON_API_KEY")


def _clear(monkeypatch):
    monkeypatch.delenv(ARM_FLAG, raising=False)
    for s in SECRETS:
        monkeypatch.delenv(s, raising=False)


def test_paper_ready_without_secrets(monkeypatch):
    _clear(monkeypatch)
    assert preflight("paper").ready is True


def test_live_not_ready_without_arming(monkeypatch):
    _clear(monkeypatch)
    res = preflight("live")
    assert res.ready is False
    assert any(c.name == "live_armed" and not c.ok for c in res.checks)


def test_live_ready_when_armed_and_secrets(monkeypatch):
    for s in SECRETS:
        monkeypatch.setenv(s, "x")
    monkeypatch.setenv(ARM_FLAG, ARM_VALUE)
    assert preflight("live").ready is True
