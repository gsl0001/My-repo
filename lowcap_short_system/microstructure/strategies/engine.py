from __future__ import annotations
from dataclasses import dataclass
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, TradePrint, LevelChange
from lowcap_short_system.microstructure import features as F
from lowcap_short_system.microstructure.strategies.base import Features, EvalContext, Signal
from lowcap_short_system.microstructure.strategies.imbalance import ImbalanceStrategy
from lowcap_short_system.microstructure.strategies.absorption import AbsorptionStrategy
from lowcap_short_system.microstructure.strategies.tape import TapeStrategy

@dataclass(frozen=True)
class ConfirmedSignal:
    kind: str            # "enter" | "exit"
    side: str            # "short"
    strength: float
    reasons: tuple[str, ...]
    features: Features

def compute_features(book: BookState, prints: list[TradePrint],
                     changes: list[LevelChange], cfg: MicroConfig) -> Features:
    return Features(
        imbalance=F.order_book_imbalance(book, cfg.imbalance_depth),
        absorption=F.absorption(changes, prints, cfg),
        bid_collapse=F.bid_stack_collapse(changes, cfg),
        tape=F.tape_metrics(prints, cfg),
        spoof=F.spoofing_score(changes, prints, cfg),
    )

class StrategyEngine:
    def __init__(self, cfg: MicroConfig) -> None:
        self.cfg = cfg
        self.strategies = [ImbalanceStrategy(), AbsorptionStrategy(), TapeStrategy()]

    def evaluate(self, book: BookState, prints: list[TradePrint],
                 changes: list[LevelChange], ctx: EvalContext) -> ConfirmedSignal | None:
        feats = compute_features(book, prints, changes, self.cfg)
        subs: list[Signal] = []
        for s in self.strategies:
            sig = s.evaluate(book, feats, ctx, self.cfg)
            if sig is not None:
                subs.append(sig)

        exits = [s for s in subs if s.kind == "exit"]
        if ctx.in_position and exits:
            best = max(exits, key=lambda s: s.strength)
            return ConfirmedSignal("exit", "short", best.strength,
                                   tuple(s.reason for s in exits), feats)

        enters = [s for s in subs if s.kind == "enter"]
        confidence = 0.0 if feats.spoof >= self.cfg.veto_spoof else 1.0
        score = sum(s.strength for s in enters) * confidence
        if enters and score >= self.cfg.min_conviction:
            return ConfirmedSignal("enter", "short", min(1.0, score),
                                   tuple(s.reason for s in enters), feats)
        return None
