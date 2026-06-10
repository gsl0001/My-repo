"""Position sizing (design section 4.3).

Size = min(volatility budget, % of ADV cap, dollar cap, located shares),
optionally cut by the squeeze guard's caution factor and the low-float flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import RiskConfig
from ..data.models import SymbolSnapshot


@dataclass
class SizeResult:
    shares: int
    constraints: list[str] = field(default_factory=list)  # which caps bound the size


class PositionSizer:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg

    def size(
        self,
        snap: SymbolSnapshot,
        located_shares: int,
        caution_factor: float = 1.0,
        low_float: bool = False,
    ) -> SizeResult:
        cfg = self.cfg
        if snap.price <= 0:
            return SizeResult(0, ["invalid price"])

        constraints: list[str] = []

        # volatility / risk-budget sizing: risk dollars / stop distance
        stop_distance = snap.price * cfg.stop_distance_pct / 100.0
        risk_based = cfg.target_risk_dollars / stop_distance if stop_distance > 0 else 0.0

        adv_cap = snap.adv_shares_20d * cfg.max_pct_of_adv / 100.0
        dollar_cap = cfg.max_position_dollars / snap.price

        shares = min(risk_based, adv_cap, dollar_cap, float(located_shares))
        if shares == adv_cap:
            constraints.append("%ADV cap")
        if shares == dollar_cap:
            constraints.append("dollar cap")
        if shares == float(located_shares):
            constraints.append("located shares")
        if shares == risk_based and not constraints:
            constraints.append("risk budget")

        if low_float:
            shares *= 0.5  # low float = squeeze-prone -> smaller size (section 8)
            constraints.append("low-float haircut")
        if caution_factor < 1.0:
            shares *= caution_factor
            constraints.append("squeeze-guard caution")

        return SizeResult(max(0, int(shares)), constraints)
