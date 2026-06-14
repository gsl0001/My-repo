"""Paper broker — simulates fills and tracks short positions offline. The OMS routes
here for the 'paper' promotion stage; the live router (Phase 3) implements the same shape."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PaperPosition:
    symbol: str
    qty: int            # short quantity (positive)
    avg_price: float
    stop_price: float


@dataclass
class PaperBroker:
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    realized: float = 0.0

    def place_short(self, symbol: str, qty: int, limit_price: float, stop_price: float) -> PaperPosition:
        existing = self.positions.get(symbol)
        if existing:
            total = existing.qty + qty
            existing.avg_price = round((existing.avg_price * existing.qty + limit_price * qty) / total, 4)
            existing.qty = total
            existing.stop_price = stop_price
            return existing
        pos = PaperPosition(symbol, qty, limit_price, stop_price)
        self.positions[symbol] = pos
        return pos

    def cover(self, symbol: str, price: float) -> float:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return 0.0
        pnl = (pos.avg_price - price) * pos.qty  # short profits when price falls
        self.realized += pnl
        return pnl

    def gross_short(self, marks: dict[str, float]) -> float:
        return sum(p.qty * marks.get(s, p.avg_price) for s, p in self.positions.items())
