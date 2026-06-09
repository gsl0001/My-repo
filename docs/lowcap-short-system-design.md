# Automated Intraday Low-Cap Shorting System — Design

> Status: **Brainstorm / design** (no implementation yet)
> Scope: Fully automated, intraday holding horizon, US equities (low / micro-cap)

## 1. Strategy summary

Systematically short low-cap / micro-cap US equities on an **intraday** horizon, where
inefficiency, thin liquidity, and dilution/promotion dynamics create a recurring edge.
Primary theses:

- **Pump-and-dump fade** — short into promotional/parabolic spikes, exit on reversion.
- **Dilution pressure** — names with active ATM offerings, toxic convertibles, or rising
  share count grind lower under continuous supply.

The system is constrained more by **borrow availability** and **liquidity** than by thesis
quality. Risk is asymmetric (capped gains, uncapped losses), so squeeze protection and
position sizing are first-class concerns.

## 2. Selected stack

| Layer | Choice | Role |
|---|---|---|
| **Broker / execution** | **TradeZero** | Order routing, short locates (REST/WebSocket API) |
| **Market data** | **Polygon.io API** | Real-time + historical full-universe data, scanning, backtest |
| **Borrow / short-availability data** | **IBKR** (short-availability files) | Daily shortable-shares + fee-rate data to drive screener |
| **Catalyst data** | **SEC EDGAR full-text API** (free) | Dilution-filing detection (S-1, S-3, 424B5, 8-K) |

### Why this combination
- **TradeZero** exposes locates and execution through a programmatic API (REST/WebSocket),
  which is the hard requirement for automation — many low-cap-friendly brokers only do
  locates through a manual GUI.
- **Polygon** gives cost-effective full-universe real-time + tick history without the
  throttling of broker market-data feeds.
- **IBKR's** daily short-availability files (published on their FTP) are a free, broad
  source of shortable inventory and borrow fees — used as a *data* input to the screener
  even though execution happens at TradeZero.

> ⚠️ **Cross-broker caveat:** Inventory/fees from IBKR data are an *estimate* of borrow
> conditions. The authoritative locate for any trade is whatever **TradeZero** can actually
> source at execution time. IBKR data narrows the universe; TradeZero confirms the trade.

## 3. Architecture

```
[SEC EDGAR API]   [Polygon RT + history]   [IBKR borrow files]
       │                  │                       │
       └────────► [Signal & Universe Engine] ◄────┘
                          │
        score = pump-fade + dilution + borrow-availability
                          │
                  [Risk / Sizing layer]
            (% of ADV cap, vol sizing, squeeze guard)
                          │
                  [Locate orchestration]  ── TradeZero API
                          │
                  [Execution]  ── TradeZero API (programmatic stops)
                          │
                  [Monitoring / logging / kill switch]
```

## 4. Component design

### 4.1 Universe filter
- Market-cap band (define target range, e.g. micro-cap).
- Price floor (avoid sub-$1 unless explicitly targeted).
- Minimum average daily volume (ADV) — liquidity gate.
- **Must be borrowable** (cross-reference IBKR availability + TradeZero locate).

### 4.2 Signal engine
- **Pump-fade score:** parabolic move + mention/volume spike + weak fundamentals.
- **Dilution score:** EDGAR filing events + rising share count.
- **Borrow score:** availability and fee rate (higher fee = more crowded = squeeze risk).

### 4.3 Risk / sizing
- Position size capped as **% of 20-day ADV** (e.g. ≤ X%).
- Volatility-based sizing + hard per-name dollar cap.
- **Squeeze guard:** abort/reduce when volume + % gain + borrow fee cross thresholds.
- Explicit slippage modeling in backtest (fills move thin names).

### 4.4 Locate orchestration
- Pre-market: pull IBKR availability, build candidate list.
- Request/confirm locates via TradeZero API before sending shorts.
- No confirmed locate ⇒ no trade (Reg SHO compliance).

### 4.5 Execution
- Marketable limits + programmatic stops (survive squeezes).
- Time-stop (intraday — flat by close unless rules say otherwise).
- Exit on target reversion %, thesis invalidation, or borrow recall.

## 5. Compliance / operational constraints
- **PDT rule:** automated intraday trading requires ≥ $25k equity (US).
- **Reg SHO:** locate required per short order — enforce in order layer, not as afterthought.
- **Borrow recall:** handle forced buy-ins gracefully.
- **Kill switch:** global flatten + halt-new-orders control.

## 6. Open questions / next steps
- [ ] Validate TradeZero locate request/confirm flow in paper/onboarding.
- [ ] Confirm Polygon plan tier needed for full-universe real-time.
- [ ] Define exact universe parameters (cap band, price floor, min ADV).
- [ ] Define squeeze-guard thresholds.
- [ ] Build backtester with realistic slippage + borrow-cost modeling.
- [ ] Decide intraday-only vs. allow overnight for dilution grinds.

## 7. Data sources reference
| Source | Type | Cost | Notes |
|---|---|---|---|
| TradeZero API | Execution + locates | Account | REST/WebSocket |
| Polygon.io | Market data | Paid tiers | RT + tick history |
| IBKR short-availability files | Borrow data | Free | Daily, FTP |
| SEC EDGAR full-text API | Filings/catalysts | Free | Dilution detection |
| StockTwits API (optional) | Social/promo | Free tier | Pump detection |
| Ortex (optional) | Short interest/borrow | Paid | Days-to-cover, SI estimates |
