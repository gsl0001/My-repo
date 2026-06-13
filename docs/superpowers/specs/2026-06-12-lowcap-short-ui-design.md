# LowCap Short — Operator UI (Prototype) — Design

> Status: **Approved design / spec** — ready for implementation plan.
> Companion to [`../../lowcap-short-system-design.md`](../../lowcap-short-system-design.md).

## 1. Goal

A front-end **operator console** for the automated intraday low-cap shorting system. The
backend does not exist yet, so this is a **prototype driven entirely by realistic mock
data** — it looks and behaves like a live trading cockpit, but is not wired to any real
broker or data feed. Its job is to make the system from the design doc concrete and
demonstrable: what the operator watches, what the squeeze guard and circuit breakers do,
and how locates gate every short.

The mock-data layer is deliberately isolated so that wiring in real TradeZero / Polygon /
IBKR / EDGAR feeds later means replacing that one layer — components do not change.

## 2. Scope

**In scope (three tabs):**
1. **Cockpit** — the live monitoring war-room (default tab).
2. **Config** — the tunable §8 universe params and §9 squeeze / circuit-breaker thresholds.
3. **Backtest** — a static backtest result viewer.

**Out of scope (prototype boundaries):**
- No real API wiring (TradeZero, Polygon, IBKR, EDGAR) — mock data only.
- No authentication, no server, no persistence beyond in-memory state (resets on reload).
- No real order entry. The kill switch, exits, and order/locate flows act on **mock
  state only**.
- Not mobile-optimized — target is a desktop trading screen (≥ 1280px wide).

## 3. Stack & project structure

- **React 18 + Vite + TypeScript + Tailwind CSS.** Run with `npm install && npm run dev`.
- All source under a new top-level `ui/` directory (sibling to `lowcap_short_system/`),
  self-contained so it does not entangle the Python scaffold.

```
ui/
  index.html
  package.json  vite.config.ts  tailwind.config.ts  tsconfig.json
  src/
    main.tsx  App.tsx                 # shell: top bar + tab router (3 tabs)
    theme.css                         # design tokens (CSS vars) + Tailwind layer
    components/                       # shared primitives
      Panel.tsx  DataTable.tsx  StatRow.tsx  Pill.tsx
      ProgressBar.tsx  Sparkline.tsx  TopBar.tsx  KillSwitch.tsx
    mockData/                         # THE swappable layer (single source of truth)
      types.ts                        # Position, Order, Candidate, LogEvent, Config, ...
      seed.ts                         # deterministic seeded initial state
      generators.ts                   # symbol/price/score/log factories
      useTickEngine.ts                # interval hook: drift prices, P&L, orders, log
      store.ts                        # React context holding live mock state + actions
    tabs/
      cockpit/   Cockpit.tsx  Positions.tsx  ActiveOrders.tsx  Scanner.tsx
                 RightRail.tsx  LiveLog.tsx
      config/    Config.tsx  UniverseForm.tsx  SqueezeForm.tsx  BreakersForm.tsx
      backtest/  Backtest.tsx  EquityCurve.tsx  StatGrid.tsx  TradesTable.tsx
```

**Routing:** a single in-memory tab state in `App.tsx` (no router dependency needed for
3 tabs). Top bar + kill switch are persistent across tabs.

## 4. Visual system (design tokens)

Terminal-leaning blend, leaning terminal: deep black, monospace numerics, bright green/red
P&L, softened with subtly rounded panels, breathing room, and a teal accent. Defined once
as CSS variables / Tailwind theme tokens; every component consumes them (no hardcoded
hex in components).

