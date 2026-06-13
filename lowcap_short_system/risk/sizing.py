"""Position sizing (Blueprint §8.1). Size = the MINIMUM of all caps, so a single
loose cap can never inflate risk. Pure and deterministic."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SizeInputs:
    account_equity: float
    risk_per_trade_pct: float   # % of equity risked to the stop (e.g. 0.5)
    entry_price: float
    stop_price: float           # for a short, stop is ABOVE entry
    adv_shares: int             # 20-day average daily volume (shares)
    max_adv_pct: float          # cap as % of ADV (e.g. 2.0)
    hard_dollar_cap: float      # max notional per name
    located_shares: int         # Reg SHO ceiling — cannot short more than located


def size_short(i: SizeInputs) -> int:
    """Shares to short = min(vol-based, %ADV, hard-$, located), floored to a 100 lot."""
    risk_dollars = i.account_equity * (i.risk_per_trade_pct / 100.0)
    per_share_risk = max(0.01, i.stop_price - i.entry_price)
    vol_qty = int(risk_dollars / per_share_risk)
    adv_qty = int(i.adv_shares * (i.max_adv_pct / 100.0))
    dollar_qty = int(i.hard_dollar_cap / i.entry_price) if i.entry_price > 0 else 0
    qty = min(vol_qty, adv_qty, dollar_qty, i.located_shares)
    qty = (qty // 100) * 100  # round down to a round lot
    return max(0, qty)
