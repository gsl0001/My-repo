# lowcap_short_system

Implementation of the **automated intraday low-cap shorting system**.
Design lives in [`../docs/lowcap-short-system-design.md`](../docs/lowcap-short-system-design.md).

> Status: **implemented, paper/backtest only.** The TradeZero adapter is a
> fail-closed skeleton until its API specifics (locate endpoints, fee refund
> semantics, rate limits) are verified in a paper/onboarding account — see
> design doc section 10. All thresholds are backtest-tuning hypotheses, not
> validated live parameters.

## Layout

| Folder | Design section | Responsibility |
|---|---|---|
| `data/` | §4.1, §7 | `market_data.py` (Polygon client behind a `MarketDataProvider` interface), `ibkr_borrow.py` (IBKR short-availability file parser), `edgar.py` (EDGAR dilution-filing search), `models.py` (domain models) |
| `signals/` | §4.2, §8 | `universe.py` (static filter + intraday trigger gate), `scores.py` (pump-fade / dilution / borrow scores), `engine.py` (ranked candidates) |
| `risk/` | §4.3, §9 | `sizing.py` (%ADV / vol / dollar caps), `squeeze_guard.py` (entry + in-position verdicts), `circuit_breakers.py` (account-level), `kill_switch.py` (global flatten + halt) |
| `locate/` | §4.4, §10 | `orchestrator.py` — quote → cost gate → reserve, partial/reject/timeout handling, fail-closed, EOD fee reconciliation |
| `execution/` | §4.5 | `broker.py` (`Broker` interface, `PaperBroker` simulator, `TradeZeroBroker` skeleton), `order_manager.py` (Reg SHO + kill-switch gated entries, stops/targets, flatten) |
| `backtest/` | §6 | `slippage.py` (spread + sqrt-impact), `costs.py` (locate/borrow/commission), `engine.py` (minute-bar replay through the live signal/risk logic) |
| `config/` | §8, §9 | `settings.py` dataclasses + `default.yaml` — every threshold is a knob |
| `engine.py` | §3, §10 | `TradingEngine`: pre-market candidates + locates → intraday triggers/management → EOD flatten + reconcile |

## Hard safety invariants

- **No locate, no short** (Reg SHO) — enforced in `OrderManager.enter_short`,
  and again by the fail-closed locate orchestrator and TradeZero skeleton.
- **Kill switch** latches, flattens everything, blocks all new orders; the
  daily-drawdown breaker engages it automatically.
- Squeeze guard errs toward abort/reduce: skipping a trade is cheap, an
  uncapped-loss squeeze is not.

## Quick start

```bash
pip install -e .[dev]
pytest
```

Run a simulated day end-to-end (see `tests/test_trading_engine.py` for the
full pattern):

```python
from lowcap_short_system.config import SystemConfig
from lowcap_short_system.engine import TradingEngine
from lowcap_short_system.execution.broker import PaperBroker

cfg = SystemConfig.from_yaml("lowcap_short_system/config/default.yaml")
broker = PaperBroker(locate_inventory={"PUMP": 10_000})
engine = TradingEngine(cfg, broker, account_equity=50_000)

candidates = engine.premarket(snapshots, borrow_map, filings_map)  # steps 1-4
engine.on_snapshot(snap, borrow)                                   # steps 5-6
report = engine.end_of_day(marks)                                  # step 7
```

Backtest minute bars through the same logic with
`backtest.BacktestEngine(cfg).run([SymbolDay(...)])`.

## Stack
- **Broker / execution:** TradeZero (REST/WebSocket API — adapter pending verification)
- **Market data:** Polygon.io API (`POLYGON_API_KEY`)
- **Borrow data:** IBKR short-availability files
- **Catalysts:** SEC EDGAR full-text API
