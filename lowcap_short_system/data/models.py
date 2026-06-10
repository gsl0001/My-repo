"""Core domain models shared across the system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar (any timeframe)."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class BorrowInfo:
    """Borrow availability for one symbol (IBKR short-availability file).

    This is an *estimate* of borrow conditions used to narrow the universe.
    The authoritative locate is whatever TradeZero sources at execution time
    (design doc section 2).
    """

    symbol: str
    shares_available: int
    fee_rate_pct: float  # annualized borrow fee, percent (e.g. 45.0 = 45%/yr)
    rebate_rate_pct: float | None = None
    as_of: datetime | None = None

    @property
    def borrowable(self) -> bool:
        return self.shares_available > 0


@dataclass(frozen=True)
class Filing:
    """An SEC EDGAR filing relevant to the dilution thesis."""

    symbol: str
    form_type: str  # e.g. "S-1", "S-3", "424B5", "8-K"
    filed_at: datetime
    accession_no: str = ""
    url: str = ""


class HaltState(Enum):
    NONE = "none"
    HALT_UP = "halt_up"  # LULD halt after an up move
    HALT_DOWN = "halt_down"


@dataclass
class SymbolSnapshot:
    """Point-in-time view of one symbol, feeding the universe filter,
    signal engine and squeeze guard (design sections 4.1, 4.2, 9)."""

    symbol: str
    price: float
    prev_close: float
    market_cap: float
    exchange: str  # primary listing, e.g. "NASDAQ", "NYSE", "AMEX"
    adv_shares_20d: float  # 20-day average daily volume, shares
    adv_dollar_20d: float  # 20-day average daily dollar volume
    float_shares: float | None = None
    day_volume: int = 0
    vwap: float | None = None
    halt_state: HaltState = HaltState.NONE
    timestamp: datetime | None = None
    # signal inputs
    consecutive_up_bars: int = 0
    pulled_back: bool = True  # False while move is parabolic with no pullback
    social_volume_zscore: float = 0.0  # optional (StockTwits etc.); 0 = unknown

    @property
    def intraday_gain_pct(self) -> float:
        """Percent move vs prior close. Positive = up."""
        if self.prev_close <= 0:
            return 0.0
        return (self.price / self.prev_close - 1.0) * 100.0

    @property
    def rvol(self) -> float:
        """Relative volume vs the 20-day average."""
        if self.adv_shares_20d <= 0:
            return 0.0
        return self.day_volume / self.adv_shares_20d


@dataclass
class Position:
    """An open short position."""

    symbol: str
    shares: int  # always positive; direction is short by construction
    entry_price: float
    entry_time: datetime
    located_shares: int
    stop_price: float
    target_price: float
    locate_fee_paid: float = 0.0
    realized_pnl: float = 0.0
    tags: dict = field(default_factory=dict)

    def adverse_move_pct(self, price: float) -> float:
        """Percent the price has moved *against* the short. Positive = losing."""
        if self.entry_price <= 0:
            return 0.0
        return (price / self.entry_price - 1.0) * 100.0

    def unrealized_pnl(self, price: float) -> float:
        return (self.entry_price - price) * self.shares

    def notional(self, price: float) -> float:
        return price * self.shares
