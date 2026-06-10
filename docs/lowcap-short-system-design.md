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
| **Broker / execution** | **TradeZero Canada** (operator is CA-resident; International entity does not accept Canadians) | Order routing, short locates (REST/WebSocket API) |
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
- **Jurisdiction / entity (operator is a Canadian resident):** Canadian residents are
  **not eligible for TradeZero International** (Bahamas) — they onboard through
  **TradeZero Canada Securities ULC** (CIRO dealer-member, CIPF). All API/locate
  assumptions in this doc must be confirmed against the Canada entity specifically.
- **PDT rule: does not apply.** FINRA's $25k pattern-day-trader rule binds US
  (TradeZero America) accounts only. Still hold a healthy equity buffer (~$30k+) —
  short selling thin names with a small account dies to margin calls, not rules.
- **Canadian specifics to confirm:** CIRO day-trading margin treatment for short
  positions, USD account funding/conversion costs, and tax treatment of high-frequency
  trading gains (likely business income, not capital gains — plan for it).
- **Reg SHO:** locate required per short order — enforce in order layer, not as afterthought.
- **SSR (Rule 201):** when a stock drops ≥ 10% from prior close, short sales are restricted
  to prices **above the national best bid** for the rest of that day and the next. Pumps
  that crack often trigger SSR exactly when we want to add — the order layer must detect
  SSR state and switch to passive (above-bid) order types, and the backtest must model it
  or fills will be fantasy.
- **LULD halts:** low caps halt constantly on pumps. Track halt state; never assume a
  resting stop fills through a halt (it gaps).
- **Borrow recall:** handle forced buy-ins gracefully.
- **Kill switch:** global flatten + halt-new-orders control.

