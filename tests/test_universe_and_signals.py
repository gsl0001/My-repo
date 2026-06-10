from dataclasses import replace
from datetime import datetime, timedelta, timezone

from lowcap_short_system.data.models import BorrowInfo, Filing
from lowcap_short_system.signals import SignalEngine, UniverseFilter
from lowcap_short_system.signals import scores


def test_good_candidate_passes(cfg, good_snapshot, good_borrow):
    verdict = UniverseFilter(cfg.universe).evaluate(good_snapshot, good_borrow)
    assert verdict.passed
    assert not verdict.low_float_flag


def test_rejections_are_explained(cfg, good_snapshot):
    f = UniverseFilter(cfg.universe)
    good_snapshot.price = 0.50
    good_snapshot.exchange = "OTC"
    verdict = f.evaluate(good_snapshot, None)
    assert not verdict.passed
    joined = " ".join(verdict.reasons)
    assert "below floor" in joined
    assert "exchange" in joined
    assert "borrow" in joined


def test_hard_borrow_fee_cap_excludes(cfg, good_snapshot, good_borrow):
    expensive = replace(good_borrow, fee_rate_pct=350.0)
    verdict = UniverseFilter(cfg.universe).evaluate(good_snapshot, expensive)
    assert not verdict.passed


def test_low_float_flags_but_does_not_exclude(cfg, good_snapshot, good_borrow):
    good_snapshot.float_shares = 10_000_000
    verdict = UniverseFilter(cfg.universe).evaluate(good_snapshot, good_borrow)
    assert verdict.passed
    assert verdict.low_float_flag


def test_trigger_gate_requires_rvol_and_move(cfg, good_snapshot):
    f = UniverseFilter(cfg.universe)
    assert f.trigger_gate(good_snapshot)
    quiet = replace_day_volume(good_snapshot, 1_000_000)  # 0.5x RVOL
    assert not f.trigger_gate(quiet)


def replace_day_volume(snap, vol):
    snap.day_volume = vol
    return snap


def test_pump_fade_score_zero_when_red(good_snapshot):
    good_snapshot.prev_close = 6.0  # down on the day
    assert scores.pump_fade_score(good_snapshot) == 0.0


def test_dilution_score_decays_with_age():
    now = datetime(2026, 6, 10, tzinfo=timezone.utc)
    fresh = [Filing("PUMP", "424B5", now - timedelta(days=1))]
    stale = [Filing("PUMP", "424B5", now - timedelta(days=29))]
    assert scores.dilution_score(fresh, now) > scores.dilution_score(stale, now)
    assert scores.dilution_score([Filing("PUMP", "424B5", now - timedelta(days=60))], now) == 0.0


def test_signal_engine_ranks_and_filters(cfg, good_snapshot, good_borrow):
    engine = SignalEngine(cfg.universe)
    no_borrow = BorrowInfo(symbol="DEAD", shares_available=0, fee_rate_pct=0.0)
    dead = replace_snapshot_symbol(good_snapshot, "DEAD")
    candidates = engine.build_candidates(
        [good_snapshot, dead],
        {"PUMP": good_borrow, "DEAD": no_borrow},
    )
    assert [c.symbol for c in candidates] == ["PUMP"]
    assert candidates[0].triggered
    assert 0 < candidates[0].composite <= 1


def replace_snapshot_symbol(snap, symbol):
    import copy

    out = copy.copy(snap)
    out.symbol = symbol
    return out
