from __future__ import annotations
from typing import Iterator, Protocol
from lowcap_short_system.microstructure.events import MarketEvent

class Feed(Protocol):
    def events(self) -> Iterator[MarketEvent]: ...
