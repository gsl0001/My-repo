from __future__ import annotations
from dataclasses import dataclass, field
from lowcap_short_system.microstructure.config import MicroConfig, load_config
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)
from lowcap_short_system.microstructure.book import BookMaintainer
from lowcap_short_system.microstructure.feeds.replay import ReplayFeed
from lowcap_short_system.microstructure.strategies.base import EvalContext
from lowcap_short_system.microstructure.strategies.engine import StrategyEngine, ConfirmedSignal

@dataclass
class ScenarioResult:
    signals: list[ConfirmedSignal] = field(default_factory=list)
    enters: int = 0
    exits: int = 0

def run_scenario(events: list[MarketEvent], cfg: MicroConfig | None = None,
                 start_in_position: bool = False) -> ScenarioResult:
    cfg = cfg or MicroConfig()
    symbol = events[0].symbol
    bm = BookMaintainer(symbol)
    eng = StrategyEngine(cfg)
    prints: list[TradePrint] = []
    in_position = start_in_position
    res = ScenarioResult()
    for ev in ReplayFeed(events).events():
        if isinstance(ev, DepthSnapshot):
            bm.apply_snapshot(ev)
            continue  # snapshots are initialization — no signal evaluation
        elif isinstance(ev, DepthDelta):
            bm.apply_delta(ev)
        elif isinstance(ev, TradePrint):
            prints.append(ev)
        sig = eng.evaluate(bm.state(ev.ts), prints, bm.changes, EvalContext(in_position))
        if sig is not None:
            res.signals.append(sig)
            if sig.kind == "enter":
                res.enters += 1
                in_position = True
            elif sig.kind == "exit":
                res.exits += 1
                in_position = False
    return res

def main() -> None:
    from lowcap_short_system.microstructure.sim import scenarios
    cfg = load_config("config/microstructure.yaml")
    runs = {
        "pump_fade_absorption": (scenarios.pump_fade_absorption(), False),
        "squeeze": (scenarios.squeeze(), True),
        "fake_wall": (scenarios.fake_wall(), False),
    }
    print("=== L2 engine sim ===")
    for name, (evs, in_pos) in runs.items():
        res = run_scenario(evs, cfg, start_in_position=in_pos)
        kinds = [s.kind for s in res.signals]
        print(f"{name:24s} enters={res.enters} exits={res.exits} signals={kinds}")

if __name__ == "__main__":
    main()
