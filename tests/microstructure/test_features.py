from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, PriceLevel, TradePrint, LevelChange
from lowcap_short_system.microstructure.features import (
    order_book_imbalance, absorption, bid_stack_collapse, tape_metrics, spoofing_score,
)

CFG = MicroConfig()

def book(bids, asks, ts=10.0):
    return BookState("X", ts, tuple(PriceLevel(*b) for b in bids), tuple(PriceLevel(*a) for a in asks))

def test_imbalance_sign_and_range():
    bid_heavy = book([(4.1, 1000), (4.0, 1000)], [(4.2, 100), (4.3, 100)])
    ask_heavy = book([(4.1, 100), (4.0, 100)], [(4.2, 1000), (4.3, 1000)])
    assert order_book_imbalance(bid_heavy, CFG.imbalance_depth) > 0.5
    assert order_book_imbalance(ask_heavy, CFG.imbalance_depth) < -0.5
    assert -1.0 <= order_book_imbalance(ask_heavy, CFG.imbalance_depth) <= 1.0

def test_absorption_detects_refresh_against_buying():
    # buyers lift the 4.12 ask for 6000 sh while the ask level refreshes (400 -> 900)
    prints = [TradePrint("X", t, 4.12, 1000, "buy") for t in (10.0, 10.1, 10.2, 10.3, 10.4, 10.5)]
    changes = [LevelChange(10.25, "ask", 4.12, 400, 900)]  # refreshed bigger despite prints
    a = absorption(changes, prints, CFG)
    assert a.side == "sell" and a.strength > 0 and a.price == 4.12

def test_absorption_absent_without_refresh():
    prints = [TradePrint("X", 10.0, 4.12, 1000, "buy")]
    assert absorption([], prints, CFG).strength == 0.0

def test_bid_stack_collapse_scores_on_vanishing_bids():
    changes = [
        LevelChange(10.0, "bid", 4.10, 500, 0),     # removed
        LevelChange(10.1, "bid", 4.09, 400, 150),   # -62% > collapse_frac
    ]
    assert bid_stack_collapse(changes, CFG) >= 1.0  # >= collapse_min_levels collapsed

def test_tape_block_and_exhaustion():
    prints = (
        [TradePrint("X", 10.0 + i * 0.1, 4.1, 1000, "buy") for i in range(8)]  # busy first half
        + [TradePrint("X", 12.5, 4.1, 6000, "buy")]                            # a block, then quiet
    )
    t = tape_metrics(prints, cfg=CFG)
    assert t.block is True
    assert t.trades_per_s > 0

def test_spoofing_score_flags_add_then_cancel_without_trade():
    changes = [
        LevelChange(10.0, "bid", 4.00, 0, 5000),    # add a wall
        LevelChange(10.3, "bid", 4.00, 5000, 0),    # cancel it
    ]
    prints = []  # no trade at 4.00
    assert spoofing_score(changes, prints, CFG) > 0.0
