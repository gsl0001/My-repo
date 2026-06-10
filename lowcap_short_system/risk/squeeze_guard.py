"""Squeeze guard (design section 9).

Protects against the asymmetric blow-up. Runs at entry (size down / abort) and
post-entry (reduce / force exit). The logic errs toward abort/reduce: skipping
a good trade is far cheaper than one uncapped-loss squeeze.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..config import SqueezeGuardConfig
from ..data.models import BorrowInfo, HaltState, Position, SymbolSnapshot


class EntryAction(Enum):
    OK = "ok"
    REDUCE = "reduce"  # caution: cut size by caution_size_factor
    ABORT = "abort"  # no entry


class PositionAction(Enum):
    HOLD = "hold"
    REDUCE = "reduce"
    FORCE_EXIT = "force_exit"


@dataclass
class GuardVerdict:
    action: EntryAction | PositionAction
    reasons: list[str] = field(default_factory=list)


class SqueezeGuard:
    def __init__(self, cfg: SqueezeGuardConfig):
        self.cfg = cfg

    def evaluate_entry(self, snap: SymbolSnapshot, borrow: BorrowInfo | None) -> GuardVerdict:
        cfg = self.cfg
        abort: list[str] = []
        caution: list[str] = []

        gain = snap.intraday_gain_pct
        if gain > cfg.abort_gain_pct and not snap.pulled_back:
            abort.append(f"+{gain:.0f}% and still accelerating")
        elif gain > cfg.caution_gain_pct:
            caution.append(f"+{gain:.0f}% intraday gain")

        if snap.rvol > cfg.abort_rvol:
            abort.append(f"RVOL {snap.rvol:.1f}x > {cfg.abort_rvol:.0f}x")
        elif snap.rvol > cfg.caution_rvol:
            caution.append(f"RVOL {snap.rvol:.1f}x")

        if borrow is not None:
            if borrow.fee_rate_pct > cfg.abort_borrow_fee_pct:
                abort.append(f"borrow fee {borrow.fee_rate_pct:.0f}%")
            elif borrow.fee_rate_pct > cfg.caution_borrow_fee_pct:
                caution.append(f"borrow fee {borrow.fee_rate_pct:.0f}%")

        if snap.float_shares is not None:
            if snap.float_shares < cfg.abort_float_shares:
                abort.append(f"float {snap.float_shares / 1e6:.1f}M shares")
            elif snap.float_shares < cfg.caution_float_shares:
                caution.append(f"low float {snap.float_shares / 1e6:.1f}M shares")

        if not snap.pulled_back and snap.consecutive_up_bars >= 5:
            abort.append("parabolic with no pullback")

        # LULD: halt-up before entry = skip (section 9)
        if snap.halt_state == HaltState.HALT_UP:
            abort.append("LULD halt-up before entry")

        if abort:
            return GuardVerdict(EntryAction.ABORT, abort + caution)
        if caution:
            return GuardVerdict(EntryAction.REDUCE, caution)
        return GuardVerdict(EntryAction.OK)

    def evaluate_position(
        self,
        position: Position,
        snap: SymbolSnapshot,
        borrow: BorrowInfo | None,
        borrow_recalled: bool = False,
        locate_lost: bool = False,
    ) -> GuardVerdict:
        cfg = self.cfg
        force: list[str] = []
        reduce: list[str] = []

        adverse = position.adverse_move_pct(snap.price)
        if adverse >= cfg.force_exit_adverse_pct:
            force.append(f"{adverse:.1f}% adverse move from entry")

        if borrow_recalled or locate_lost:
            force.append("borrow recall / locate lost")

        # RVOL spiking against us while underwater
        if snap.rvol > cfg.force_exit_rvol and adverse > 0:
            force.append(f"RVOL {snap.rvol:.1f}x against position")

        # new highs on accelerating volume
        if not snap.pulled_back and adverse > 0 and snap.consecutive_up_bars >= 3:
            force.append("new highs on accelerating volume")

        # halt-up against us = exit on resume
        if snap.halt_state == HaltState.HALT_UP and adverse > 0:
            force.append("LULD halt-up against position")

        if snap.halt_state == HaltState.HALT_UP:
            reduce.append("halt-up: pause adds")

        if force:
            return GuardVerdict(PositionAction.FORCE_EXIT, force)
        if reduce:
            return GuardVerdict(PositionAction.REDUCE, reduce)
        return GuardVerdict(PositionAction.HOLD)
