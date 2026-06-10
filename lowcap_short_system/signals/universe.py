"""Static universe filter (design sections 4.1 and 8).

Returns the reasons a symbol fails, so rejections are auditable in logs and
backtest output rather than silent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import UniverseConfig
from ..data.models import BorrowInfo, SymbolSnapshot


@dataclass
class UniverseVerdict:
    passed: bool
    low_float_flag: bool = False  # flag = size down later, not exclusion
    reasons: list[str] = field(default_factory=list)


class UniverseFilter:
    def __init__(self, cfg: UniverseConfig):
        self.cfg = cfg

    def evaluate(self, snap: SymbolSnapshot, borrow: BorrowInfo | None) -> UniverseVerdict:
        cfg = self.cfg
        reasons: list[str] = []

        if snap.exchange not in cfg.allowed_exchanges:
            reasons.append(f"exchange {snap.exchange or '?'} not in {cfg.allowed_exchanges}")
        if not (cfg.min_market_cap <= snap.market_cap <= cfg.max_market_cap):
            reasons.append(f"market cap {snap.market_cap:,.0f} outside band")
        if snap.price < cfg.price_floor:
            reasons.append(f"price {snap.price:.2f} below floor {cfg.price_floor:.2f}")
        if snap.price > cfg.price_ceiling:
            reasons.append(f"price {snap.price:.2f} above ceiling {cfg.price_ceiling:.2f}")
        if snap.adv_dollar_20d < cfg.min_adv_dollar_20d:
            reasons.append(f"dollar ADV {snap.adv_dollar_20d:,.0f} below minimum")
        if snap.adv_shares_20d < cfg.min_adv_shares_20d:
            reasons.append(f"share ADV {snap.adv_shares_20d:,.0f} below minimum")

        # Must be borrowable per the IBKR pre-filter; TradeZero confirms later.
        if borrow is None or not borrow.borrowable:
            reasons.append("no borrow availability in IBKR file")
        elif borrow.fee_rate_pct > cfg.hard_max_borrow_fee_pct:
            reasons.append(
                f"borrow fee {borrow.fee_rate_pct:.0f}% above hard cap "
                f"{cfg.hard_max_borrow_fee_pct:.0f}%"
            )

        low_float = (
            snap.float_shares is not None and snap.float_shares < cfg.low_float_flag_shares
        )
        return UniverseVerdict(passed=not reasons, low_float_flag=low_float, reasons=reasons)

    def trigger_gate(self, snap: SymbolSnapshot) -> bool:
        """Intraday 'in play' gate on top of the static universe (section 8):
        relative volume spike plus a move worth fading."""
        return (
            snap.rvol >= self.cfg.min_trigger_rvol
            and abs(snap.intraday_gain_pct) >= self.cfg.min_trigger_move_pct
        )
