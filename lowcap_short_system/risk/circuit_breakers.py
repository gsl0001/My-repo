"""Account-level circuit breakers (design section 9): hard stops that halt
all new orders independently of per-trade logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import RiskConfig
from ..data.models import Position


@dataclass
class BreakerState:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


class AccountCircuitBreakers:
    def __init__(self, cfg: RiskConfig, starting_equity: float):
        self.cfg = cfg
        self.starting_equity = starting_equity
        self.realized_pnl_today = 0.0
        self.tripped = False
        self.trip_reason: str | None = None

    def record_realized(self, pnl: float) -> None:
        self.realized_pnl_today += pnl

    def daily_drawdown_pct(self, unrealized_pnl: float = 0.0) -> float:
        """Drawdown as a positive percentage of starting equity."""
        if self.starting_equity <= 0:
            return 0.0
        total = self.realized_pnl_today + unrealized_pnl
        return max(0.0, -total / self.starting_equity * 100.0)

    def check_drawdown(self, unrealized_pnl: float = 0.0) -> bool:
        """Returns True (and trips) when the daily loss limit is breached.
        A tripped breaker stays tripped for the rest of the day."""
        dd = self.daily_drawdown_pct(unrealized_pnl)
        if dd >= self.cfg.daily_drawdown_limit_pct:
            self.tripped = True
            self.trip_reason = f"daily drawdown {dd:.1f}% >= {self.cfg.daily_drawdown_limit_pct}%"
        return self.tripped

    def allows_new_entry(
        self,
        open_positions: list[Position],
        marks: dict[str, float],
        new_notional: float = 0.0,
    ) -> BreakerState:
        reasons: list[str] = []
        if self.tripped:
            reasons.append(self.trip_reason or "breaker tripped")

        if len(open_positions) >= self.cfg.max_concurrent_positions:
            reasons.append(f"max concurrent positions ({self.cfg.max_concurrent_positions})")

        gross = sum(p.notional(marks.get(p.symbol, p.entry_price)) for p in open_positions)
        if gross + new_notional > self.cfg.max_gross_short_exposure:
            reasons.append(
                f"gross short exposure {gross + new_notional:,.0f} > "
                f"{self.cfg.max_gross_short_exposure:,.0f}"
            )

        unrealized = sum(
            p.unrealized_pnl(marks.get(p.symbol, p.entry_price)) for p in open_positions
        )
        if self.check_drawdown(unrealized):
            reasons.append(self.trip_reason or "daily drawdown limit")

        return BreakerState(allowed=not reasons, reasons=list(dict.fromkeys(reasons)))

    def position_max_loss_breached(self, position: Position, price: float) -> bool:
        return position.adverse_move_pct(price) >= self.cfg.per_position_max_loss_pct

    def reset_for_new_day(self, starting_equity: float) -> None:
        self.starting_equity = starting_equity
        self.realized_pnl_today = 0.0
        self.tripped = False
        self.trip_reason = None
