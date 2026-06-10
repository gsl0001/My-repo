from datetime import datetime, timedelta, timezone

import pytest

from lowcap_short_system.backtest import BacktestEngine, CostModel, SlippageModel
from lowcap_short_system.backtest.engine import SymbolDay
from lowcap_short_system.data.models import Bar, BorrowInfo


def minute_bars(symbol, path, start_price, volume=1_000_000):
    """path: list of multipliers vs start price, one per minute bar."""
    t0 = datetime(2026, 6, 10, 13, 31, tzinfo=timezone.utc)
    bars = []
    prev = start_price
    for i, mult in enumerate(path):
        close = start_price * mult
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=t0 + timedelta(minutes=i),
                open=prev,
                high=max(prev, close) * 1.005,
                low=min(prev, close) * 0.995,
                close=close,
                volume=volume,
            )
        )
        prev = close
    return bars


def make_day(symbol="PUMP", path=None, borrow_fee=40.0, available=500_000):
    # spike to +40% then fade — the bread-and-butter setup
    path = path or [1.2, 1.3, 1.4, 1.38, 1.30, 1.20, 1.10, 1.05, 1.00, 0.98]
    return SymbolDay(
        symbol=symbol,
        bars=minute_bars(symbol, path, start_price=4.0),
        prev_close=4.0,
        market_cap=80_000_000,
        exchange="NASDAQ",
        adv_shares_20d=1_000_000,
        adv_dollar_20d=5_000_000,
        borrow=BorrowInfo(symbol=symbol, shares_available=available, fee_rate_pct=borrow_fee),
        float_shares=30_000_000,
    )


def test_fade_trade_wins_net_of_costs(cfg):
    engine = BacktestEngine(cfg)
    result = engine.run([make_day()])
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "target reversion"
    assert trade.gross_pnl > 0
    assert trade.net_pnl > 0
    assert trade.locate_fee > 0 and trade.borrow_fee > 0 and trade.commissions > 0
    assert trade.net_pnl < trade.gross_pnl  # costs actually subtracted


def test_squeeze_day_is_stopped_out(cfg):
    # relentless ramp: trigger then keep climbing through the stop
    path = [1.2, 1.3, 1.45, 1.6, 1.8, 2.0, 2.2, 2.4]
    result = BacktestEngine(cfg).run([make_day(path=path)])
    assert len(result.trades) == 1
    trade = result.trades[0]
    # the squeeze guard usually fires before the hard stop; either way the
    # loss is capped well below the full ramp
    assert trade.exit_reason == "stop hit" or trade.exit_reason.startswith("squeeze guard")
    assert trade.net_pnl < 0
    loss_pct = (trade.exit_price / trade.entry_price - 1) * 100
    assert loss_pct < cfg.risk.stop_distance_pct + 5


def test_eod_flatten_when_no_exit_hit(cfg):
    # fades a little but never reaches stop or target
    path = [1.2, 1.3, 1.25, 1.24, 1.23, 1.22, 1.21, 1.20]
    result = BacktestEngine(cfg).run([make_day(path=path)])
    assert result.trades[0].exit_reason == "EOD flatten"


def test_untriggered_day_skipped(cfg):
    path = [1.01, 1.02, 1.01, 1.00, 0.99]  # no move worth fading
    result = BacktestEngine(cfg).run([make_day(path=path)])
    assert not result.trades
    assert "never triggered" in result.skipped["PUMP"]


def test_universe_reject_skipped(cfg):
    day = make_day(available=0)  # no borrow
    result = BacktestEngine(cfg).run([day])
    assert not result.trades
    assert "borrow" in result.skipped["PUMP"]


def test_slippage_is_adverse_and_grows_with_participation():
    model = SlippageModel()
    bar = Bar("PUMP", datetime(2026, 6, 10, tzinfo=timezone.utc), 5, 5.1, 4.9, 5.0, 100_000)
    short_small = model.fill_price(bar, 1_000, "short")
    short_big = model.fill_price(bar, 100_000, "short")
    cover = model.fill_price(bar, 1_000, "cover")
    assert short_small < bar.close < cover  # always adverse
    assert short_big < short_small  # more size, worse fill


def test_borrow_fee_prorated():
    cm = CostModel()
    full_day = cm.borrow_fee(10_000, fee_rate_pct=252.0, minutes_held=390)
    assert full_day == pytest.approx(100.0)  # 252%/yr on $10k = $100/day
    half_day = cm.borrow_fee(10_000, fee_rate_pct=252.0, minutes_held=195)
    assert half_day == pytest.approx(50.0)


def test_summary_shape(cfg):
    result = BacktestEngine(cfg).run([make_day()])
    s = result.summary()
    assert set(s) == {"trades", "win_rate", "gross_pnl", "fees", "net_pnl", "skipped"}
