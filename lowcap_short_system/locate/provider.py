"""Short-locate orchestration (Blueprint §7). The system fails CLOSED: no confirmed
locate ⇒ no order. Mock provider for offline/paper; live provider stubbed for Phase 3."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LocateResult:
    symbol: str
    located_shares: int
    cost_per_share: float
    ok: bool
    reason: str = ""


class LocateProvider(Protocol):
    def locate(self, symbol: str, requested: int) -> LocateResult: ...


class MockLocateProvider:
    """Offline locate. `available` maps symbol -> shares; symbols absent are fully available."""
    def __init__(self, available: dict[str, int] | None = None, cost: float = 0.02) -> None:
        self._avail = available or {}
        self._cost = cost

    def locate(self, symbol: str, requested: int) -> LocateResult:
        avail = self._avail.get(symbol, requested)
        granted = min(requested, max(0, avail))
        if granted <= 0:
            return LocateResult(symbol, 0, 0.0, False, "no borrow")
        return LocateResult(symbol, granted, self._cost, True)


class TradeZeroLocateProvider:
    """Phase 3: real TradeZero locate (quote -> accept -> reserve). Needs credentials."""
    def locate(self, symbol: str, requested: int) -> LocateResult:
        raise NotImplementedError(
            "Live TradeZero locate is Phase 3 — requires API credentials + a live account."
        )
