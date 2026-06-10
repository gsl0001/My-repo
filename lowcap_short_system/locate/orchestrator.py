"""TradeZero locate orchestration (design section 10).

Flow per candidate: quote -> cost gate -> accept/reserve. Reg SHO is enforced
here and in the order manager: no confirmed locate, no short order — and on
any API/auth failure we fail closed (drop the symbol, never trade).

Locate fees are usually non-refundable, so unused reservations are a real
sunk cost; the cost gate (step 3) exists to keep that bounded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from ..config import LocateConfig
from ..execution.broker import (
    Broker,
    BrokerError,
    LocateQuote,
    LocateReservation,
    LocateUnavailable,
)

logger = logging.getLogger(__name__)


class LocateOutcome(Enum):
    RESERVED = "reserved"
    NO_AVAILABILITY = "no_availability"
    TOO_EXPENSIVE = "too_expensive"
    FAILED = "failed"  # reject/timeout/API error after retries -> fail closed


@dataclass
class LocateResult:
    symbol: str
    outcome: LocateOutcome
    reservation: LocateReservation | None = None
    quote: LocateQuote | None = None
    detail: str = ""


@dataclass
class LocateLedger:
    """Tracks reservations and fees so EOD reconciliation (step 7) can report
    locate spend, including sunk cost on unused locates."""

    reservations: dict[str, LocateReservation] = field(default_factory=dict)
    fees_paid: float = 0.0
    shares_used: dict[str, int] = field(default_factory=dict)

    def record(self, res: LocateReservation) -> None:
        self.reservations[res.symbol] = res
        self.fees_paid += res.total_fee

    def use(self, symbol: str, shares: int) -> None:
        self.shares_used[symbol] = self.shares_used.get(symbol, 0) + shares

    def located_shares(self, symbol: str) -> int:
        res = self.reservations.get(symbol)
        return res.shares if res else 0

    def remaining_shares(self, symbol: str) -> int:
        return max(0, self.located_shares(symbol) - self.shares_used.get(symbol, 0))

    def unused_fee_sunk_cost(self) -> float:
        sunk = 0.0
        for symbol, res in self.reservations.items():
            if res.shares <= 0:
                continue
            unused = max(0, res.shares - self.shares_used.get(symbol, 0))
            sunk += res.total_fee * (unused / res.shares)
        return sunk


class LocateOrchestrator:
    def __init__(self, broker: Broker, cfg: LocateConfig):
        self.broker = broker
        self.cfg = cfg
        self.ledger = LocateLedger()

    def expected_edge(self, price: float, shares: int) -> float:
        """Expected fade move x size x win-prob (step 3)."""
        move = price * self.cfg.expected_fade_pct / 100.0
        return move * shares * self.cfg.expected_win_prob

    def secure_locate(self, symbol: str, price: float, shares_wanted: int) -> LocateResult:
        """Steps 2-4 for one candidate. Returns a reservation or the reason
        the symbol was dropped."""
        quote = self._quote_with_retries(symbol, shares_wanted)
        if isinstance(quote, LocateResult):
            return quote  # NO_AVAILABILITY or FAILED

        # step 3: locate cost gate
        shares_quotable = min(shares_wanted, quote.shares_available)
        locate_cost = quote.cost_per_share * shares_quotable
        edge = self.expected_edge(price, shares_quotable)
        max_cost = edge * self.cfg.max_locate_cost_fraction_of_edge
        if locate_cost > max_cost:
            return LocateResult(
                symbol,
                LocateOutcome.TOO_EXPENSIVE,
                quote=quote,
                detail=(
                    f"locate cost {locate_cost:.2f} > {max_cost:.2f} "
                    f"({self.cfg.max_locate_cost_fraction_of_edge:.0%} of edge {edge:.2f})"
                ),
            )

        # step 4: accept/reserve (fee usually incurred here; partials capped)
        try:
            reservation = self.broker.accept_locate(quote, shares_quotable)
        except BrokerError as exc:
            logger.warning("locate accept failed for %s: %s", symbol, exc)
            return LocateResult(symbol, LocateOutcome.FAILED, quote=quote, detail=str(exc))

        if reservation.shares < shares_quotable:
            logger.info(
                "partial locate %s: granted %d of %d — size will be capped",
                symbol, reservation.shares, shares_quotable,
            )
        self.ledger.record(reservation)
        return LocateResult(symbol, LocateOutcome.RESERVED, reservation=reservation, quote=quote)

    def _quote_with_retries(self, symbol: str, shares: int) -> LocateQuote | LocateResult:
        last_err: Exception | None = None
        for attempt in range(1 + self.cfg.locate_retry_budget):
            try:
                return self.broker.quote_locate(symbol, shares)
            except LocateUnavailable as exc:
                return LocateResult(symbol, LocateOutcome.NO_AVAILABILITY, detail=str(exc))
            except BrokerError as exc:
                last_err = exc
                logger.warning("locate quote attempt %d failed for %s: %s", attempt + 1, symbol, exc)
        # retry budget exhausted: drop the symbol cleanly, fail closed
        return LocateResult(symbol, LocateOutcome.FAILED, detail=str(last_err))

    def end_of_day_reconcile(self) -> dict:
        """Step 7: report locate spend; unused locate fees are sunk cost."""
        report = {
            "fees_paid": round(self.ledger.fees_paid, 2),
            "unused_fee_sunk_cost": round(self.ledger.unused_fee_sunk_cost(), 2),
            "symbols_located": sorted(self.ledger.reservations),
        }
        logger.info("locate EOD reconcile: %s", report)
        return report
