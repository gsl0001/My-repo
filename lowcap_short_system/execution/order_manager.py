"""Order manager (design section 4.5).

The single gateway for orders. Every short entry must pass, in order:
kill switch -> account circuit breakers -> confirmed locate (Reg SHO).
Entries are marketable limits with an attached programmatic stop; exits cover
on target reversion, stop, squeeze-guard force-exit, borrow recall, or the
end-of-day flatten (intraday mandate).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import RiskConfig
from ..data.models import Position
from ..locate.orchestrator import LocateOrchestrator
from ..risk.circuit_breakers import AccountCircuitBreakers
from ..risk.kill_switch import KillSwitch
from .broker import Broker, Order, OrderSide, OrderStatus

logger = logging.getLogger(__name__)

# How far through the limit a marketable order is priced (entry sells a bit
# below the bid side to get filled in fast tape).
MARKETABLE_LIMIT_PCT = 0.5


@dataclass
class EntryResult:
    accepted: bool
    position: Position | None = None
    reason: str = ""


class OrderManager:
    def __init__(
        self,
        broker: Broker,
        locates: LocateOrchestrator,
        breakers: AccountCircuitBreakers,
        kill_switch: KillSwitch,
        risk_cfg: RiskConfig,
    ):
        self.broker = broker
        self.locates = locates
        self.breakers = breakers
        self.kill_switch = kill_switch
        self.risk_cfg = risk_cfg
        self.positions: dict[str, Position] = {}

    # ---- entries -----------------------------------------------------------

    def enter_short(self, symbol: str, price: float, shares: int) -> EntryResult:
        if self.kill_switch.engaged:
            return EntryResult(False, reason=f"kill switch: {self.kill_switch.reason}")
        if shares <= 0:
            return EntryResult(False, reason="zero size after caps")
        if symbol in self.positions:
            return EntryResult(False, reason="already in position")

        state = self.breakers.allows_new_entry(
            list(self.positions.values()),
            marks={s: p.entry_price for s, p in self.positions.items()},
            new_notional=price * shares,
        )
        if not state.allowed:
            return EntryResult(False, reason="; ".join(state.reasons))

        # Reg SHO: never short without a confirmed locate.
        remaining = self.locates.ledger.remaining_shares(symbol)
        if remaining <= 0:
            return EntryResult(False, reason="no confirmed locate (Reg SHO)")
        shares = min(shares, remaining)

        stop_price = price * (1 + self.risk_cfg.stop_distance_pct / 100.0)
        target_price = price * (1 - self.risk_cfg.target_reversion_pct / 100.0)
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL_SHORT,
            shares=shares,
            limit_price=round(price * (1 - MARKETABLE_LIMIT_PCT / 100.0), 4),
            stop_price=stop_price,
        )
        order = self.broker.submit_order(order)
        if order.status not in (OrderStatus.FILLED, OrderStatus.PARTIAL) or order.filled_shares <= 0:
            return EntryResult(False, reason=f"entry order {order.status.value}")

        self.locates.ledger.use(symbol, order.filled_shares)
        reservation = self.locates.ledger.reservations.get(symbol)
        res_shares = reservation.shares if reservation else 0
        fee_share = (
            reservation.total_fee * order.filled_shares / res_shares
            if reservation and res_shares > 0
            else 0.0
        )
        position = Position(
            symbol=symbol,
            shares=order.filled_shares,
            entry_price=order.avg_fill_price,
            entry_time=order.submitted_at or datetime.now(timezone.utc),
            located_shares=res_shares,
            stop_price=stop_price,
            target_price=target_price,
            locate_fee_paid=fee_share,
        )
        self.positions[symbol] = position
        logger.info(
            "SHORT %s %d @ %.4f (stop %.4f, target %.4f)",
            symbol, position.shares, position.entry_price, stop_price, target_price,
        )
        return EntryResult(True, position=position)

    # ---- exits -------------------------------------------------------------

    def cover(self, symbol: str, price: float, reason: str, shares: int | None = None) -> Position | None:
        """Cover all (or part) of a short. Returns the position when fully closed."""
        position = self.positions.get(symbol)
        if position is None:
            return None
        to_cover = min(shares or position.shares, position.shares)
        order = self.broker.submit_order(
            Order(symbol=symbol, side=OrderSide.BUY_TO_COVER, shares=to_cover, limit_price=None)
        )
        if order.status != OrderStatus.FILLED:
            logger.error("cover order for %s not filled (%s)", symbol, order.status.value)
            return None
        pnl = (position.entry_price - order.avg_fill_price) * order.filled_shares
        position.realized_pnl += pnl
        position.shares -= order.filled_shares
        self.breakers.record_realized(pnl)
        logger.info("COVER %s %d @ %.4f (%s) pnl %.2f", symbol, to_cover, order.avg_fill_price, reason, pnl)
        if position.shares <= 0:
            del self.positions[symbol]
            return position
        return None

    def manage(self, symbol: str, price: float) -> Position | None:
        """Stop / target checks on a mark. Squeeze-guard force exits are driven
        by the engine, which calls cover() directly with the verdict reason."""
        position = self.positions.get(symbol)
        if position is None:
            return None
        if price >= position.stop_price:
            return self.cover(symbol, price, "stop hit")
        if self.breakers.position_max_loss_breached(position, price):
            return self.cover(symbol, price, "per-position max loss")
        if price <= position.target_price:
            return self.cover(symbol, price, "target reversion")
        return None

    def flatten_all(self, reason: str) -> None:
        """EOD flatten / kill-switch path: cover everything, halt is caller's job."""
        logger.warning("FLATTEN ALL: %s", reason)
        for symbol in list(self.positions):
            mark = self.positions[symbol].entry_price
            self.cover(symbol, mark, f"flatten: {reason}")

    def gross_exposure(self, marks: dict[str, float]) -> float:
        return sum(p.notional(marks.get(s, p.entry_price)) for s, p in self.positions.items())
