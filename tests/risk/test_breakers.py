from lowcap_short_system.risk.breakers import (
    BreakerLimits, AccountMetrics, check_breakers,
)

LIM = BreakerLimits(daily_drawdown_pct=-4.0, max_positions=6, max_gross_short=150_000, consecutive_losses=3)


def metrics(**kw) -> AccountMetrics:
    d = dict(drawdown_pct=-1.0, positions=2, gross_short=50_000, loss_streak=0)
    d.update(kw)
    return AccountMetrics(**d)


def test_clean_state_not_halted():
    s = check_breakers(metrics(), LIM)
    assert s.halted is False and s.reasons == ()


def test_drawdown_trips():
    assert "daily drawdown limit" in check_breakers(metrics(drawdown_pct=-4.0), LIM).reasons


def test_max_positions_trips():
    assert "max positions" in check_breakers(metrics(positions=6), LIM).reasons


def test_gross_short_trips():
    assert "gross short cap" in check_breakers(metrics(gross_short=150_000), LIM).reasons


def test_loss_streak_trips():
    assert "consecutive losses" in check_breakers(metrics(loss_streak=3), LIM).reasons


def test_multiple_reasons_all_reported():
    s = check_breakers(metrics(drawdown_pct=-5.0, positions=9), LIM)
    assert s.halted and len(s.reasons) == 2
