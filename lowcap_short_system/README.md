# lowcap_short_system

Project scaffold for the **automated intraday low-cap shorting system**.
Design lives in [`../docs/lowcap-short-system-design.md`](../docs/lowcap-short-system-design.md).

> Status: **scaffold only** — no implementation yet.

## Layout

| Folder | Maps to design section | Responsibility |
|---|---|---|
| `data/` | §4.1, §7, §11.2 | Ingestion: Polygon (market data), IBKR borrow files, SEC EDGAR catalysts, **borrow/locate recorder** |
| `signals/` | §4.2, §8 | Universe filter + pump-fade / dilution / borrow scoring |
| `risk/` | §4.3, §9 | Position sizing, squeeze guard, account circuit breakers, kill switch |
| `locate/` | §4.4, §10 | TradeZero locate orchestration (quote → cost gate → reserve → credit-back) |
| `execution/` | §4.5, §5 | TradeZero order routing, programmatic stops, SSR/halt handling, EOD flatten |
| `backtest/` | §11 | Realism requirements: survivorship-free universe, locate-cost bracketing, SSR/halt fills |
| `config/` | §8, §9 | Universe params + squeeze thresholds as tunable config (not hardcoded) |

## Build order

Follow the phased roadmap in design **§12** — gates are go/no-go, not advisory.
First thing to build is the **borrow/locate data recorder** (`data/`, design §11.2):
historical locate data cannot be bought later, so backtest data collection starts only
when the recorder is live.

## Stack
- **Broker / execution:** TradeZero (REST/WebSocket API)
- **Market data:** Polygon.io API
- **Borrow data:** IBKR short-availability files
- **Catalysts:** SEC EDGAR full-text API
