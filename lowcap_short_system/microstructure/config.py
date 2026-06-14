from __future__ import annotations
from dataclasses import dataclass, fields
import os
import yaml

@dataclass(frozen=True)
class MicroConfig:
    # imbalance
    imbalance_depth: int = 5
    enter_imbalance: float = 0.35      # ask-heavy if imbalance <= -enter_imbalance
    # absorption
    absorb_window_s: float = 5.0
    absorb_min_volume: int = 5000
    # bid-stack collapse
    collapse_frac: float = 0.5
    collapse_min_levels: int = 2
    # tape
    tape_window_s: float = 5.0
    sweep_levels: int = 3
    block_size: int = 5000
    exhaustion_drop: float = 0.5
    # spoofing
    spoof_window_s: float = 5.0
    veto_spoof: float = 0.5            # spoof score >= this vetoes new entries
    # engine
    min_conviction: float = 0.6        # summed enter-strength * spoof-confidence

def load_config(path: str) -> MicroConfig:
    if not os.path.exists(path):
        return MicroConfig()
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    known = {f.name for f in fields(MicroConfig)}
    return MicroConfig(**{k: v for k, v in data.items() if k in known})
