import json
import pytest
from lowcap_short_system.microstructure.events import DepthSnapshot, TradePrint, DepthDelta
from lowcap_short_system.microstructure.feeds.replay import ReplayFeed, load_jsonl
from lowcap_short_system.microstructure.feeds.live_stubs import TradeZeroDepthFeed, IBKRDepthFeed

def test_replay_orders_events_by_ts():
    evs = [
        TradePrint("X", 3.0, 4.1, 100, "buy"),
        DepthSnapshot("X", 1.0, ((4.0, 100),), ((4.1, 100),)),
        DepthDelta("X", 2.0, "ask", 4.1, 50),
    ]
    out = list(ReplayFeed(evs).events())
    assert [e.ts for e in out] == [1.0, 2.0, 3.0]

def test_load_jsonl_roundtrip(tmp_path):
    p = tmp_path / "evs.jsonl"
    p.write_text(
        json.dumps({"type": "snapshot", "symbol": "X", "ts": 1.0, "bids": [[4.0, 100]], "asks": [[4.1, 100]]}) + "\n"
        + json.dumps({"type": "trade", "symbol": "X", "ts": 2.0, "price": 4.1, "size": 100, "aggressor": "buy"}) + "\n"
        + json.dumps({"type": "delta", "symbol": "X", "ts": 3.0, "side": "ask", "price": 4.1, "new_size": 0}) + "\n"
    )
    evs = load_jsonl(str(p))
    assert isinstance(evs[0], DepthSnapshot) and isinstance(evs[1], TradePrint) and isinstance(evs[2], DepthDelta)

def test_live_feeds_are_stubbed():
    with pytest.raises(NotImplementedError):
        TradeZeroDepthFeed("TICK").events()
    with pytest.raises(NotImplementedError):
        IBKRDepthFeed("TICK").events()
