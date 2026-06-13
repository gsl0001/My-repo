from __future__ import annotations
from dataclasses import dataclass

Side = str          # "bid" | "ask"
Aggressor = str     # "buy" | "sell" | "unknown"

@dataclass(frozen=True)
class PriceLevel:
    price: float
    size: int

@dataclass(frozen=True)
class BookState:
    symbol: str
    ts: float
    bids: tuple[PriceLevel, ...]   # sorted by price descending
    asks: tuple[PriceLevel, ...]   # sorted by price ascending

    @property
    def best_bid(self) -> PriceLevel | None:
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> PriceLevel | None:
        return self.asks[0] if self.asks else None

    @property
    def mid(self) -> float | None:
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None

    @property
    def spread(self) -> float | None:
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None

@dataclass(frozen=True)
class DepthSnapshot:
    symbol: str
    ts: float
    bids: tuple[tuple[float, int], ...]
    asks: tuple[tuple[float, int], ...]

@dataclass(frozen=True)
class DepthDelta:
    symbol: str
    ts: float
    side: Side
    price: float
    new_size: int          # 0 removes the level

@dataclass(frozen=True)
class TradePrint:
    symbol: str
    ts: float
    price: float
    size: int
    aggressor: Aggressor

@dataclass(frozen=True)
class LevelChange:
    ts: float
    side: Side
    price: float
    old_size: int
    new_size: int

MarketEvent = DepthSnapshot | DepthDelta | TradePrint