| Token | Value | Use |
|---|---|---|
| `--bg` | `#04060a` | app background |
| `--bg-bar` | `#070b11` | top bar / log strip |
| `--panel` | `#090d14` | panel surfaces |
| `--border` | `#141b27` | panel borders / row dividers (`#0f141d`) |
| `--text` | `#c9d1d9` | body text |
| `--text-strong` | `#e6edf3` | symbols / emphasis |
| `--text-muted` | `#6e7681` / `#5c636d` | labels / secondary |
| `--accent` | `#2dd4bf` | active tab, selection, streaming dot, links |
| `--up` | `#3fb950` | gains / "ok" guard / fills |
| `--down` | `#f85149` | losses / "exit" guard / kill switch |
| `--warn` | `#d29922` | caution / partial / squeeze alerts |
| `--info` | `#58a6ff` / `#9bbce8` | working orders / signals |
| `--violet` | `#a78bfa` | locate events |

- **Type:** UI labels in system sans (`system-ui`); **all numerics in monospace**
  (`'SF Mono', Consolas, monospace`). Section labels are 9–9.5px, uppercase, letter-spaced.
- **Density:** compact rows (~4px vertical padding); panels `border-radius: 8px`,
  outer cards `10px`.

## 5. Mock data layer

The heart of the prototype. One module owns all state; a tick engine animates it.

**Entities (`types.ts`):**
- `Position` — symbol, shortQty, avgPrice, last, pctFromEntry, unrealizedPnl, stopPrice,
  borrowFeePct, guardState (`ok | caution | exit`).
- `Order` — symbol, side (`SHORT | BUY | LOCATE`), type (`LMT | STP | REQ`), qty, price,
  filledQty, ageSec, status (`working | partial | stop-resting | pending-locate |
  filled | rejected`).
- `Candidate` (scanner row) — symbol, last, pctChange, rvol, floatM, borrowFeePct,
  pumpScore, dilutionScore, borrowScore, compositeScore, locate (`{ ok, costPerShare }`
  or `{ ok:false, reason }`).
- `LogEvent` — timestamp (ms precision), kind (`DATA | SIGNAL | GUARD | LOCATE | ORDER |
  FILL | EXIT | RISK | HALT`), message, optional pnl.
- `Account` — equity, dayPnl, grossShort, grossLimit, drawdownPct, drawdownLimitPct,
  positionsCount, positionsMax, halted (bool).
- `Config` — the §8/§9 knobs (see §7).

**`useTickEngine`** (≈1s interval, pausable):
- Random-walks `last` prices for positions + candidates; recomputes pct / unrealized P&L /
  account day-P&L and the drawdown meter.
- Advances orders: working → partial → filled; ages locate requests; occasionally spawns
  a new candidate or order.
- Evaluates the **squeeze guard** (§9 thresholds) per position each tick → sets guardState
  and, on force-exit conditions, emits a `GUARD` + `EXIT` log pair and closes the position.
- Appends `LogEvent`s to a capped ring buffer (newest first) so the live log scrolls.
- When `halted` is true (kill switch), it stops opening new orders/positions and flattens.

State lives in a React context (`store.ts`) exposing the snapshot plus actions:
`triggerKill()`, `resumeTrading()`, `cancelOrder(id)`, `coverPosition(sym)`,
`updateConfig(patch)`. Seed is deterministic so reloads start from the same scene.

## 6. Cockpit tab

Layout: persistent **top bar** (logo · tabs · account stats `EQUITY / DAY / GROSS` ·
**KILL SWITCH**), then a `2fr / 1fr` grid, then a full-width log.

- **Open Positions** (top-left) — table: SYM · SHORT qty · AVG · LAST · % · uP&L · STOP ·
  FEE · GUARD. % / uP&L colored; GUARD shows `ok / caution / EXIT`. Row click → cover
  (mock). Updates every tick.
- **Active Orders** (mid-left) — table: SYM · SIDE · TYPE · QTY · PRICE · FILLED · AGE ·
  STATUS, with status dots: `● working` (info), `◐ partial` (warn), `◇ stop resting`
  (muted), `⧗ pending locate` (violet). Header carries the Reg SHO reminder
  ("no short w/o locate"). Row click → cancel working order (mock).
- **Live Scanner / In Play** (bottom-left) — candidate table: SYM · LAST · %CHG · RVOL ·
  FEE · PUMP · DIL · SCORE · LOCATE gate (`✓ $cost` green / `✕ reason` red). Top composite
  score highlighted with accent. "● streaming" indicator.
