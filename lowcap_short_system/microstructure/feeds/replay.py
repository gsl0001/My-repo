from __future__ import annotations
import json
from typing import Iterator
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)

class ReplayFeed:
    """Replays a fixed list of events in timestamp order."""
    def __init__(self, events: list[MarketEvent]) -> None:
        self._events = sorted(events, key=lambda e: e.ts)

    def events(self) -> Iterator[MarketEvent]:
        return iter(self._events)

def _parse(obj: dict) -> MarketEvent:
    kind = obj["type"]
    if kind == "snapshot":
        return DepthSnapshot(obj["symbol"], obj["ts"],
                             tuple((p, s) for p, s in obj["bids"]),
                             tuple((p, s) for p, s in obj["asks"]))
    if kind == "delta":
        return DepthDelta(obj["symbol"], obj["ts"], obj["side"], obj["price"], obj["new_size"])
    if kind == "trade":
        return TradePrint(obj["symbol"], obj["ts"], obj["price"], obj["size"], obj["aggressor"])
    raise ValueError(f"unknown event type: {kind}")

def load_jsonl(path: str) -> list[MarketEvent]:
    with open(path, "r", encoding="utf-8") as fh:
        return [_parse(json.loads(line)) for line in fh if line.strip()]
