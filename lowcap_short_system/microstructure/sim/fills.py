from __future__ import annotations
from lowcap_short_system.microstructure.events import BookState

def fill_against_book(book: BookState, side: str, qty: int) -> tuple[int, float]:
    """Fill `qty` against displayed depth. side='sell' hits bids; 'buy' lifts asks.
    Returns (filled_qty, avg_price). Caps at displayed size (no infinite liquidity)."""
    levels = book.bids if side == "sell" else book.asks
    remaining, notional, filled = qty, 0.0, 0
    for lvl in levels:
        take = min(remaining, lvl.size)
        notional += take * lvl.price
        filled += take
        remaining -= take
        if remaining <= 0:
            break
    avg = notional / filled if filled else 0.0
    return filled, avg
