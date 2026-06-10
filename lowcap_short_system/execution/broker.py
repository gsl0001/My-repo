"""Broker abstraction.

Everything above this layer (locate orchestration, order manager, backtest)
talks to the `Broker` interface. Two implementations:

- `PaperBroker` — deterministic simulator for tests, paper trading and the
  backtester.
- `TradeZeroBroker` — adapter skeleton for the real TradeZero REST/WebSocket
  API. Endpoint names, locate-fee refund semantics, and rate limits MUST be
  verified against TradeZero docs in a paper/onboarding account before any
  live wiring (design doc section 10 warning). Until then it fails closed.
"""

from __future__ import annotations

import itertools
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class BrokerError(RuntimeError):
    pass


class LocateUnavailable(BrokerError):
    pass


@dataclass(frozen=True)
class LocateQuote:
    symbol: str
    shares_available: int
    cost_per_share: float
    quote_id: str = ""


@dataclass(frozen=True)
class LocateReservation:
    symbol: str
    shares: int
    total_fee: float  # usually non-refundable; modeled as sunk cost
    reservation_id: str = ""


class OrderSide(Enum):
    SELL_SHORT = "sell_short"
    BUY_TO_COVER = "buy_to_cover"


class OrderStatus(Enum):
    NEW = "new"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELED = "canceled"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    shares: int
    limit_price: float | None  # None = market (avoid in thin names)
    stop_price: float | None = None  # attached protective stop for shorts
    order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: OrderStatus = OrderStatus.NEW
    filled_shares: int = 0
    avg_fill_price: float = 0.0
    submitted_at: datetime | None = None


class Broker(ABC):
    # --- locates (Reg SHO gate) ---
    @abstractmethod
    def quote_locate(self, symbol: str, shares: int) -> LocateQuote:
        """Availability + cost per share. Raises LocateUnavailable when none."""

    @abstractmethod
    def accept_locate(self, quote: LocateQuote, shares: int) -> LocateReservation:
        """Reserve shares against a quote (fee usually incurred here).
        May grant fewer shares than requested (partial locate)."""

    # --- orders ---
    @abstractmethod
    def submit_order(self, order: Order) -> Order: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> None: ...

    @abstractmethod
    def flatten_all(self) -> list[Order]:
        """Cover every open short at market(able) price. Kill-switch path."""


class PaperBroker(Broker):
    """Deterministic simulator. Prices are set by the harness via set_price();
    fills are immediate at the limit (or current price for market orders)."""

    def __init__(
        self,
        locate_inventory: dict[str, int] | None = None,
        locate_cost_per_share: float = 0.01,
    ):
        self.prices: dict[str, float] = {}
        self.locate_inventory = dict(locate_inventory or {})
        self.locate_cost_per_share = locate_cost_per_share
        self.reservations: list[LocateReservation] = []
        self.orders: list[Order] = []
        self.open_shorts: dict[str, int] = {}
        self._quote_seq = itertools.count(1)

    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    def quote_locate(self, symbol: str, shares: int) -> LocateQuote:
        available = self.locate_inventory.get(symbol, 0)
        if available <= 0:
            raise LocateUnavailable(f"no locate inventory for {symbol}")
        return LocateQuote(
            symbol=symbol,
            shares_available=min(shares, available),
            cost_per_share=self.locate_cost_per_share,
            quote_id=f"q{next(self._quote_seq)}",
        )

    def accept_locate(self, quote: LocateQuote, shares: int) -> LocateReservation:
        available = self.locate_inventory.get(quote.symbol, 0)
        granted = min(shares, quote.shares_available, available)
        if granted <= 0:
            raise LocateUnavailable(f"locate inventory gone for {quote.symbol}")
        self.locate_inventory[quote.symbol] = available - granted
        res = LocateReservation(
            symbol=quote.symbol,
            shares=granted,
            total_fee=granted * quote.cost_per_share,
            reservation_id=uuid.uuid4().hex[:12],
        )
        self.reservations.append(res)
        return res

    def submit_order(self, order: Order) -> Order:
        order.submitted_at = datetime.now(timezone.utc)
        price = self.prices.get(order.symbol)
        if price is None:
            order.status = OrderStatus.REJECTED
        else:
            fill = order.limit_price if order.limit_price is not None else price
            # marketable limit: fills only if it crosses the current price
            crosses = (
                order.limit_price is None
                or (order.side == OrderSide.SELL_SHORT and order.limit_price <= price)
                or (order.side == OrderSide.BUY_TO_COVER and order.limit_price >= price)
            )
            if crosses:
                order.status = OrderStatus.FILLED
                order.filled_shares = order.shares
                order.avg_fill_price = min(fill, price) if order.side == OrderSide.BUY_TO_COVER else max(fill, price)
                delta = order.shares if order.side == OrderSide.SELL_SHORT else -order.shares
                self.open_shorts[order.symbol] = self.open_shorts.get(order.symbol, 0) + delta
            else:
                order.status = OrderStatus.CANCELED  # immediate-or-cancel semantics
        self.orders.append(order)
        return order

    def cancel_order(self, order_id: str) -> None:
        for o in self.orders:
            if o.order_id == order_id and o.status == OrderStatus.NEW:
                o.status = OrderStatus.CANCELED

    def flatten_all(self) -> list[Order]:
        covers = []
        for symbol, shares in list(self.open_shorts.items()):
            if shares <= 0:
                continue
            covers.append(
                self.submit_order(
                    Order(symbol=symbol, side=OrderSide.BUY_TO_COVER, shares=shares, limit_price=None)
                )
            )
        return covers


class TradeZeroBroker(Broker):
    """TradeZero API adapter skeleton.

    DO NOT WIRE LIVE until the following are verified against TradeZero API
    docs in a paper/onboarding account (design doc section 10):
      - exact locate quote/accept endpoint names and payloads
      - whether locate fees are refundable on unused holds
      - intraday (not just pre-market) locate support
      - rate limits (batch/queue locate quotes accordingly)

    Fails closed: every method raises until implemented, so no code path can
    accidentally trade without a confirmed, real locate.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    def _not_implemented(self) -> BrokerError:
        return BrokerError(
            "TradeZeroBroker is a skeleton — verify API endpoints in a paper "
            "account before wiring (see class docstring)"
        )

    def quote_locate(self, symbol: str, shares: int) -> LocateQuote:
        raise self._not_implemented()

    def accept_locate(self, quote: LocateQuote, shares: int) -> LocateReservation:
        raise self._not_implemented()

    def submit_order(self, order: Order) -> Order:
        raise self._not_implemented()

    def cancel_order(self, order_id: str) -> None:
        raise self._not_implemented()

    def flatten_all(self) -> list[Order]:
        raise self._not_implemented()
