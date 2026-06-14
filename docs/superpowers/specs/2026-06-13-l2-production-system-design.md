# Level 2 Microstructure Engine & Production-Readiness Blueprint — Design

> **Status:** Approved design / spec. Extends the operating blueprint
> [`lowcap_short_system/MASTER_BLUEPRINT.md`](../../../lowcap_short_system/MASTER_BLUEPRINT.md)
> and the architecture doc [`docs/lowcap-short-system-design.md`](../../lowcap-short-system-design.md).
> This spec adds the **Level 2 (depth-of-book) data + strategy layer** and the
> **production engineering plan**, and decomposes the work into phases.

## Purpose & Audience (readership)

**Purpose.** Be the single source of truth for evolving the prototype into a *production*
automated low-cap shorting engine that trades on **Level 2 market microstructure**. It
defines the depth-of-book data spine, the microstructure feature/strategy layer, how those
signals plug into the existing risk gates, and the engineering (infra, observability,
security, testing, promotion) required to run it safely with real capital.

**Audience.** (1) The builder/operator (primary) — enough detail to implement and run it.
(2) A future small engineering team — clear module boundaries and interfaces. (3) A
compliance/risk reviewer — explicit Reg SHO/SSR/PDT enforcement and audit trail.

**Guiding asymmetry (inherited from the blueprint).** Shorting low-caps has capped gains
and uncapped losses. L2 is a *timing/confirmation layer that feeds the existing locate →
Reg SHO → squeeze-guard gates — never a bypass of risk.* Every ambiguous decision resolves
toward *don't / smaller / abort*.

## 1. Scope

**In scope (this spec):** the L2 data model + book maintainer, the microstructure feature
layer, four L2 strategies, how strategies integrate with the blueprint's pipeline, an
L2-aware sim/backtest harness, and the production engineering plan across architecture,
observability, security/compliance, and testing/promotion. Plus a phased build plan.

**Out of scope / environment boundary.** Live broker/data wiring (real TradeZero/IBKR depth
and order routing) is **Phase 3+** and cannot be exercised without live credentials, a
funded account, and broker onboarding. This spec defines the **adapter interfaces** so live
wiring is a swap; Phases 1–2 run on mock/replay data. No real orders are sent from any code
built under Phases 1–2.

## 2. Stack & placement

- **Engine: Python 3.11+** in `lowcap_short_system/` (matches the existing scaffold, config
  YAML, and the Polygon/IBKR/TradeZero/moomoo SDK ecosystem; numpy/pandas/asyncio for
  microstructure + backtest). Tooling: `pytest`, `ruff`, `mypy`, `pydantic` for typed
  models/config.
- **Operator UI: the existing React cockpit** in `ui/` — unchanged here; in Phase 2 it gains
  an L2 panel fed by the engine over a thin read-only bridge (JSON snapshots).
- **Adapter pattern everywhere** at the I/O boundary (depth feed, trade feed, order router,
  locate) so mock/replay and live implementations are interchangeable.

New package layout under `lowcap_short_system/`:

```
microstructure/            # NEW — the L2 engine
  __init__.py
  book.py                  # OrderBook model + BookMaintainer (apply snapshots/deltas)
  events.py                # DepthSnapshot, DepthDelta, TradePrint, BookState (pydantic)
  feeds/
    base.py                # DepthFeed / TradeFeed adapter protocols
    replay.py              # ReplayDepthFeed (file/synthetic) — drives tests + sim
    mock.py                # MockDepthFeed (live-like synthetic stream for the cockpit)
    # tradezero.py, ibkr.py  -> Phase 3 stubs implementing the protocols
  features.py              # pure microstructure features (imbalance, absorption, tape, spoof)
  strategies/
    base.py                # Strategy protocol: (BookState, features) -> Signal
    imbalance.py  absorption.py  tape.py  spoof_filter.py
    engine.py              # composes strategies -> confirmed timing signals
  sim/
    harness.py             # replay -> features -> strategies -> signal-quality + fill model
    fills.py               # queue-position / displayed-size fill model
config/
  microstructure.yaml      # all L2 thresholds (never hardcoded)
```

## 3. Level 2 data spine

