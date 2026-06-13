from __future__ import annotations
from typing import Iterator
from lowcap_short_system.microstructure.events import MarketEvent

class _LiveFeedStub:
    """Phase 3: real broker depth. Stubbed behind the Feed protocol for now."""
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def events(self) -> Iterator[MarketEvent]:
        raise NotImplementedError(
            "Live broker depth is Phase 3 — requires credentials + a funded account."
        )

class TradeZeroDepthFeed(_LiveFeedStub):
    pass

class IBKRDepthFeed(_LiveFeedStub):
    pass
