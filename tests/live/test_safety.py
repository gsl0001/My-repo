import pytest
from lowcap_short_system.live.safety import is_armed, require_armed, LiveNotArmed, ARM_FLAG, ARM_VALUE

SECRETS = ("TRADEZERO_API_KEY", "TRADEZERO_API_SECRET", "POLYGON_API_KEY")


def _disarm(monkeypatch):
    monkeypatch.delenv(ARM_FLAG, raising=False)
    for s in SECRETS:
        monkeypatch.delenv(s, raising=False)


def test_not_armed_by_default(monkeypatch):
    _disarm(monkeypatch)
    assert is_armed() is False


def test_require_armed_raises_when_unarmed(monkeypatch):
    _disarm(monkeypatch)
    with pytest.raises(LiveNotArmed):
        require_armed()


def test_flag_without_secrets_is_not_armed(monkeypatch):
    _disarm(monkeypatch)
    monkeypatch.setenv(ARM_FLAG, ARM_VALUE)  # flag but no creds
    assert is_armed() is False


def test_armed_only_with_exact_flag_and_all_secrets(monkeypatch):
    for s in SECRETS:
        monkeypatch.setenv(s, "x")
    monkeypatch.setenv(ARM_FLAG, "yes")  # wrong value
    assert is_armed() is False
    monkeypatch.setenv(ARM_FLAG, ARM_VALUE)
    assert is_armed() is True