**Normalized model (`events.py`, pydantic):**
- `PriceLevel(price, size, orders?)`.
- `BookState(symbol, ts, bids: list[PriceLevel], asks: list[PriceLevel])` — top-N levels per
  side (N configurable, default 10), best bid/ask derived.
- `DepthSnapshot` (full book), `DepthDelta(side, price, new_size)` (incremental; size 0 =
  remove level), `TradePrint(ts, price, size, aggressor: 'buy'|'sell'|'unknown')`.

**`BookMaintainer` (`book.py`):** applies a snapshot then deltas to maintain a live
`BookState`; tracks per-level change history in a short ring buffer (needed for absorption &
spoofing). Detects crossed/locked books and staleness (no update in N ms → mark stale; a
stale book blocks new entries — fail safe).

**Feeds (`feeds/`):** `DepthFeed`/`TradeFeed` are async protocols yielding the event types
above. `ReplayDepthFeed` reads recorded/synthetic JSONL at controllable speed (drives unit
tests + the sim). `MockDepthFeed` generates a plausible live stream (drives the cockpit in
Phase 2). `tradezero.py`/`ibkr.py` are Phase-3 stubs raising `NotImplementedError` behind the
same protocol.

## 4. Microstructure feature layer (`features.py`, pure)

Functions over `BookState` + recent `TradePrint`/book history → typed feature values in
`[-1, 1]` or `[0, 1]`:
- **`order_book_imbalance(book, depth=k)`** — depth-weighted (bid_size − ask_size)/(sum),
  `+` = bid-heavy (supportive), `−` = ask-heavy (offer pressure). Weight near-touch levels
  higher.
- **`absorption(history, prints)`** — large executed volume at a level while displayed size
  *refreshes* (level holds despite prints) ⇒ hidden/iceberg seller absorbing buying =
  classic fade trigger at HOD. Returns strength + side.
- **`bid_stack_collapse(history)`** — rapid removal of bid depth across levels ⇒ support
  vanishing (entry/scale signal for the short).
- **`tape(prints, window)`** — trades/sec, sweep detection (multi-level single-aggressor
  prints), block prints, and an exhaustion flag (climactic volume then drop-off).
- **`spoofing_score(history)`** — level flicker/cancel rate (size appears then cancels before
  trading) ⇒ discount that depth as a *fake wall*; feeds a confidence multiplier the other
  features and strategies apply.

All pure, deterministic, unit-tested with hand-built book/tape fixtures.

## 5. L2 strategies (`strategies/`)

Each strategy implements `Strategy.evaluate(book, features, cfg) -> Signal | None`, where
`Signal(kind: 'enter'|'add'|'reduce'|'exit', side, strength, reason)`. Thresholds in
`config/microstructure.yaml`. Strategies **confirm/time** the blueprint's playbooks; they do
not open risk on their own — the engine's signal is an input to the existing entry gates.

1. **Imbalance pressure (`imbalance.py`)** — sustained ask-heavy imbalance (offer pressure)
   above threshold, discounted by `spoofing_score`, times a fade entry / supports adds.
2. **Absorption / iceberg (`absorption.py`)** — absorption at/again below HOD (hidden seller)
   ⇒ high-conviction fade `enter`; loss of absorption (seller pulls) ⇒ `reduce`.
3. **Tape & sweep (`tape.py`)** — buy-side exhaustion (sweep then tape slows, failed new
   high) ⇒ `enter`; renewed up-sweeps on accelerating tape against an open short ⇒ `exit`
   (ties to squeeze-guard force-exit).
4. **Spoof/fake-wall defense (`spoof_filter.py`)** — not a standalone entry; a *gating
   filter* that lowers signal confidence / vetoes entries when depth is spoofy, so the other
   three aren't fooled by flickering walls.

**`engine.py`** composes them: collects sub-signals, applies the spoof filter as a
confidence multiplier, and emits a single `ConfirmedSignal` only when conviction clears a
configurable bar. Output is consumed by the execution gate (Stage 6) — still subject to
locate (Stage 5), Reg SHO/SSR, sizing caps, and the squeeze guard (Stage 7).

## 6. Integration with the blueprint pipeline

- **Scanner/scoring (Stages 1–2):** L2 features add a *microstructure score* component
  (absorption present, healthy two-sided depth, low spoofiness) to the composite; spoofy or
  paper-thin books penalize.
