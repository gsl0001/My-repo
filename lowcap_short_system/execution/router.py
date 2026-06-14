"""Order-router interface. Both the offline PaperBroker and the live broker adapters
implement this, so the OMS routes through one seam regardless of mode."""
from __future__ import annotations
from typing import Protocol
from lowcap_short_system.execution.paper import PaperPosition


class OrderRouter(Protocol):
    def place_short(self, symbol: str, qty: int, limit_price: float, stop_price: float) -> PaperPosition: ...