## 6. Open questions / next steps
- [x] Confirm TradeZero exposes locates programmatically — **confirmed**: official
  Developer API at [developer.tradezero.com](https://developer.tradezero.com) includes a
  dedicated [Locates API](https://developer.tradezero.com/docs/documentation/locates)
  (quote → accept → inventory → **sell-back credit for unused locates**), default rate
  limit 200 req/min, no extra API fee. Enable via Client Portal + API Trading Agreement.
- [ ] **Confirm Developer API is enabled for TradeZero Canada accounts.** Docs say
  "available to eligible TradeZero account holders" without an entity breakdown — ask
  TradeZero support directly before opening the account. **This is a hard blocker:** if
  the Canada entity can't enable the API, the broker choice must be revisited.
- [ ] Exercise the locate request/confirm/credit-back flow end-to-end in a test account
  (flow drafted in §10) and record actual latencies + fee behavior.
- [ ] Confirm Polygon plan tier needed for full-universe real-time.
- [x] Define starting universe parameters — drafted in §8 (tune via backtest).
- [x] Define starting squeeze-guard thresholds — drafted in §9 (tune via backtest).
- [x] Draft TradeZero locate-orchestration flow — §10.
- [ ] **Start the borrow/locate data recorder (§11.2) — the clock on backtest data only
  starts when this is running.** Highest-priority build item.
- [ ] Build backtester per realism requirements in §11.
- [ ] Decide intraday-only vs. allow overnight for dilution grinds.
- [ ] Execute the phased roadmap in §12 — no live capital before its gates pass.

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

> ✅ **Verified against TradeZero docs (2026):** the Developer API exposes the full locate
> lifecycle — request, status, accept quote, and **sell (credit) unused locates back** —
> with a default rate limit of **200 authenticated requests/min** and no extra API fee.
> Still to confirm in a test account: actual quote latency, intraday (not just pre-market)
> locate inventory depth, and the real economics of the credit-back (haircut vs. full
> refund). Confirm before any live wiring.

---

## 11. Backtest realism requirements

A naive backtest of this strategy will look spectacular and be unreproducible live. These
are the non-negotiables before any backtest number is trusted:

### 11.1 Survivorship bias
Most pump-and-dump names get delisted. Backtesting on today's universe silently drops the
best historical shorts *and* the worst squeezes. Use a point-in-time universe including
**delisted tickers** (Polygon retains delisted symbols — verify coverage depth for
micro-caps before relying on it).

### 11.2 Borrow/locate history does not exist retroactively ⚠️
Nobody sells historical TradeZero locate fees or intraday availability. This is the
binding constraint on the whole plan:

- **Build a recorder first.** Daily snapshot of IBKR short-availability files + periodic
  TradeZero locate quotes for the scanned universe, archived from day one. Every day the
  recorder isn't running is a day of backtest data lost forever.
- Until ~3–6 months of recorded data exist, locate costs in the backtest are *assumptions*.
  Bracket them: run every backtest at 1×, 2×, and 4× assumed locate cost and see where the
  edge dies.
- Ortex or similar can partially proxy historical borrow fees for sensitivity checks, not
  for ground truth on locate pricing.

### 11.3 Fill realism
- **No mid-or-better fills.** Assume crossing the spread + slippage scaled to
  (order size / interval volume). Thin tape: our own order moves the price.
- **Model SSR (Rule 201):** when triggered, short entries become above-bid passive orders —
  lower fill probability, worse timing. Ignoring SSR overstates pump-fade entries on the
  exact days that matter most.
- **Model LULD halts:** positions through a halt re-open at the gap price, not the stop
  price. Stops do not protect through halts.
- **Locate quantity caps size:** simulated position ≤ simulated located shares, not
  ≤ desired size.

### 11.4 Validation discipline
- Split data: tune §8/§9 thresholds in-sample, report out-of-sample only.
- Walk-forward, not one global fit; pump regimes shift (2021 ≠ 2024 ≠ 2026).
- Report **per-trade distribution**, not just aggregate PnL — the strategy lives or dies
  on the left tail (the one squeeze that eats a month).
- Minimum sample before trusting anything: a few hundred out-of-sample trades.

## 12. Phased roadmap with go/no-go gates

Each phase has an explicit gate. **Failing a gate means stop or go back — not "proceed
with caution."**

### Phase 0 — Infrastructure & data (≈ weeks 1–4)
First action (before building anything): **confirm with TradeZero support that a
TradeZero Canada account can enable the Developer API** (§6 blocker).
Build: borrow/locate recorder (§11.2), Polygon ingestion, EDGAR filing watcher,
TradeZero API auth + locate flow exercised in a paper-environment account.
> **Gate:** recorder running unattended ≥ 2 weeks with no data gaps; locate
> quote→accept→credit-back round-trip demonstrated via API.

### Phase 1 — Research & backtest (≈ months 2–4, overlaps Phase 0 recording)
Build: backtester meeting all §11 requirements; tune §8/§9 in-sample; out-of-sample +
locate-cost-bracketed results.
> **Gate:** out-of-sample edge survives 2× assumed locate costs and pessimistic fills;
> per-trade left tail acceptable under §9 circuit breakers; a few hundred OOS trades.
> *If the edge only exists at optimistic costs — stop here. That is a result.*

### Phase 2 — Shadow trading (≈ months 4–6)
Run the full live loop — signals, real locate quotes (quote, don't accept), simulated
fills against the live tape — with zero capital at risk. Log everything.
> **Gate:** ≥ 6 weeks shadow PnL within tolerance of backtest expectation for the same
> period (tracking error explained); zero compliance violations (every simulated short
> had a real available locate; SSR respected); kill switch tested.

### Phase 3 — Small live (≈ months 6–9)
Real money at **minimum viable size** (1 position at a time, smallest sensible size),
with a comfortable equity buffer (no PDT floor for a Canada account, but margin on
volatile shorts demands headroom). Purpose: measure real fills, real locate fees,
real recall behavior — not to make money.
> **Gate:** ≥ 100 live trades; realized slippage + locate costs within the bracket
> assumed in Phase 1; no risk-limit breaches; live edge statistically consistent with
> shadow/backtest.

### Phase 4 — Scale gradually
Increase size only while live tracking holds. Permanent practices: weekly live-vs-model
reconciliation, edge-decay monitoring (this edge is crowded and erodes), and an automatic
de-risk rule (e.g. halve size after any week breaching drawdown limits).

### Running cost reality check (order of magnitude, verify current pricing)
| Item | Est. monthly |
|---|---|
| Polygon (real-time full-universe tier) | ~$200 |
| TradeZero API | $0 (account required) |
| Locate fees (live phases — the dominant cost) | highly variable; often $10s–$100s/day when active |
| Infra (VPS/cloud, logging, alerting) | ~$20–100 |

Locate fees scale with activity and are the most likely silent edge-killer — which is why
the §10 cost gate and §11.2 bracketing exist.
