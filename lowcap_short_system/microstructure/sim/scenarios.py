from __future__ import annotations
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)

def pump_fade_absorption() -> list[MarketEvent]:
    """Parabolic top: heavy buying lifts the 4.12 ask but it refreshes (hidden seller),
    plus ask-heavy depth. Engine should confirm a fade enter."""
    evs: list[MarketEvent] = [
        DepthSnapshot("TICK", 0.0, ((4.10, 100), (4.09, 100)), ((4.12, 3000), (4.13, 3000))),
    ]
    t = 0.1
    for _ in range(6):
        evs.append(TradePrint("TICK", t, 4.12, 2000, "buy"))
        t += 0.1
    evs.append(DepthDelta("TICK", t, "ask", 4.12, 5000))  # refresh bigger despite the buying
    return evs

def squeeze() -> list[MarketEvent]:
    """Up-sweep against an open short: buys across rising prices in under a second."""
    return [
        DepthSnapshot("TICK", 0.0, ((4.10, 200),), ((4.12, 200), (4.13, 200), (4.14, 200))),
        TradePrint("TICK", 0.1, 4.12, 200, "buy"),
        TradePrint("TICK", 0.2, 4.13, 200, "buy"),
        TradePrint("TICK", 0.3, 4.14, 200, "buy"),
    ]

def fake_wall() -> list[MarketEvent]:
    """Same fade setup as pump_fade, but a spoofed bid wall flickers in and out -> veto."""
    evs = pump_fade_absorption()
    evs.append(DepthDelta("TICK", 0.05, "bid", 4.00, 9000))   # add wall (no trade at 4.00)
    evs.append(DepthDelta("TICK", 0.55, "bid", 4.00, 0))      # cancel it
    return evs
