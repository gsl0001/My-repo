from __future__ import annotations
from collections import deque
from lowcap_short_system.microstructure.events import (
    BookState, DepthSnapshot, DepthDelta, PriceLevel, LevelChange,
)

class BookMaintainer:
    def __init__(self, symbol: str, depth: int = 10, history: int = 500) -> None:
        self.symbol = symbol
        self.depth = depth
        self._bids: dict[float, int] = {}
        self._asks: dict[float, int] = {}
        self._last_ts: float = 0.0
        self._changes: deque[LevelChange] = deque(maxlen=history)

    def apply_snapshot(self, snap: DepthSnapshot) -> None:
        self._bids = {p: s for p, s in snap.bids if s > 0}
        self._asks = {p: s for p, s in snap.asks if s > 0}
        self._last_ts = snap.ts

    def apply_delta(self, delta: DepthDelta) -> None:
        book = self._bids if delta.side == "bid" else self._asks
        old = book.get(delta.price, 0)
        if delta.new_size <= 0:
            book.pop(delta.price, None)
        else:
            book[delta.price] = delta.new_size
        self._last_ts = delta.ts
        self._changes.append(
            LevelChange(delta.ts, delta.side, delta.price, old, max(0, delta.new_size))
        )

    def state(self, ts: float | None = None) -> BookState:
        bids = tuple(
            PriceLevel(p, self._bids[p]) for p in sorted(self._bids, reverse=True)[: self.depth]
        )
        asks = tuple(
            PriceLevel(p, self._asks[p]) for p in sorted(self._asks)[: self.depth]
        )
        return BookState(self.symbol, ts if ts is not None else self._last_ts, bids, asks)

    @property
    def changes(self) -> list[LevelChange]:
        return list(self._changes)

    def is_stale(self, now: float, max_age_s: float) -> bool:
        return (now - self._last_ts) > max_age_s
