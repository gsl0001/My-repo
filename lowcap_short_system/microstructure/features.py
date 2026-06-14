from __future__ import annotations
from dataclasses import dataclass
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, TradePrint, LevelChange

@dataclass(frozen=True)
class Absorption:
    strength: float          # 0..1
    side: str                # "sell" (hidden seller) | "none"
    price: float | None

@dataclass(frozen=True)
class Tape:
    trades_per_s: float
    sweep: bool
    block: bool
    exhaustion: bool

def order_book_imbalance(book: BookState, depth: int) -> float:
    """Depth-weighted (bid - ask)/(bid + ask). + = bid-heavy, - = ask-heavy. Range [-1, 1]."""
    def weighted(levels) -> float:
        return sum(lvl.size / (i + 1) for i, lvl in enumerate(levels[:depth]))
    bw, aw = weighted(book.bids), weighted(book.asks)
    return (bw - aw) / (bw + aw) if (bw + aw) > 0 else 0.0

def absorption(changes: list[LevelChange], prints: list[TradePrint], cfg: MicroConfig) -> Absorption:
    """Hidden seller: heavy buy volume at an ask price while that ask level refreshes (holds/grows)."""
    if not prints:
        return Absorption(0.0, "none", None)
    latest = prints[-1].ts
    window = [p for p in prints if latest - p.ts <= cfg.absorb_window_s]
    buy_vol: dict[float, int] = {}
    for p in window:
        if p.aggressor == "buy":
            buy_vol[p.price] = buy_vol.get(p.price, 0) + p.size
    best_price, best_strength = None, 0.0
    for price, vol in buy_vol.items():
        if vol < cfg.absorb_min_volume:
            continue
        refreshed = any(
            c.side == "ask" and c.price == price and c.new_size >= c.old_size
            and latest - c.ts <= cfg.absorb_window_s
            for c in changes
        )
        if refreshed:
            strength = min(1.0, vol / (2 * cfg.absorb_min_volume))
            if strength > best_strength:
                best_price, best_strength = price, strength
    return Absorption(best_strength, "sell" if best_strength > 0 else "none", best_price)

def bid_stack_collapse(changes: list[LevelChange], cfg: MicroConfig) -> float:
    """Fraction (capped at 1) of bid levels that vanished or shrank past collapse_frac, vs min_levels."""
    collapsed: set[float] = set()
    for c in changes:
        if c.side != "bid" or c.old_size <= 0:
            continue
        if c.new_size == 0 or c.new_size <= c.old_size * (1 - cfg.collapse_frac):
            collapsed.add(c.price)
    return min(1.0, len(collapsed) / cfg.collapse_min_levels)

def tape_metrics(prints: list[TradePrint], cfg: MicroConfig) -> Tape:
    if not prints:
        return Tape(0.0, False, False, False)
    latest = prints[-1].ts
    window = [p for p in prints if latest - p.ts <= cfg.tape_window_s]
    span = max(cfg.tape_window_s, 1e-9)
    rate = len(window) / span
    block = any(p.size >= cfg.block_size for p in window)
    recent_buy_prices = {p.price for p in window if p.aggressor == "buy" and latest - p.ts <= 1.0}
    sweep = len(recent_buy_prices) >= cfg.sweep_levels
    half = latest - cfg.tape_window_s / 2
    first = [p for p in window if p.ts < half]
    second = [p for p in window if p.ts >= half]
    first_rate = len(first) / (cfg.tape_window_s / 2)
    second_rate = len(second) / (cfg.tape_window_s / 2)
    exhaustion = bool(first and second_rate <= cfg.exhaustion_drop * first_rate)
    return Tape(rate, sweep, block, exhaustion)

def spoofing_score(changes: list[LevelChange], prints: list[TradePrint], cfg: MicroConfig) -> float:
    """Ratio of 'add then cancel without a trade at that price' to total adds, in the window. 0..1."""
    if not changes:
        return 0.0
    latest = changes[-1].ts
    window = [c for c in changes if latest - c.ts <= cfg.spoof_window_s]
    traded_prices = {p.price for p in prints if latest - p.ts <= cfg.spoof_window_s}
    adds = [c for c in window if c.old_size == 0 and c.new_size > 0]
    cancels = {c.price for c in window if c.old_size > 0 and c.new_size == 0}
    if not adds:
        return 0.0
    spoofy = sum(
        1 for c in adds if c.price in cancels and c.price not in traded_prices
    )
    return min(1.0, spoofy / len(adds))
