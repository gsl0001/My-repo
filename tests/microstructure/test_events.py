from lowcap_short_system.microstructure.events import (
    PriceLevel, BookState, DepthSnapshot, DepthDelta, TradePrint, LevelChange,
)

def test_bookstate_derived_quotes():
    b = BookState(
        symbol="TICK", ts=1.0,
        bids=(PriceLevel(4.10, 500), PriceLevel(4.09, 300)),
        asks=(PriceLevel(4.12, 400), PriceLevel(4.13, 200)),
    )
    assert b.best_bid.price == 4.10
    assert b.best_ask.price == 4.12
    assert round(b.mid, 3) == 4.11
    assert round(b.spread, 3) == 0.02

def test_empty_book_quotes_are_none():
    b = BookState(symbol="X", ts=0.0, bids=(), asks=())
    assert b.best_bid is None and b.best_ask is None
    assert b.mid is None and b.spread is None

def test_event_types_are_frozen():
    d = DepthDelta(symbol="X", ts=1.0, side="bid", price=4.0, new_size=0)
    t = TradePrint(symbol="X", ts=1.0, price=4.0, size=100, aggressor="buy")
    s = DepthSnapshot(symbol="X", ts=1.0, bids=((4.0, 100),), asks=((4.1, 100),))
    c = LevelChange(ts=1.0, side="ask", price=4.1, old_size=100, new_size=200)
    assert d.new_size == 0 and t.aggressor == "buy" and s.bids[0][1] == 100 and c.new_size == 200
