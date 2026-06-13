import pytest
from lowcap_short_system.locate.provider import (
    MockLocateProvider, TradeZeroLocateProvider, LocateResult,
)


def test_full_availability_by_default():
    r = MockLocateProvider().locate("TICK", 5000)
    assert r.ok and r.located_shares == 5000 and r.cost_per_share == 0.02


def test_partial_locate():
    r = MockLocateProvider({"BBLG": 1200}).locate("BBLG", 5000)
    assert r.ok and r.located_shares == 1200


def test_no_borrow_fails_closed():
    r = MockLocateProvider({"GNSX": 0}).locate("GNSX", 5000)
    assert r.ok is False and r.located_shares == 0 and r.reason == "no borrow"


def test_live_provider_is_stubbed():
    with pytest.raises(NotImplementedError):
        TradeZeroLocateProvider().locate("TICK", 100)


def test_result_is_frozen_dataclass():
    r = LocateResult("X", 100, 0.03, True)
    with pytest.raises(Exception):
        r.located_shares = 200  # type: ignore[misc]