- **Execution (Stage 6):** an entry fires only when the playbook setup **and** a
  `ConfirmedSignal` agree, a confirmed locate exists, Reg SHO/SSR pricing is satisfied, and
  sizing caps pass. L2 also sets the marketable-limit offset from the book.
- **Management (Stage 7):** L2 exit signals (renewed sweeps, bid collapse against us,
  absorption flipping) feed the squeeze-guard force-exit path. L2 never overrides a
  risk-driven exit; it can only make exits *earlier*.

## 7. Sim / backtest harness (`sim/`)

`harness.py` replays recorded/synthetic depth+tape through the feature+strategy stack and
measures **signal quality**: lead time from signal to actual reversal, true/false-positive
rate, and per-strategy contribution. `fills.py` models fills against *displayed* depth
(queue position, partial fills, sweep-through), not flat bps — extending blueprint §14's
slippage realism to the book level. Outputs feed threshold tuning in
`config/microstructure.yaml`.

## 8. Production engineering plan

**Architecture/infra.** Event-driven `asyncio` pipeline: feed handler → `BookMaintainer` →
feature layer → strategy engine → OMS, connected by in-process async queues (a clean seam to
swap for a real message bus later). Single process now; the queue boundaries allow splitting
into services (feed, strategy, OMS) later. **Reconnection-to-flat:** any feed/heartbeat gap
blocks new entries and, if prolonged, force-flattens — never holds naked risk through a
blackout. A documented **latency budget** (feed→signal→order) with metrics to enforce it.

**Observability/ops.** Structured JSON logging with correlation IDs per signal/order; metrics
(feed lag, book staleness, events/sec, signal counts, fill quality, breaker state) exposed for
scraping; alerting on staleness, breaker trips, and auth/feed loss; health endpoints; the
failure-mode runbook (blueprint §17) extended with L2-feed failures.

**Security/compliance.** Secrets via environment/secret store (never in repo); least-privilege
API keys; an **append-only audit log** of every signal, locate, and order with the config
version that produced it; Reg SHO (locate-before-short, fail closed), SSR Rule 201 pricing,
and PDT equity floor enforced in the OMS; recordkeeping/retention policy for the trade journal.

**Testing/backtest/promotion.** `pytest` unit (pure features/strategies/book) + integration
(replay → engine → mock OMS); `ruff`+`mypy` and the test suite in CI; the L2 sim harness as a
validation gate; explicit promotion gates — **backtest → paper (order logic) → tiny-live →
scale** — each with quantitative criteria before advancing, and a config snapshot per stage.

## 9. Phased decomposition (each phase is its own plan → build cycle)

1. **Phase 1 — L2 engine core (BUILD NOW).** `events`, `book`+`BookMaintainer`, `features`,
   the four `strategies` + `engine`, `ReplayDepthFeed`, and the `sim` harness — pure Python,
   mock/replay-driven, fully unit-tested. Adapter protocols defined; live adapters stubbed.
   Deliverable: a tested microstructure engine that turns a depth/tape stream into confirmed
   signals and can be evaluated offline.
2. **Phase 2 — Integrate + visualize.** Wire L2 score into scanner/exec gates; add a cockpit
   **L2 panel** (depth ladder + tape + live signal badges) fed by `MockDepthFeed`/a bridge.
3. **Phase 3 — Live adapters (needs broker creds).** Implement `tradezero.py`/`ibkr.py` depth
   + order adapters against the protocols; paper-test order logic.
4. **Phase 4 — Production hardening.** Infra/observability/security per §8 → tiny-live with
   promotion gates.

## 10. Phase 1 success criteria

- `microstructure/` package importable; `pytest` green; `ruff` + `mypy` clean.
- A documented run (`python -m lowcap_short_system.microstructure.sim.harness` on a bundled
  synthetic scenario) prints signal-quality metrics for a scripted pump-fade-into-absorption
  scenario, demonstrating the engine emits a fade `enter` near the synthetic top and an
  `exit` on a synthetic squeeze — with the spoof filter vetoing a fake-wall scenario.
- Every threshold lives in `config/microstructure.yaml`; nothing hardcoded.
- No network/broker calls anywhere in Phase 1 code.
