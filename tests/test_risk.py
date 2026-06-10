from datetime import datetime, timezone

import pytest

from lowcap_short_system.data.models import HaltState, Position
from lowcap_short_system.risk import (
    AccountCircuitBreakers,
    EntryAction,
    KillSwitch,
    PositionAction,
    PositionSizer,
    SqueezeGuard,
)
from lowcap_short_system.risk.kill_switch import TradingHalted


def make_position(entry_price=5.0, shares=1000):
    return Position(
        symbol="PUMP",
        shares=shares,
        entry_price=entry_price,
        entry_time=datetime(2026, 6, 10, 14, 0, tzinfo=timezone.utc),
        located_shares=shares,
        stop_price=entry_price * 1.15,
        target_price=entry_price * 0.85,
    )


# ---- squeeze guard ----------------------------------------------------------


def test_entry_ok_on_clean_setup(cfg, good_snapshot, good_borrow):
    guard = SqueezeGuard(cfg.squeeze)
    assert guard.evaluate_entry(good_snapshot, good_borrow).action == EntryAction.OK


def test_entry_caution_on_big_gain(cfg, good_snapshot, good_borrow):
    good_snapshot.prev_close = good_snapshot.price / 1.6  # +60%
    verdict = SqueezeGuard(cfg.squeeze).evaluate_entry(good_snapshot, good_borrow)
    assert verdict.action == EntryAction.REDUCE


def test_entry_abort_on_accelerating_parabolic(cfg, good_snapshot, good_borrow):
    good_snapshot.prev_close = good_snapshot.price / 2.5  # +150%
    good_snapshot.pulled_back = False
    verdict = SqueezeGuard(cfg.squeeze).evaluate_entry(good_snapshot, good_borrow)
    assert verdict.action == EntryAction.ABORT


def test_entry_abort_on_halt_up(cfg, good_snapshot, good_borrow):
    good_snapshot.halt_state = HaltState.HALT_UP
    verdict = SqueezeGuard(cfg.squeeze).evaluate_entry(good_snapshot, good_borrow)
    assert verdict.action == EntryAction.ABORT


def test_entry_abort_on_tiny_float(cfg, good_snapshot, good_borrow):
    good_snapshot.float_shares = 4_000_000
    verdict = SqueezeGuard(cfg.squeeze).evaluate_entry(good_snapshot, good_borrow)
    assert verdict.action == EntryAction.ABORT


def test_force_exit_on_adverse_move(cfg, good_snapshot, good_borrow):
    guard = SqueezeGuard(cfg.squeeze)
    pos = make_position(entry_price=4.0)
    good_snapshot.price = 4.0 * 1.16  # 16% against the short
    verdict = guard.evaluate_position(pos, good_snapshot, good_borrow)
    assert verdict.action == PositionAction.FORCE_EXIT


def test_force_exit_on_borrow_recall(cfg, good_snapshot, good_borrow):
    guard = SqueezeGuard(cfg.squeeze)
    pos = make_position(entry_price=good_snapshot.price)
    verdict = guard.evaluate_position(pos, good_snapshot, good_borrow, borrow_recalled=True)
    assert verdict.action == PositionAction.FORCE_EXIT


def test_hold_when_winning(cfg, good_snapshot, good_borrow):
    guard = SqueezeGuard(cfg.squeeze)
    pos = make_position(entry_price=6.0)  # price 5.20 -> winning short
    verdict = guard.evaluate_position(pos, good_snapshot, good_borrow)
    assert verdict.action == PositionAction.HOLD


# ---- sizing -----------------------------------------------------------------


def test_size_respects_all_caps(cfg, good_snapshot):
    sizer = PositionSizer(cfg.risk)
    res = sizer.size(good_snapshot, located_shares=100_000)
    # risk budget: 1000 / (5.20 * 0.15) = ~1282 shares, the binding constraint
    assert res.shares == int(cfg.risk.target_risk_dollars / (good_snapshot.price * 0.15))
    assert res.shares * good_snapshot.price <= cfg.risk.max_position_dollars
    assert res.shares <= good_snapshot.adv_shares_20d * cfg.risk.max_pct_of_adv / 100


def test_size_capped_by_locate(cfg, good_snapshot):
    res = PositionSizer(cfg.risk).size(good_snapshot, located_shares=100)
    assert res.shares == 100
    assert "located shares" in res.constraints


def test_low_float_and_caution_haircuts(cfg, good_snapshot):
    sizer = PositionSizer(cfg.risk)
    full = sizer.size(good_snapshot, located_shares=100_000).shares
    cut = sizer.size(
        good_snapshot, located_shares=100_000, caution_factor=0.5, low_float=True
    ).shares
    assert cut == int(int(full * 0.5) * 0.5) or cut == pytest.approx(full * 0.25, abs=2)


# ---- circuit breakers -------------------------------------------------------


def test_drawdown_trips_and_latches(cfg):
    brk = AccountCircuitBreakers(cfg.risk, starting_equity=50_000)
    brk.record_realized(-2_500)  # -5% > 4% limit
    assert brk.check_drawdown()
    brk.record_realized(+5_000)  # recovery does NOT untrip
    assert brk.tripped
    state = brk.allows_new_entry([], marks={})
    assert not state.allowed


def test_max_positions_and_gross_exposure(cfg):
    brk = AccountCircuitBreakers(cfg.risk, starting_equity=50_000)
    positions = [make_position() for _ in range(cfg.risk.max_concurrent_positions)]
    state = brk.allows_new_entry(positions, marks={})
    assert not state.allowed
    assert any("concurrent" in r for r in state.reasons)

    big = [make_position(entry_price=50.0, shares=2100)]  # $105k gross
    state = brk.allows_new_entry(big, marks={})
    assert any("gross" in r for r in state.reasons)


def test_per_position_max_loss(cfg):
    brk = AccountCircuitBreakers(cfg.risk, starting_equity=50_000)
    pos = make_position(entry_price=5.0)
    assert brk.position_max_loss_breached(pos, price=5.0 * 1.21)
    assert not brk.position_max_loss_breached(pos, price=5.0 * 1.10)


# ---- kill switch ------------------------------------------------------------


def test_kill_switch_blocks_and_latches():
    ks = KillSwitch()
    ks.assert_trading_allowed()
    ks.engage("manual")
    assert ks.engaged
    with pytest.raises(TradingHalted):
        ks.assert_trading_allowed()
    ks.engage("second call is a no-op")
    assert ks.reason == "manual"
