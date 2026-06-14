from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, PriceLevel, TradePrint, LevelChange
from lowcap_short_system.microstructure.strategies.base import EvalContext
from lowcap_short_system.microstructure.strategies.engine import StrategyEngine, compute_features

CFG = MicroConfig()

def ask_heavy_book(ts=10.0):
    return BookState("X", ts, (PriceLevel(4.10, 100),), (PriceLevel(4.12, 2000), PriceLevel(4.13, 2000)))

def test_strong_absorption_alone_confirms_enter():
    prints = [TradePrint("X", 10.0 + i * 0.1, 4.12, 2000, "buy") for i in range(6)]  # 12k buy vol
    changes = [LevelChange(10.4, "ask", 4.12, 2000, 4000)]                            # refreshed
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.6), prints, changes, EvalContext(False))
    assert sig and sig.kind == "enter"

def test_weak_single_signal_does_not_confirm():
    # mild ask-heavy imbalance only (~ -0.4 strength) is below min_conviction 0.6
    eng = StrategyEngine(CFG)
    book = BookState("X", 10.0, (PriceLevel(4.10, 300),), (PriceLevel(4.12, 700),))
    sig = eng.evaluate(book, [], [], EvalContext(False))
    assert sig is None

def test_spoof_veto_blocks_entry():
    # ask-heavy + absorption would enter, but a spoofy book vetoes it
    prints = [TradePrint("X", 10.0 + i * 0.1, 4.12, 2000, "buy") for i in range(6)]
    changes = [
        LevelChange(10.4, "ask", 4.12, 2000, 4000),
        LevelChange(10.0, "bid", 4.00, 0, 9000),   # add wall
        LevelChange(10.3, "bid", 4.00, 9000, 0),   # cancel (no trade at 4.00) -> spoof
    ]
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.6), prints, changes, EvalContext(False))
    assert sig is None  # vetoed

def test_exit_dominates_when_in_position_on_upsweep():
    prints = [TradePrint("X", 10.0, 4.12, 100, "buy"),
              TradePrint("X", 10.1, 4.13, 100, "buy"),
              TradePrint("X", 10.2, 4.14, 100, "buy")]  # 3 distinct prices in <1s -> sweep
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.3), prints, [], EvalContext(True))
    assert sig and sig.kind == "exit"

def test_compute_features_bundles_all():
    f = compute_features(ask_heavy_book(), [], [], CFG)
    assert hasattr(f, "imbalance") and hasattr(f, "tape") and hasattr(f, "spoof")
