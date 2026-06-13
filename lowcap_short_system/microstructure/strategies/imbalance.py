from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class ImbalanceStrategy:
    name = "imbalance"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        if not ctx.in_position and feats.imbalance <= -cfg.enter_imbalance:
            return Signal("enter", "short", min(1.0, abs(feats.imbalance)),
                          f"ask-heavy imbalance {feats.imbalance:.2f}")
        return None
