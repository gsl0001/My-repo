from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.features import Absorption, Tape
from lowcap_short_system.microstructure.strategies.base import Features, EvalContext
from lowcap_short_system.microstructure.strategies.imbalance import ImbalanceStrategy
from lowcap_short_system.microstructure.strategies.absorption import AbsorptionStrategy
from lowcap_short_system.microstructure.strategies.tape import TapeStrategy

CFG = MicroConfig()
BOOK = BookState("X", 1.0, (), ())
FLAT = EvalContext(in_position=False)
IN = EvalContext(in_position=True)

def feats(**kw):
    base = dict(imbalance=0.0, absorption=Absorption(0.0, "none", None),
                bid_collapse=0.0, tape=Tape(0.0, False, False, False), spoof=0.0)
    base.update(kw)
    return Features(**base)

def test_imbalance_enters_on_ask_heavy():
    s = ImbalanceStrategy()
    sig = s.evaluate(BOOK, feats(imbalance=-0.5), FLAT, CFG)
    assert sig and sig.kind == "enter" and sig.side == "short"
    assert s.evaluate(BOOK, feats(imbalance=-0.1), FLAT, CFG) is None  # below threshold

def test_absorption_enters_on_hidden_seller():
    s = AbsorptionStrategy()
    sig = s.evaluate(BOOK, feats(absorption=Absorption(0.9, "sell", 4.12)), FLAT, CFG)
    assert sig and sig.kind == "enter" and sig.strength == 0.9

def test_tape_enters_on_exhaustion_after_sweep_and_exits_on_upsweep():
    s = TapeStrategy()
    enter = s.evaluate(BOOK, feats(tape=Tape(5.0, True, False, True)), FLAT, CFG)
    assert enter and enter.kind == "enter"
    exit_sig = s.evaluate(BOOK, feats(tape=Tape(9.0, True, False, False)), IN, CFG)
    assert exit_sig and exit_sig.kind == "exit"
