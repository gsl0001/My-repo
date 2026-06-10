"""Trading-cost model: locate fees, borrow-fee accrual, commissions.

Locate fees are charged up front and treated as non-refundable (sunk even if
the trade never triggers). Borrow fees accrue on the time the short is held —
small intraday, but high-fee names make it non-trivial.
"""

from __future__ import annotations

from dataclasses import dataclass

TRADING_DAYS_PER_YEAR = 252
MINUTES_PER_SESSION = 390


@dataclass
class CostModel:
    locate_cost_per_share: float = 0.02
    commission_per_share: float = 0.005
    min_commission: float = 1.0

    def locate_fee(self, shares: int) -> float:
        return shares * self.locate_cost_per_share

    def commission(self, shares: int) -> float:
        return max(self.min_commission, shares * self.commission_per_share)

    def borrow_fee(
        self, notional: float, fee_rate_pct: float, minutes_held: float
    ) -> float:
        """Borrow fee accrued for an intraday hold, pro-rated from the
        annualized rate."""
        daily_rate = fee_rate_pct / 100.0 / TRADING_DAYS_PER_YEAR
        return notional * daily_rate * (minutes_held / MINUTES_PER_SESSION)
