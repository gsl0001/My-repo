"""Order management (Blueprint §8). Converts a short decision into a risk-bounded paper
position through the gates: halt check -> locate (Reg SHO, fail closed) -> sizing ->
place short + attached stop. The single chokepoint where every short must pass the rules."""
from __future__ import annotations
from dataclasses import dataclass

from lowcap_short_system.risk.sizing import SizeInputs, size_short
from lowcap_short_system.locate.provider import LocateProvider
from lowcap_short_system.execution.paper import PaperPosition
from lowcap_short_system.execution.router import OrderRouter


@dataclass(frozen=True)
class ShortDecision:
    symbol: str
    entry_price: float
    stop_price: float       # above entry for a short
    adv_shares: int


@dataclass(frozen=True)
class RiskParams:
    account_equity: float
    risk_per_trade_pct: float
    max_adv_pct: float
    hard_dollar_cap: float
    requested_shares: int   # desired size before caps (e.g. from target notional)


@dataclass(frozen=True)
class SubmitResult:
    ok: bool
    reason: str
    position: PaperPosition | None = None
    located: int = 0
    locate_cost: float = 0.0


def submit_short(
    decision: ShortDecision,
    risk: RiskParams,
    locate_provider: LocateProvider,
    broker: OrderRouter,
    *,
    halted: bool = False,
) -> SubmitResult:
    if halted:
        return SubmitResult(False, "trading halted")

    # Reg SHO: confirm a locate BEFORE sizing/transmitting. Fail closed.
    loc = locate_provider.locate(decision.symbol, risk.requested_shares)
    if not loc.ok or loc.located_shares <= 0:
        return SubmitResult(False, f"no confirmed locate ({loc.reason})", located=0)

    qty = size_short(SizeInputs(
        account_equity=risk.account_equity,
        risk_per_trade_pct=risk.risk_per_trade_pct,
        entry_price=decision.entry_price,
        stop_price=decision.stop_price,
        adv_shares=decision.adv_shares,
        max_adv_pct=risk.max_adv_pct,
        hard_dollar_cap=risk.hard_dollar_cap,
        located_shares=loc.located_shares,
    ))
    if qty <= 0:
        return SubmitResult(False, "size computed to zero", located=loc.located_shares)

    pos = broker.place_short(decision.symbol, qty, decision.entry_price, decision.stop_price)
    return SubmitResult(True, "filled", position=pos, located=loc.located_shares,
                        locate_cost=round(loc.cost_per_share * qty, 2))
