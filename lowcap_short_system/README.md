# lowcap_short_system

Project scaffold for the **automated intraday low-cap shorting system**.
Design lives in [`../docs/lowcap-short-system-design.md`](../docs/lowcap-short-system-design.md).

> Status: **scaffold only** — no implementation yet.

## Layout

| Folder | Maps to design section | Responsibility |
|---|---|---|
| `data/` | §4.1, §7 | Ingestion: Polygon (market data), IBKR borrow files, SEC EDGAR catalysts |
| `signals/` | §4.2, §8 | Universe filter + pump-fade / dilution / borrow scoring |
| `risk/` | §4.3, §9 | Position sizing, squeeze guard, account circuit breakers, kill switch |
| `locate/` | §4.4, §10 | TradeZero locate orchestration (quote → cost gate → reserve) |
| `execution/` | §4.5 | TradeZero order routing, programmatic stops, EOD flatten |
| `backtest/` | §6 | Slippage + borrow-cost modeling, strategy validation |
| `config/` | §8, §9 | Universe params + squeeze thresholds as tunable config (not hardcoded) |

## Stack
- **Broker / execution:** TradeZero (REST/WebSocket API)
- **Market data:** Polygon.io API
- **Borrow data:** IBKR short-availability files
- **Catalysts:** SEC EDGAR full-text API
