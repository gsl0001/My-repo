"""Account-level circuit breakers (Blueprint §12). When any trips, the system halts
ALL new orders. Pure check — the caller acts on the result (flatten / halt)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BreakerLimits:
    daily_drawdown_pct: float    # negative, e.g. -4.0
    max_positions: int
    max_gross_short: float
    consecutive_losses: int


@dataclass(frozen=True)
class AccountMetrics:
    drawdown_pct: float          # <= 0
    positions: int
    gross_short: float
    loss_streak: int


@dataclass(frozen=True)
class BreakerStatus:
    halted: bool
    reasons: tuple[str, ...]


def check_breakers(m: AccountMetrics, lim: BreakerLimits) -> BreakerStatus:
    reasons: list[str] = []
    if m.drawdown_pct <= lim.daily_drawdown_pct:
        reasons.append("daily drawdown limit")
    if m.positions >= lim.max_positions:
        reasons.append("max positions")
    if m.gross_short >= lim.max_gross_short:
        reasons.append("gross short cap")
    if m.loss_streak >= lim.consecutive_losses:
        reasons.append("consecutive losses")
    return BreakerStatus(bool(reasons), tuple(reasons))
