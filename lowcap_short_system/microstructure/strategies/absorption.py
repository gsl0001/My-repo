from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class AbsorptionStrategy:
    name = "absorption"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        a = feats.absorption
        if not ctx.in_position and a.side == "sell" and a.strength > 0:
            return Signal("enter", "short", a.strength,
                          f"hidden seller absorption @ {a.price}")
        return None
