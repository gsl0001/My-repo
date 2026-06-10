"""Slippage model for thin names (design section 4.3: "fills move thin names").

Two components, both adverse to the trade:
- a fixed half-spread cost, wider for low-priced names
- square-root market impact scaling with participation (order size relative
  to the bar's volume), the standard shape for impact in illiquid stocks
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.models import Bar


@dataclass
class SlippageModel:
    half_spread_bps: float = 25.0  # low caps quote wide
    impact_coefficient_bps: float = 80.0  # impact at 100% participation

    def slippage_bps(self, shares: int, bar_volume: int) -> float:
        participation = shares / bar_volume if bar_volume > 0 else 1.0
        participation = min(1.0, participation)
        return self.half_spread_bps + self.impact_coefficient_bps * participation**0.5

    def fill_price(self, bar: Bar, shares: int, side: str) -> float:
        """Adverse-adjusted fill at the bar close. side: 'short' or 'cover'."""
        slip = self.slippage_bps(shares, bar.volume) / 10_000.0
        if side == "short":
            return bar.close * (1.0 - slip)  # sell lower
        return bar.close * (1.0 + slip)  # buy back higher
