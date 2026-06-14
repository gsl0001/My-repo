"""Trading session orchestrator — ties the whole pipeline together for one symbol:
feed events → BookMaintainer → StrategyEngine → (on confirmed signal) OMS → broker,
with everything written to the audit trail.

This is the harness for **paper** live-testing: run it with a ReplayFeed/mock feed,
MockLocateProvider, and PaperBroker. For real live trading the operator swaps in the
live feed/locate/router behind the same seams AND arms live mode — the agent does not."""
from __future__ import annotations
from dataclasses import dataclass, field

from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)
from lowcap_short_system.microstructure.book import BookMaintainer
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.strategies.base import EvalContext
from lowcap_short_system.microstructure.strategies.engine import StrategyEngine
from lowcap_short_system.risk.breakers import BreakerLimits
from lowcap_short_system.locate.provider import LocateProvider
from lowcap_short_system.execution.paper import PaperBroker
from lowcap_short_system.execution.oms import ShortDecision, RiskParams, SubmitResult, submit_short
from lowcap_short_system.observability.audit import AuditLog
from lowcap_short_system.live.safety import require_armed

STOP_MULT = 1.08  # protective stop 8% above entry for a short


@dataclass
class TradingSession:
    symbol: str
    locate_provider: LocateProvider
    broker: PaperBroker
    audit: AuditLog
    risk: RiskParams
    breaker_limits: BreakerLimits
    adv_shares: int
    mode: str = "paper"          # "paper" | "live"
    micro_cfg: MicroConfig = field(default_factory=MicroConfig)

    def __post_init__(self) -> None:
        if self.mode == "live":
            require_armed()       # refuse to even build a live session unless the operator armed it
        self._book = BookMaintainer(self.symbol)
        self._engine = StrategyEngine(self.micro_cfg)
        self._prints: list[TradePrint] = []
        self.in_position = False
        self.results: list[SubmitResult] = []

    def _halted(self) -> bool:
        return len(self.broker.positions) >= self.breaker_limits.max_positions

    def on_event(self, ev: MarketEvent) -> None:
        if isinstance(ev, DepthSnapshot):
            self._book.apply_snapshot(ev)
            return  # snapshots are initialization, not actionable
        if isinstance(ev, DepthDelta):
            self._book.apply_delta(ev)
        elif isinstance(ev, TradePrint):
            self._prints.append(ev)

        sig = self._engine.evaluate(
            self._book.state(ev.ts), self._prints, self._book.changes, EvalContext(self.in_position)
        )
        if sig is None:
            return
        self.audit.record("SIGNAL", symbol=self.symbol, signal=sig.kind, strength=sig.strength)
        if sig.kind == "enter" and not self.in_position:
            self._enter(ev.ts)
        elif sig.kind == "exit" and self.in_position:
            self._exit(ev.ts)

    def _enter(self, ts: float) -> None:
        book = self._book.state(ts)
        entry = book.best_ask.price if book.best_ask else (book.mid or 0.0)
        if entry <= 0:
            return
        decision = ShortDecision(self.symbol, entry, round(entry * STOP_MULT, 2), self.adv_shares)
        res = submit_short(decision, self.risk, self.locate_provider, self.broker, halted=self._halted())
        self.audit.record(
            "ORDER" if res.ok else "REJECT", symbol=self.symbol, reason=res.reason,
            located=res.located, locate_cost=res.locate_cost,
        )
        if res.ok:
            self.in_position = True
        self.results.append(res)

    def _exit(self, ts: float) -> None:
        book = self._book.state(ts)
        price = book.best_ask.price if book.best_ask else (book.mid or 0.0)
        pnl = self.broker.cover(self.symbol, price)
        self.audit.record("EXIT", symbol=self.symbol, price=price, pnl=pnl)
        self.in_position = False

    def run(self, events: list[MarketEvent]) -> list[SubmitResult]:
        for ev in sorted(events, key=lambda e: e.ts):
            self.on_event(ev)
        return self.results
