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
- [ ] Validate TradeZero locate request/confirm flow in paper/onboarding (flow drafted in §10).
- [ ] Confirm Polygon plan tier needed for full-universe real-time.
- [x] Define starting universe parameters — drafted in §8 (tune via backtest).
- [x] Define starting squeeze-guard thresholds — drafted in §9 (tune via backtest).
- [x] Draft TradeZero locate-orchestration flow — §10.
- [ ] Build backtester with realistic slippage + borrow-cost modeling.
- [ ] Decide intraday-only vs. allow overnight for dilution grinds.

> All numeric thresholds in §8–§9 are **starting hypotheses to be tuned against a
> backtest**, not validated parameters. They exist to make the system concrete and
> testable, not to be traded live as-is.

## 7. Data sources reference
| Source | Type | Cost | Notes |
|---|---|---|---|
| TradeZero API | Execution + locates | Account | REST/WebSocket |
| Polygon.io | Market data | Paid tiers | RT + tick history |
| IBKR short-availability files | Borrow data | Free | Daily, FTP |
| SEC EDGAR full-text API | Filings/catalysts | Free | Dilution detection |
| StockTwits API (optional) | Social/promo | Free tier | Pump detection |
| Ortex (optional) | Short interest/borrow | Paid | Days-to-cover, SI estimates |

---

## 8. Universe parameters (starting defaults)

> All values are tuning starting points. Each should be a config knob, not a hardcoded
> constant.

| Parameter | Starting value | Rationale |
|---|---|---|
| **Market cap band** | $10M – $500M | Micro/small-cap inefficiency; below $10M is too manipulable/illiquid |
| **Price floor** | $1.00 | Sub-$1 = delisting halts, no borrow, worst manipulation; avoid |
| **Price ceiling** | $25.00 | Keeps focus on low-priced names where pump dynamics dominate |
| **Min average dollar volume (20d)** | ≥ $3M/day | Liquidity gate so our own fills don't dominate the tape |
| **Min ADV (shares, 20d)** | ≥ 500k | Secondary liquidity check for share-count sizing |
| **Float** | Track; flag low float (< 20M sh) | Low float = squeeze-prone → smaller size, not auto-exclude |
| **Borrowable (IBKR file)** | shares available > 0 | Pre-filter; TradeZero confirms the real locate |
| **Max acceptable borrow fee** | ≤ 100% annualized (soft), hard cap 300% | Above this = crowded, squeeze-risky, and fees eat the edge |
| **Listing** | NASDAQ / NYSE / AMEX only | Exclude OTC/pinks (no clean borrow, no reliable data) |

**Intraday trigger gates (on top of the static universe):**
- Relative volume (RVOL vs 20d) ≥ 3× to qualify as "in play."
- Gap or intraday move present (the pump-fade needs a spike to fade).

## 9. Squeeze-guard thresholds (starting defaults)

The squeeze guard protects against the asymmetric blow-up. It runs both at **entry**
(size down / abort) and **post-entry** (reduce / exit).

| Signal | Caution (reduce size) | Abort / no-entry | Force-exit (in position) |
|---|---|---|---|
| Intraday % gain vs prior close | > 50% | > 100% and still accelerating | — |
| RVOL (vs 20d) | > 5× | > 10× | spikes to > 10× against us |
| Borrow fee (annualized) | > 100% | > 300% | recall / locate lost |
| Float | < 20M sh | < 5M sh | — |
| Adverse move from entry | — | — | ≥ 15–20% against position |
| Consecutive green/up-thrust | — | parabolic w/ no pullback | new highs on accelerating vol |
| LULD halt | halt-up = pause adds | halt-up before entry = skip | halt-up against us = exit on resume |

**Account-level circuit breakers (hard stops, halt all new orders):**
- Per-position max loss: 15–20% adverse (configurable).
- Daily account drawdown limit: e.g. −3% to −5% → flatten + stop for the day.
- Max concurrent positions / max gross short exposure caps.
- **Global kill switch:** one control that flattens everything and blocks new orders.

> Squeeze logic should err toward *abort/reduce*. In low caps, the cost of skipping a good
> trade is far lower than the cost of one uncapped-loss squeeze.

## 10. TradeZero locate-orchestration flow

This is the riskiest part to automate — locates are a hard Reg SHO gate and TradeZero
locate fees are a real, often non-refundable cost. Flow:

```
1. PRE-MARKET — build candidate list
   universe filter (§8) + IBKR borrow file ⇒ symbols worth checking

2. LOCATE QUOTE  (per candidate)
   query TradeZero locate availability:
     → shares available?
     → cost per share to locate?
   no availability ⇒ drop symbol

3. LOCATE COST GATE
   accept only if  locate_cost  <  X% of expected edge
     (e.g. expected fade move × size × win-prob)
   too expensive ⇒ drop symbol

4. LOCATE ACCEPT / RESERVE
   confirm locate via API ⇒ shares reserved (fee usually incurred here)
   record located_shares per symbol

5. SIGNAL TRIGGER ⇒ SHORT ORDER
   on intraday signal, send short order ≤ located_shares
   use marketable limit + attached programmatic stop

6. POSITION MANAGEMENT
   squeeze guard (§9) runs continuously
   exit on: target reversion % | time-stop (flat by close) |
            thesis invalidation | stop hit | borrow recall

7. END OF DAY
   ensure flat (intraday mandate)
   release/reconcile unused locates; log locate fees as cost
```

**Edge cases the order layer must handle:**
- **Partial locate** — fewer shares granted than requested → cap size accordingly.
- **Locate reject / timeout** — retry budget, then drop symbol cleanly.
- **Non-refundable locate fee** — model unused locates as sunk cost; tune step 3 so we
  don't over-reserve.
- **Borrow recall mid-trade** — detect and force-exit gracefully.
- **API/auth failure** — fail closed (no order without a confirmed locate). Never short
  without a confirmed locate (Reg SHO).
- **Rate limits** — batch/queue locate quotes within TradeZero API limits.

> ⚠️ **To verify against TradeZero API docs:** exact locate endpoint names, whether locate
> fees are refundable on unused holds, intraday (not just pre-market) locate support, and
> rate limits. Confirm all of this in a paper/onboarding account before any live wiring.
