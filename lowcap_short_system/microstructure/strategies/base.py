from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.features import Absorption, Tape

@dataclass(frozen=True)
class Signal:
    kind: str        # "enter" | "add" | "reduce" | "exit"
    side: str        # always "short"
    strength: float  # 0..1
    reason: str

@dataclass(frozen=True)
class EvalContext:
    in_position: bool

@dataclass(frozen=True)
class Features:
    imbalance: float
    absorption: Absorption
    bid_collapse: float
    tape: Tape
    spoof: float

class Strategy(Protocol):
    name: str
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None: ...
