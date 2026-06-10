"""Top-level trading engine: wires data -> signals -> risk -> locates ->
execution into the daily cycle from design section 10.

    pre-market : universe + borrow file -> candidates -> locate quotes/reserves
    intraday   : on each snapshot tick — triggers, squeeze guard, entries,
                 position management, circuit breakers
    end of day : flatten (intraday mandate), reconcile locates

The engine is broker-agnostic; pass a PaperBroker for simulation or the
TradeZero adapter (once verified) for live.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import SystemConfig
from .data.models import BorrowInfo, Filing, SymbolSnapshot
from .execution.broker import Broker
from .execution.order_manager import OrderManager
from .locate.orchestrator import LocateOrchestrator, LocateOutcome
from .risk.circuit_breakers import AccountCircuitBreakers
from .risk.kill_switch import KillSwitch
from .risk.sizing import PositionSizer
from .risk.squeeze_guard import EntryAction, PositionAction, SqueezeGuard
from .signals.engine import Candidate, SignalEngine

logger = logging.getLogger(__name__)


@dataclass
class EngineState:
    candidates: dict[str, Candidate] = field(default_factory=dict)
    locate_outcomes: dict[str, str] = field(default_factory=dict)
    eod_done: bool = False


class TradingEngine:
    def __init__(
        self,
        cfg: SystemConfig,
        broker: Broker,
        account_equity: float,
    ):
        self.cfg = cfg
        self.broker = broker
        self.kill_switch = KillSwitch()
        self.signals = SignalEngine(cfg.universe)
        self.guard = SqueezeGuard(cfg.squeeze)
        self.sizer = PositionSizer(cfg.risk)
        self.locates = LocateOrchestrator(broker, cfg.locate)
        self.breakers = AccountCircuitBreakers(cfg.risk, account_equity)
        self.orders = OrderManager(
            broker, self.locates, self.breakers, self.kill_switch, cfg.risk
        )
        self.state = EngineState()

    # ---- pre-market (steps 1-4) ---------------------------------------------

    def premarket(
        self,
        snapshots: list[SymbolSnapshot],
        borrow_map: dict[str, BorrowInfo],
        filings_map: dict[str, list[Filing]] | None = None,
    ) -> list[Candidate]:
        """Build the candidate list and secure locates up front."""
        candidates = self.signals.build_candidates(snapshots, borrow_map, filings_map)
        for cand in candidates:
            snap = cand.snapshot
            located_target = self.sizer.size(
                snap,
                located_shares=cand.borrow.shares_available,
                low_float=cand.low_float_flag,
            )
            if located_target.shares <= 0:
                self.state.locate_outcomes[cand.symbol] = "sized to zero"
                continue
            result = self.locates.secure_locate(cand.symbol, snap.price, located_target.shares)
            self.state.locate_outcomes[cand.symbol] = result.outcome.value
            if result.outcome == LocateOutcome.RESERVED:
                self.state.candidates[cand.symbol] = cand
        logger.info(
            "premarket: %d candidates, %d located",
            len(candidates), len(self.state.candidates),
        )
        return list(self.state.candidates.values())

    # ---- intraday (steps 5-6) ------------------------------------------------

    def on_snapshot(self, snap: SymbolSnapshot, borrow: BorrowInfo | None = None) -> None:
        """Handle one market-data update for a candidate or open position."""
        if self.kill_switch.engaged:
            return

        symbol = snap.symbol
        position = self.orders.positions.get(symbol)

        if position is not None:
            # squeeze guard runs continuously while in a position
            verdict = self.guard.evaluate_position(position, snap, borrow)
            if verdict.action == PositionAction.FORCE_EXIT:
                self._mark_broker_price(symbol, snap.price)
                self.orders.cover(symbol, snap.price, "squeeze guard: " + "; ".join(verdict.reasons))
            else:
                self._mark_broker_price(symbol, snap.price)
                self.orders.manage(symbol, snap.price)
            self._check_account_breakers()
            return

        cand = self.state.candidates.get(symbol)
        if cand is None or self.state.eod_done:
            return
        if not self.signals.universe.trigger_gate(snap):
            return

        verdict = self.guard.evaluate_entry(snap, borrow or cand.borrow)
        if verdict.action == EntryAction.ABORT:
            logger.info("entry aborted %s: %s", symbol, "; ".join(verdict.reasons))
            return
        caution = (
            self.cfg.squeeze.caution_size_factor
            if verdict.action == EntryAction.REDUCE
            else 1.0
        )
        size = self.sizer.size(
            snap,
            located_shares=self.locates.ledger.remaining_shares(symbol),
            caution_factor=caution,
            low_float=cand.low_float_flag,
        )
        self._mark_broker_price(symbol, snap.price)
        result = self.orders.enter_short(symbol, snap.price, size.shares)
        if not result.accepted:
            logger.info("entry rejected %s: %s", symbol, result.reason)

    def on_borrow_recall(self, symbol: str, price: float) -> None:
        """Forced buy-in: exit gracefully (design section 5)."""
        self._mark_broker_price(symbol, price)
        self.orders.cover(symbol, price, "borrow recall")

    # ---- end of day (step 7) ---------------------------------------------------

    def end_of_day(self, marks: dict[str, float] | None = None) -> dict:
        """Flatten everything (intraday mandate) and reconcile locates."""
        for symbol, price in (marks or {}).items():
            self._mark_broker_price(symbol, price)
        self.orders.flatten_all("end of day")
        self.state.eod_done = True
        return self.locates.end_of_day_reconcile()

    # ---- controls ---------------------------------------------------------------

    def kill(self, reason: str) -> None:
        """Global kill switch: flatten everything, block all new orders."""
        self.kill_switch.engage(reason)
        self.orders.flatten_all(f"kill switch: {reason}")

    # ---- internals ----------------------------------------------------------------

    def _check_account_breakers(self) -> None:
        self.breakers.check_drawdown()  # realized pnl; marks add unrealized at entry checks
        if self.breakers.tripped and not self.kill_switch.engaged:
            self.kill(self.breakers.trip_reason or "account circuit breaker")

    def _mark_broker_price(self, symbol: str, price: float) -> None:
        # PaperBroker needs marks for fills; real brokers ignore this.
        set_price = getattr(self.broker, "set_price", None)
        if set_price is not None:
            set_price(symbol, price)
