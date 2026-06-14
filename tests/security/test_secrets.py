import pytest
from lowcap_short_system.security.secrets import get_secret, missing_secrets, MissingSecret


def test_get_secret_raises_when_unset(monkeypatch):
    monkeypatch.delenv("TRADEZERO_API_KEY", raising=False)
    with pytest.raises(MissingSecret):
        get_secret("TRADEZERO_API_KEY")


def test_get_secret_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "abc123")
    assert get_secret("POLYGON_API_KEY") == "abc123"


def test_missing_secrets_lists_unset(monkeypatch):
    for n in ("TRADEZERO_API_KEY", "TRADEZERO_API_SECRET", "POLYGON_API_KEY"):
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("POLYGON_API_KEY", "x")
    missing = missing_secrets()
    assert "POLYGON_API_KEY" not in missing
    assert "TRADEZERO_API_KEY" in missing and "TRADEZERO_API_SECRET" in missing
