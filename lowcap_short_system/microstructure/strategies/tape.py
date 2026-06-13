from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class TapeStrategy:
    name = "tape"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        t = feats.tape
        if ctx.in_position and t.sweep:
            return Signal("exit", "short", 0.8, "up-sweep against short")
        if not ctx.in_position and t.exhaustion and t.sweep:
            return Signal("enter", "short", 0.7, "buy exhaustion after sweep")
        return None