- **Right rail** (stacked panels):
  - **Day P&L** — big monospace number + 6-bar sparkline.
  - **Circuit Breakers** — daily drawdown meter (value / limit) + Positions (n/max) +
    Gross short ($/limit). Bar turns warn→down as it approaches a limit.
  - **Squeeze Alerts** — names currently in caution/exit with reason (gain, RVOL, fee).
  - **Locates Reserved** — reserved shares + cost, flag unused (sunk-cost reminder).
- **Live Log** (full-width bottom) — reverse-chronological feed, ms timestamps, color-coded
  `kind` chips (DATA/SIGNAL/GUARD/LOCATE/ORDER/FILL/EXIT/RISK/HALT). Auto-scrolls as
  the tick engine appends; "● N events / min" indicator.

**Kill switch flow:** click → confirm modal ("Flatten all positions and halt new
orders?") → on confirm sets `halted`, emits `HALT` + per-position `EXIT` log events,
zeroes positions/working orders, and shows a persistent red banner "TRADING HALTED" with
a **Resume** action. Purely mock-state.

## 7. Config tab

Three forms, each mapping directly to the design doc. Edits call `updateConfig` and flow
live into the cockpit's mock evaluation (e.g. lowering the force-exit gain threshold makes
more positions flip to EXIT on the next tick) so tuning feels real.

- **Universe (§8)** — market-cap band ($min/$max), price floor/ceiling, min avg $ volume,
  min ADV shares, low-float flag threshold, max borrow fee (soft/hard), listing filter.
- **Squeeze guard (§9)** — for each signal (intraday % gain, RVOL, borrow fee, float,
  adverse move) the caution / abort / force-exit thresholds, as a clear three-column grid.
- **Account circuit breakers** — per-position max loss %, daily drawdown limit %, max
  concurrent positions, max gross short $, kill-switch arm/disarm.

Each field has its starting default from the design doc and a one-line rationale tooltip.
"Reset to design defaults" button.

## 8. Backtest tab

Static mock result set (no live engine):
- **Equity curve** — SVG line chart of cumulative P&L over a sample date range, with
  drawdown shading.
- **Stat grid** — total P&L, win rate, profit factor, max drawdown, Sharpe, avg hold time,
  avg borrow cost, slippage drag, # trades. Each a labeled stat card.
- **Trades table** — sample closed trades: date, symbol, side, entry, exit, P&L, % return,
  borrow cost, hold time, exit reason (target / stop / time / guard). Sortable.

## 9. Shared components

- `Panel` — titled surface (label + optional right-aligned status) with consistent
  border/radius/padding.
- `DataTable` — generic compact table (column defs + right-align + cell renderers for
  colored numbers / pills).
- `Pill` — small status chip (the log `kind` chips and order-status dots reuse this).
- `StatRow` — label-left / value-right line used across rail panels and config.
- `ProgressBar` — used by circuit-breaker meters; color thresholds (up→warn→down).
- `Sparkline` — tiny inline bar/line series (Day P&L; reused if needed).
- `TopBar` / `KillSwitch` — persistent shell elements.

## 10. Testing & verification

- **Type safety:** TypeScript strict; `npm run build` must pass clean.
- **Unit tests (Vitest):** the pure logic in `mockData` — squeeze-guard evaluation
  (threshold → guardState transitions), P&L math, order-lifecycle advance, and config
  edits changing guard outcomes. These are the parts with real logic; UI is presentational.
- **Manual verification:** `npm run dev`, confirm all three tabs render, prices/P&L/log
  tick live, kill switch flattens + halts + resumes, and a config threshold change visibly
  changes cockpit guard states.

## 11. Out of scope / future

- Replace `mockData/` with real adapters (Polygon WS for prices/scanner, TradeZero REST/WS
  for orders + locates, IBKR borrow file ingest, EDGAR catalyst feed) behind the same
  `store` interface.
- Auth, multi-session, persistence, alerting/notifications, mobile layout.
