"""Event-driven intraday backtester.

Replays minute bars for one symbol-day at a time through the same signal,
sizing and squeeze-guard logic the live engine uses, with explicit slippage
and cost modeling (design section 6). Borrow availability and locate cost are
inputs per symbol-day, since historical TradeZero locate data isn't available;
treat locate costs as a sensitivity parameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..config import SystemConfig
from ..data.models import Bar, BorrowInfo, SymbolSnapshot
from ..risk.sizing import PositionSizer
from ..risk.squeeze_guard import EntryAction, PositionAction, SqueezeGuard
from ..signals.universe import UniverseFilter
from .costs import CostModel
from .slippage import SlippageModel


@dataclass
class SymbolDay:
    """One symbol-day of replayable data plus the reference context."""

    symbol: str
    bars: list[Bar]  # minute bars, ascending
    prev_close: float
    market_cap: float
    exchange: str
    adv_shares_20d: float
    adv_dollar_20d: float
    borrow: BorrowInfo
    float_shares: float | None = None
    dilution_score: float = 0.0


@dataclass
class TradeRecord:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    shares: int
    entry_price: float
    exit_price: float
    exit_reason: str
    gross_pnl: float
    locate_fee: float
    borrow_fee: float
    commissions: float

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.locate_fee - self.borrow_fee - self.commissions


@dataclass
class BacktestResult:
    trades: list[TradeRecord] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # symbol -> reason

    @property
    def net_pnl(self) -> float:
        return sum(t.net_pnl for t in self.trades)

    @property
    def gross_pnl(self) -> float:
        return sum(t.gross_pnl for t in self.trades)

    @property
    def total_fees(self) -> float:
        return sum(t.locate_fee + t.borrow_fee + t.commissions for t in self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.net_pnl > 0) / len(self.trades)

    def summary(self) -> dict:
        return {
            "trades": len(self.trades),
            "win_rate": round(self.win_rate, 3),
            "gross_pnl": round(self.gross_pnl, 2),
            "fees": round(self.total_fees, 2),
            "net_pnl": round(self.net_pnl, 2),
            "skipped": len(self.skipped),
        }


class BacktestEngine:
    def __init__(
        self,
        cfg: SystemConfig,
        slippage: SlippageModel | None = None,
        costs: CostModel | None = None,
    ):
        self.cfg = cfg
        self.universe = UniverseFilter(cfg.universe)
        self.guard = SqueezeGuard(cfg.squeeze)
        self.sizer = PositionSizer(cfg.risk)
        self.slippage = slippage or SlippageModel()
        self.costs = costs or CostModel()

    def run(self, days: list[SymbolDay]) -> BacktestResult:
        result = BacktestResult()
        for day in days:
            trade_or_reason = self._run_symbol_day(day)
            if isinstance(trade_or_reason, TradeRecord):
                result.trades.append(trade_or_reason)
            else:
                result.skipped[day.symbol] = trade_or_reason
        return result

    def _snapshot(self, day: SymbolDay, bar: Bar, cum_volume: int, up_bars: int, pulled_back: bool) -> SymbolSnapshot:
        return SymbolSnapshot(
            symbol=day.symbol,
            price=bar.close,
            prev_close=day.prev_close,
            market_cap=day.market_cap,
            exchange=day.exchange,
            adv_shares_20d=day.adv_shares_20d,
            adv_dollar_20d=day.adv_dollar_20d,
            float_shares=day.float_shares,
            day_volume=cum_volume,
            timestamp=bar.timestamp,
            consecutive_up_bars=up_bars,
            pulled_back=pulled_back,
        )

    def _run_symbol_day(self, day: SymbolDay) -> TradeRecord | str:
        if not day.bars:
            return "no bars"

        cum_volume = 0
        up_bars = 0
        day_high = 0.0
        entry: dict | None = None

        for i, bar in enumerate(day.bars):
            cum_volume += bar.volume
            up_bars = up_bars + 1 if bar.close > bar.open else 0
            pulled_back = bar.close < day_high * 0.97 if day_high > 0 else False
            day_high = max(day_high, bar.high)
            snap = self._snapshot(day, bar, cum_volume, up_bars, pulled_back)
            is_last_bar = i == len(day.bars) - 1

            if entry is None:
                if is_last_bar:
                    return "never triggered"
                verdict = self.universe.evaluate(snap, day.borrow)
                if not verdict.passed:
                    return "; ".join(verdict.reasons)
                if not self.universe.trigger_gate(snap):
                    continue
                guard = self.guard.evaluate_entry(snap, day.borrow)
                if guard.action == EntryAction.ABORT:
                    continue  # may become enterable later in the day
                caution = (
                    self.cfg.squeeze.caution_size_factor
                    if guard.action == EntryAction.REDUCE
                    else 1.0
                )
                located = min(day.borrow.shares_available, int(snap.adv_shares_20d))
                size = self.sizer.size(snap, located, caution_factor=caution,
                                       low_float=verdict.low_float_flag)
                if size.shares <= 0:
                    return "sized to zero"
                fill = self.slippage.fill_price(bar, size.shares, "short")
                entry = {
                    "time": bar.timestamp,
                    "shares": size.shares,
                    "price": fill,
                    "stop": fill * (1 + self.cfg.risk.stop_distance_pct / 100.0),
                    "target": fill * (1 - self.cfg.risk.target_reversion_pct / 100.0),
                }
                continue

            # --- position management ---
            exit_reason = None
            if bar.high >= entry["stop"]:
                exit_reason = "stop hit"
            elif bar.low <= entry["target"]:
                exit_reason = "target reversion"
            else:
                adverse = (bar.close / entry["price"] - 1.0) * 100.0
                if adverse >= self.cfg.risk.per_position_max_loss_pct:
                    exit_reason = "per-position max loss"
                else:
                    pos_snap = snap
                    from ..data.models import Position

                    pos = Position(
                        symbol=day.symbol, shares=entry["shares"],
                        entry_price=entry["price"], entry_time=entry["time"],
                        located_shares=entry["shares"], stop_price=entry["stop"],
                        target_price=entry["target"],
                    )
                    guard = self.guard.evaluate_position(pos, pos_snap, day.borrow)
                    if guard.action == PositionAction.FORCE_EXIT:
                        exit_reason = "squeeze guard: " + "; ".join(guard.reasons)
            if is_last_bar and exit_reason is None:
                exit_reason = "EOD flatten"
            if exit_reason is None:
                continue

            if exit_reason == "stop hit":
                exit_price = self.slippage.fill_price(
                    Bar(bar.symbol, bar.timestamp, bar.open, bar.high, bar.low,
                        entry["stop"], bar.volume),
                    entry["shares"], "cover",
                )
            elif exit_reason == "target reversion":
                exit_price = entry["target"]
            else:
                exit_price = self.slippage.fill_price(bar, entry["shares"], "cover")

            shares = entry["shares"]
            minutes_held = max(1.0, (bar.timestamp - entry["time"]).total_seconds() / 60.0)
            gross = (entry["price"] - exit_price) * shares
            return TradeRecord(
                symbol=day.symbol,
                entry_time=entry["time"],
                exit_time=bar.timestamp,
                shares=shares,
                entry_price=entry["price"],
                exit_price=exit_price,
                exit_reason=exit_reason,
                gross_pnl=gross,
                locate_fee=self.costs.locate_fee(shares),
                borrow_fee=self.costs.borrow_fee(
                    entry["price"] * shares, day.borrow.fee_rate_pct, minutes_held
                ),
                commissions=self.costs.commission(shares) * 2,  # in + out
            )

        return "no exit produced"  # unreachable: last bar always exits
