# LowCap Short — Automated Intraday Low-Cap Shorting System

An automated system for **shorting low/micro-cap US equities intraday**, driven by **Level 2
(depth-of-book) market microstructure**. It pairs a **Python trading engine** with a
**React operator cockpit**, built borrow-first and risk-first.

> ⚠️ **Safety / status.** Everything in this repo is **simulation / dry-run**. No code here
> connects to a live broker or places real orders. The cockpit runs on mock data; the Python
> engine runs on replay/synthetic data; the live broker adapters are **dry-run by default and
> hard-gated** so they cannot trade by accident. Going live is an explicit, operator-driven
> step (see [§9](#9-live-trading--safety-model)). This is **not financial advice**; shorting
> low-caps has **capped gains and uncapped losses**.

---

## Table of contents
1. [What it is & the edge](#1-what-it-is--the-edge)
2. [Quick start](#2-quick-start)
3. [Repository layout](#3-repository-layout)
4. [Architecture & data flow](#4-architecture--data-flow)
5. [The trading logic (exact)](#5-the-trading-logic-exact)
6. [The operator cockpit (UI)](#6-the-operator-cockpit-ui)
7. [Configuration — every knob](#7-configuration--every-knob)
8. [Compliance & risk](#8-compliance--risk)
9. [Live trading & safety model](#9-live-trading--safety-model)
10. [Testing & CI](#10-testing--ci)
11. [Roadmap / phase status](#11-roadmap--phase-status)

---

## 1. What it is & the edge

Two recurring, structurally-driven inefficiencies in US micro/small-caps:

- **Pump-and-dump fade** — promotional/parabolic spikes in low-float names overshoot and
  mean-revert intraday. We short *climactic strength that fails*, never a falling knife.
- **Dilution grind** — names with active ATM offerings / toxic convertibles face continuous
  mechanical supply and trend down.

The binding constraints are **borrow availability and liquidity**, not thesis quality — so the
system is built borrow-first (locate before order, always) and risk-first (every entry ships
with a stop; circuit breakers halt the book).

The full operating doctrine lives in
[`lowcap_short_system/MASTER_BLUEPRINT.md`](lowcap_short_system/MASTER_BLUEPRINT.md) (the
9-stage pipeline). This README documents the **implemented** logic.

## 2. Quick start

**Operator cockpit (UI)** — from the repo root, PowerShell:
```powershell
.\start.ps1            # checks Node, installs deps on first run, starts the dev server
.\start.ps1 -Open      # also open the browser;  -Port 3000 ;  -Install to reinstall
```
Plain npm: `cd ui; npm install; npm run dev`.

**Python L2 engine demo** (prints the microstructure sim — fade enter / squeeze exit / spoof veto):
```powershell
python -m pip install pytest ruff mypy pyyaml      # first time only
python -m lowcap_short_system.microstructure.sim.harness
```

**Tests:** `python -m pytest tests -q` (engine) and `cd ui; npm run test` (UI).

## 3. Repository layout

```
start.ps1                      # one-command launcher for the cockpit
.env.example                   # secret names only (copy to .env, gitignored)
.github/workflows/ci.yml       # CI: pytest+ruff+mypy (engine) and vitest+build (UI)

lowcap_short_system/           # Python trading engine
  MASTER_BLUEPRINT.md          # operating doctrine (9-stage pipeline)
  PROMOTION.md                 # backtest -> paper -> tiny-live -> scale gates
  microstructure/              # Level 2 engine
    events.py                  # OrderBook / DepthSnapshot / DepthDelta / TradePrint
    book.py                    # BookMaintainer (apply deltas, history, staleness)
    features.py                # imbalance, absorption, bid-collapse, tape, spoofing
    strategies/                # imbalance, absorption, tape + engine (composition)
    feeds/                     # ReplayFeed + live feed stubs
    sim/                       # harness, fill model, synthetic scenarios
    config.py                  # MicroConfig (+ config/microstructure.yaml loader)
  risk/      sizing.py, breakers.py
  locate/    provider.py       # LocateProvider (Reg SHO) + Mock + TradeZero stub
  execution/ paper.py, oms.py, router.py
  observability/ audit.py      # append-only JSONL audit log
  security/  secrets.py        # env-only secrets, fail-loud
  live/      safety.py, transport.py, tradezero.py   # dry-run, hard-gated adapters
config/microstructure.yaml     # all L2 thresholds (never hardcoded)

ui/                            # React + Vite + TS operator cockpit (mock-data driven)
  src/mockData/                # store, tick engine, l2 mirror, generators
  src/tabs/cockpit|config|backtest, src/components/
docs/                          # design specs & implementation plans
```

## 4. Architecture & data flow

Two processes, decoupled by clean interfaces. The **engine** decides; the **cockpit**
visualizes. Today both run on mock/replay data; live adapters slot in behind the same seams.

```
            ┌──────────── PYTHON ENGINE (lowcap_short_system) ────────────┐
 depth +    │  Feed → BookMaintainer → features → StrategyEngine            │
 tape  ─────▶  (ReplayFeed now;        (imbalance, absorption,  (spoof veto │
 (mock/      │   broker feed later)     tape, collapse, spoof)   + conviction)│
  replay)    │                                   │ ConfirmedSignal           │
            │                                   ▼                           │
            │   sizing (risk/) → locate gate (Reg SHO, fail closed) →       │
            │   circuit breakers (risk/) → OMS → OrderRouter                │
            │                       (PaperBroker now | TradeZero dry-run)   │
            │   every step → append-only audit log (observability/)        │
            └──────────────────────────────────────────────────────────────┘

            ┌──────────── REACT COCKPIT (ui/) ─ mock-data mirror ──────────┐
 useTickEngine (~1s) → store (positions, orders, scanner, L2 book/tape,    │
 account) → Cockpit panels (positions, active orders, scanner, L2 ladder,  │
 right rail, live log) + Config + Backtest. Kill switch / pause / cover /   │
 short-from-scanner act on mock state.                                     │
            └──────────────────────────────────────────────────────────────┘
```

**A symbol becomes an order only after passing every gate in sequence** — universe → in-play
→ research/thesis → L2 confirmation → confirmed locate → sizing/SSR → risk caps. Any failure
resolves toward *don't / smaller / abort*.

## 5. The trading logic (exact)

This section documents the implemented algorithms with their exact rules and default
thresholds. **All numbers are starting hypotheses to be tuned against a backtest** and live in
config, never hardcoded.

### 5.1 Level 2 features  ([`microstructure/features.py`](lowcap_short_system/microstructure/features.py))

Pure functions over the current `BookState` and recent `TradePrint`s / book changes.

- **Order-book imbalance** — depth-weighted, near-touch levels weighted higher:
  ```
  weighted(side) = Σ  size_i / (i + 1)      for i in top `imbalance_depth` (=5) levels
  imbalance      = (weighted(bids) − weighted(asks)) / (weighted(bids) + weighted(asks))
  ```
  Range `[-1, 1]`. **Negative = ask-heavy = offer pressure** (bearish, supportive of a short).
- **Absorption / hidden seller** — within `absorb_window_s` (5s), sum buy-aggressor volume at
  each ask price. A price qualifies if `buy_vol ≥ absorb_min_volume` (5000) **and** the ask
  level at that price *refreshed* (a change where `new_size ≥ old_size` despite the buying).
  `strength = min(1, buy_vol / (2 × absorb_min_volume))`, `side = "sell"`. This is the classic
  fade trigger at the high.
- **Bid-stack collapse** — count bid levels that vanished (`new_size = 0`) or shrank past
  `collapse_frac` (50%). `score = min(1, collapsed / collapse_min_levels)` (2).
- **Tape** — over `tape_window_s` (5s): `trades_per_s`; `sweep` = ≥ `sweep_levels` (3) distinct
  buy prices in the last 1s; `block` = any print ≥ `block_size` (5000); `exhaustion` = the
  second half of the window is ≤ `exhaustion_drop` (0.5) × the first half's rate (sped up, then
  died).
- **Spoofing score** — fraction of level *adds* (`0 → size`) that were later *cancelled*
  (`size → 0`) at the same price with **no trade** there in `spoof_window_s` (5s). Higher =
  faker book. Used to discount fake walls.

### 5.2 Strategies  ([`microstructure/strategies/`](lowcap_short_system/microstructure/strategies))

Each is stateless: `evaluate(book, features, ctx, cfg) → Signal | None`. We only ever short.

| Strategy | Enters (`enter`) | Exits (`exit`, while in position) |
|---|---|---|
| **Imbalance** | `imbalance ≤ −enter_imbalance` (−0.35); strength = `min(1, |imbalance|)` | — |
| **Absorption** | hidden-seller absorption present; strength = absorption strength | — |
| **Tape** | `exhaustion AND sweep` (climactic top); strength 0.7 | `sweep` against the short (up-sweep) |

### 5.3 Strategy engine  ([`strategies/engine.py`](lowcap_short_system/microstructure/strategies/engine.py))

Composes the sub-signals into one `ConfirmedSignal`:

1. **Exits dominate.** If in a position and any strategy says `exit` → emit `exit`.
2. **Spoof veto.** `confidence = 0 if spoofing_score ≥ veto_spoof (0.5) else 1`. A spoofy book
   zeroes conviction — no entry.
3. **Conviction.** `score = Σ(enter strengths) × confidence`. Emit `enter` only if there is at
   least one enter signal **and** `score ≥ min_conviction` (0.6).

Consequences of the defaults: a **strong absorption alone** (strength ~0.8) clears 0.6 and
fires. A **lone mild imbalance** (~0.4) does **not** — it needs a second confirmation (e.g.
imbalance + tape). A **spoofy** book is vetoed regardless.

### 5.4 Exits & force-exit

- **Python engine** ([`strategies/engine.py`](lowcap_short_system/microstructure/strategies/engine.py)):
  while in a position, an up-sweep on the tape produces an `exit` (exits dominate over entries).
- **UI tick engine** ([`ui/src/mockData/tick.ts`](ui/src/mockData/tick.ts)): on every step an open
  position is force-covered — booking realized P&L and logging `GUARD` + `EXIT` — when
  **`last ≥ stop_price`** (stop hit) **or** the squeeze guard flags `exit`.

### 5.5 Position sizing  ([`risk/sizing.py`](lowcap_short_system/risk/sizing.py))

Size = the **minimum** of all caps, floored to a 100-share lot — a loose cap can never inflate
risk:
```
risk_$        = account_equity × (risk_per_trade_pct / 100)
per_share_risk = max(0.01, stop_price − entry_price)        # short: stop is above entry
vol_qty       = risk_$ / per_share_risk                      # volatility sizing
adv_qty       = adv_shares × (max_adv_pct / 100)             # % of 20d ADV (don't move tape)
dollar_qty    = hard_dollar_cap / entry_price                # hard per-name notional cap
qty           = floor_to_100( min(vol_qty, adv_qty, dollar_qty, located_shares) )
```
`located_shares` is the Reg SHO ceiling — **you can never short more than is located.**

### 5.6 Locate gate (Reg SHO)  ([`locate/provider.py`](lowcap_short_system/locate/provider.py))

Borrow-first. `LocateProvider.locate(symbol, requested) → LocateResult{located_shares, cost,
ok}`. `MockLocateProvider` simulates availability offline; `TradeZeroLocate` (dry-run) walks the
ETB → quote → accept flow. **The system fails closed: no `ok` locate ⇒ no order, ever.**

### 5.7 Circuit breakers  ([`risk/breakers.py`](lowcap_short_system/risk/breakers.py))

`check_breakers(metrics, limits) → BreakerStatus`. Halts **all new orders** when any trips:
daily drawdown ≤ limit (e.g. −4%), positions ≥ max (6), gross short ≥ cap ($150k), or loss
streak ≥ limit. Plus the **kill switch** (flatten everything + halt). All failure paths resolve
toward *flat and halted*.

### 5.8 Order management (the chokepoint)  ([`execution/oms.py`](lowcap_short_system/execution/oms.py))

`submit_short(decision, risk, locate_provider, broker, halted)` runs the gates in order:

```
1. halted?                          → reject "trading halted"
2. locate(requested)                → if not ok / 0 shares → reject "no confirmed locate"  (Reg SHO)
3. size_short(... located_shares)   → if 0 → reject "size computed to zero"
4. broker.place_short(symbol, qty, entry, stop)   → marketable limit + attached stop
   → SubmitResult{ ok, position, located, locate_cost }
```
`broker` is any `OrderRouter` — `PaperBroker` (offline fills, P&L, gross) today, the dry-run
`TradeZeroOrderRouter` when wired. Every signal/locate/order is written to the append-only
**audit log** ([`observability/audit.py`](lowcap_short_system/observability/audit.py)) stamped
with the live config version.

### 5.9 Squeeze guard (§9 thresholds)

Runs continuously on open positions and pre-entry candidates; errs toward reduce/abort.
Implemented in the UI ([`ui/src/mockData/guard.ts`](ui/src/mockData/guard.ts)); mirrors the
blueprint table:

| Signal | Caution (reduce) | Abort / force-exit |
|---|---|---|
| Intraday % gain vs prior close | > 50% | > 100% |
| RVOL (vs 20d) | > 5× | > 10× |
| Borrow fee (annualized) | > 100% | > 300% |
| Float | < 20M sh | < 5M sh |
| Adverse move from entry | — | ≥ 15% against |

## 6. The operator cockpit (UI)

React + Vite + TypeScript; runs entirely on a **mock-data tick engine** (~1s) so it looks and
behaves live without any backend ([`ui/src/mockData/`](ui/src/mockData)).

**Cockpit tab** — Open Positions (click a row → confirm → cover) · Active Orders (working /
partial / resting stop / pending locate; click to cancel) · **Live Scanner** (in-play
candidates with pump/dilution/borrow scores + locate gate; click a borrowable `✓` row → confirm
→ places a short) · **L2 panel** (live depth ladder + features + signal badge for the top
in-play name — a TypeScript mirror of the Python engine, [`ui/src/mockData/l2.ts`](ui/src/mockData/l2.ts))
· right rail (Day P&L, circuit breakers, squeeze alerts, reserved locates) · full-width
color-coded **live log**. Top bar: session clock, **Pause/Resume** (freezes the sim), and a
confirm-gated **KILL SWITCH** (flatten + halt).

**Config tab** — the §8 universe params and §9 squeeze / circuit-breaker thresholds as live
forms; edits re-evaluate guards immediately and **auto-save to the browser**.

**Backtest tab** — equity curve, stat grid, trades table (sample result set).

The UI's auto-trading loop: the tick engine force-exits guard-EXIT / stop-hit positions, auto-
enters strong borrowable candidates (respecting caps), spawns/ages in-play names, and emits real
log events — so the cockpit is self-sustaining and coherent.

## 7. Configuration — every knob

| Where | Holds |
|---|---|
| [`config/microstructure.yaml`](config/microstructure.yaml) | L2 engine thresholds (§5.1–§5.3): imbalance depth/threshold, absorption window/volume, collapse, tape (window/sweep/block/exhaustion), spoof window/veto, conviction. Loaded by `MicroConfig` / `load_config`. |
| `risk` params (passed into `size_short` / `check_breakers`) | risk-per-trade %, %ADV cap, hard $ cap, drawdown/position/gross/loss-streak limits. |
| UI `Config` tab → `config-defaults.ts` / `guard.ts` | universe band, squeeze thresholds, circuit breakers (browser-persisted). |
| `.env` (from [`.env.example`](.env.example)) | live credentials — **blank until you wire live yourself**. |

Each live trading day should snapshot the exact config version used (for journal attribution).

## 8. Compliance & risk

| Rule | Enforcement |
|---|---|
| **Reg SHO (locate)** | OMS asserts a confirmed locate before any short; **fails closed** (§5.6, §5.8). |
| **Reg SHO Rule 201 (SSR)** | A short under SSR must price above the NBB — flagged in the order payload; enforce pre-send when live (`live/tradezero.py`). |
| **PDT** | ≥ $25k equity for automated intraday trading — a pre-market gate (operational). |
| **Borrow recall / buy-in** | Handled by the force-exit path (§5.4). |
| **Kill switch** | Always available — flatten everything + block new orders. |
| **Audit trail** | Append-only JSONL of every signal/locate/order with config version. |

## 9. Live trading & safety model

The live adapters ([`lowcap_short_system/live/`](lowcap_short_system/live)) are **dry-run by
default** and **hard-gated**:

- `TradeZeroClient(dry_run=True, ...)` — every call is logged to the audit trail and
  **simulated**; nothing is sent.
- Live routing requires **both** credentials present **and** an explicit env flag
  `LOWCAP_LIVE_ARMED=I_UNDERSTAND_REAL_MONEY` (see [`live/safety.py`](lowcap_short_system/live/safety.py)).
  An unarmed live order raises `LiveNotArmed` and **transmits nothing** (proven by test).
- **The agent never arms live trading.** Only the human operator does, knowingly.

**To go live (operator steps):**
1. Verify the real TradeZero endpoints/auth in onboarding; fill `.env` from `.env.example`.
2. Provide a real `Transport` (e.g. a `requests`/`httpx` wrapper) to
   `TradeZeroClient(dry_run=False, transport=...)`.
3. Set `LOWCAP_LIVE_ARMED=I_UNDERSTAND_REAL_MONEY` only when you intend to trade real money.
4. Walk the [`PROMOTION.md`](lowcap_short_system/PROMOTION.md) ladder — backtest → paper →
   tiny-live → scale — yourself, with quantitative exit criteria at each stage.

## 10. Testing & CI

- **Engine:** `python -m pytest tests -q` (71 tests), `python -m ruff check lowcap_short_system tests`,
  `python -m mypy lowcap_short_system`.
- **UI:** `cd ui; npm run test` (79 tests), `npm run build`.
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs all of the above on every
  push / PR.

Logic is test-pinned: microstructure features/strategies/engine, sizing min-of-caps, Reg SHO
fail-closed, circuit-breaker trips, audit append-only, secrets fail-loud, and the
"unarmed-live-sends-nothing" guarantee.

## 11. Roadmap / phase status

- ✅ **Phase 1** — Python L2 microstructure engine (book, features, strategies, sim).
- ✅ **Phase 2** — cockpit L2 panel + TypeScript mirror.
- ✅ **Offline Phase 4** — sizing, breakers, locate gate, paper OMS, audit, secrets, promotion
  gates, CI, and **dry-run** TradeZero adapters.
- ⛔ **Phase 3 (operator-gated)** — live broker depth + real order routing. Requires your live
  credentials, a funded account (≥ $25k), broker onboarding, and explicit authorization. The
  adapters are stubbed/dry-run behind the protocols, ready to wire.

---

*Built as a simulation and engineering exercise. Trading low-cap equities — especially shorting —
carries substantial, potentially unlimited risk. Validate everything against a backtest and paper
trading before risking any capital. Not financial advice.*











trading logics
Trading decisions happen in two places: **whether to enter a short**, and **whether to exit one**. Here's exactly how each is made.

## Entering a short

**Step 1 — Read the order book + tape into 5 signals.** Every tick, the engine computes:
- **Imbalance** — is there more size resting on the offer (ask) than the bid? A number from −1 to +1. Negative = sell pressure (bearish, good for a short).
- **Absorption** — is heavy buying repeatedly hitting the ask, but the ask keeps refreshing and price won't go higher? That's a hidden seller soaking up demand — the classic "top." 
- **Tape sweep / exhaustion** — did buying sweep across several prices and then *die out*? Climactic exhaustion.
- **Bid collapse** — is support on the bid side vanishing?
- **Spoofing score** — how much of the displayed size is fake (added then yanked without trading)?

**Step 2 — Each strategy casts a vote (with a strength 0–1):**
- Imbalance strategy votes "enter" if imbalance ≤ **−0.35**, strength = how lopsided it is.
- Absorption strategy votes "enter" if a hidden seller is present, strength = how strong.
- Tape strategy votes "enter" if there's exhaustion *after* a sweep (strength 0.7).

**Step 3 — Combine the votes into one decision:**
1. **Spoof veto first.** If the book is too fake (spoof score ≥ **0.5**), conviction is zeroed → **no entry**, no matter what else. It won't be fooled by fake walls.
2. **Add up conviction.** `score = sum of the enter-vote strengths × (0 if spoofy else 1)`.
3. **Threshold.** Enter only if `score ≥ 0.6`.

What that means in practice:
- **Strong absorption alone** (strength ~0.8) → clears 0.6 → **enters**. (A hidden seller is high-conviction by itself.)
- **A mild imbalance alone** (~0.4) → below 0.6 → **waits.** It needs a *second* confirmation, e.g. imbalance + tape exhaustion.
- **Spoofy book** → vetoed regardless.

This is deliberately the design philosophy: the cost of skipping a good trade is small; the cost of one squeeze is account-ending — so it errs toward *don't*.

## The gates after the signal (a "yes" can still be killed)
A confirmed entry signal is not an order yet. It must pass, in order:
1. **Halted?** If a circuit breaker or kill switch is engaged → rejected.
2. **Locate (Reg SHO)** — can you actually borrow the shares? No confirmed locate → **rejected, always**. (Fails closed.)
3. **Sizing** — the share count is the *minimum* of: volatility sizing, % of average volume, a hard dollar cap, and the shares you located. If that comes out to zero → rejected.
4. **Order** — placed as a marketable limit with a **protective stop attached automatically**.

So the L2 read decides *timing/conviction*; the gates decide *whether it's allowed and how big*. L2 is a confirmation layer, never a way around the risk rules.

## Exiting a position
An open short is closed when **any one** of these fires (whichever comes first):
- **Stop hit** — price reaches the stop (auto-cover).
- **Squeeze guard** — the stock runs against you past thresholds: intraday gain > 100%, RVOL > 10×, borrow fee > 300%, or **≥ 15% adverse** from entry → force-exit.
- **Tape exit** — a fresh up-sweep on the tape while you're short (the engine treats renewed aggressive buying as a squeeze starting).
- **Time stop** — flat by the close (it's an intraday system).
- **Borrow recall** — if the locate is lost mid-trade.

Exits always **dominate** entries — if you're in a position and an exit condition shows up, it exits, no debate.

Net: **enter only on confirmed, non-spoofed order-book exhaustion that's borrowable and within risk caps; exit fast on any sign it's going wrong.** Want me to show a concrete worked example end-to-end (one symbol, tick by tick), or go deeper on the sizing math or the squeeze guard?