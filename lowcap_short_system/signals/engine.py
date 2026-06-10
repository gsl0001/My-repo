"""Signal & universe engine: turns raw data into ranked short candidates."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import UniverseConfig
from ..data.models import BorrowInfo, Filing, SymbolSnapshot
from . import scores
from .universe import UniverseFilter


@dataclass
class Candidate:
    snapshot: SymbolSnapshot
    borrow: BorrowInfo
    pump_score: float
    dilution_score: float
    borrow_score: float
    composite: float
    low_float_flag: bool
    triggered: bool  # passed the intraday "in play" gate
    filings: list[Filing] = field(default_factory=list)

    @property
    def symbol(self) -> str:
        return self.snapshot.symbol


class SignalEngine:
    def __init__(self, universe_cfg: UniverseConfig, min_composite: float = 0.10):
        self.universe = UniverseFilter(universe_cfg)
        self.cfg = universe_cfg
        self.min_composite = min_composite

    def build_candidates(
        self,
        snapshots: list[SymbolSnapshot],
        borrow_map: dict[str, BorrowInfo],
        filings_map: dict[str, list[Filing]] | None = None,
    ) -> list[Candidate]:
        """Filter to the tradable universe, score, and rank descending."""
        filings_map = filings_map or {}
        out: list[Candidate] = []
        for snap in snapshots:
            borrow = borrow_map.get(snap.symbol)
            verdict = self.universe.evaluate(snap, borrow)
            if not verdict.passed:
                continue
            assert borrow is not None  # universe filter requires borrowable
            filings = filings_map.get(snap.symbol, [])
            pump = scores.pump_fade_score(snap)
            dilution = scores.dilution_score(filings)
            brw = scores.borrow_score(borrow, self.cfg.soft_max_borrow_fee_pct)
            composite = scores.composite_score(pump, dilution, brw)
            if composite < self.min_composite:
                continue
            out.append(
                Candidate(
                    snapshot=snap,
                    borrow=borrow,
                    pump_score=pump,
                    dilution_score=dilution,
                    borrow_score=brw,
                    composite=composite,
                    low_float_flag=verdict.low_float_flag,
                    triggered=self.universe.trigger_gate(snap),
                    filings=filings,
                )
            )
        out.sort(key=lambda c: c.composite, reverse=True)
        return out
