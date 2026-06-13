# LowCap Short Operator UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React/Vite/TypeScript/Tailwind operator console (Cockpit · Config · Backtest) for the intraday low-cap shorting system, driven entirely by a swappable mock-data layer that ticks live.

**Architecture:** A single in-memory `store` (React context) holds all state. Pure logic modules (guard evaluation, P&L math, order lifecycle) are unit-tested with Vitest. A `useTickEngine` hook advances the store on an interval so prices/P&L/orders/log feel live. Presentational components compose a small set of shared primitives and read the store. Replacing `mockData/` with real adapters later leaves components untouched.

**Tech Stack:** React 18, Vite, TypeScript (strict), Tailwind CSS v3, Vitest + @testing-library/react (jsdom).

**Spec:** [`../specs/2026-06-12-lowcap-short-ui-design.md`](../specs/2026-06-12-lowcap-short-ui-design.md)

**Commit convention:** every commit message ends with a trailer line `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Commit commands below omit it for brevity — add it.

**Working directory:** all paths are relative to the repo root. The app lives under `ui/`. Run npm/vitest commands from inside `ui/`.

---

## File Structure

```
ui/
  index.html
  package.json  vite.config.ts  tailwind.config.ts  postcss.config.js
  tsconfig.json  tsconfig.node.json  vitest.setup.ts
  src/
    main.tsx                       # React entry
    App.tsx                        # shell: StoreProvider + TopBar + tab router
    index.css                      # Tailwind layers + base body styles
    mockData/
      types.ts                     # all domain types
      rng.ts                       # seeded deterministic RNG
      guard.ts                     # evaluateGuard() — pure
      pnl.ts                       # short P&L + account math — pure
      orders.ts                    # advanceOrder() lifecycle — pure
      seed.ts                      # initial deterministic state
      generators.ts                # candidate / log factories
      useTickEngine.ts             # interval hook advancing the store
      store.tsx                    # context: state snapshot + actions
    components/
      Panel.tsx  DataTable.tsx  Pill.tsx  StatRow.tsx
      ProgressBar.tsx  Sparkline.tsx  TopBar.tsx  KillSwitch.tsx
    tabs/
      cockpit/  Cockpit.tsx  Positions.tsx  ActiveOrders.tsx
                Scanner.tsx  RightRail.tsx  LiveLog.tsx
      config/   Config.tsx
      backtest/ Backtest.tsx  backtestData.ts
  src/**/__tests__/*.test.ts(x)    # colocated tests
```

---

## Task 1: Scaffold the app

**Files:**
- Create: `ui/package.json`, `ui/vite.config.ts`, `ui/tsconfig.json`, `ui/tsconfig.node.json`, `ui/postcss.config.js`, `ui/tailwind.config.ts`, `ui/index.html`, `ui/src/main.tsx`, `ui/src/App.tsx`, `ui/src/index.css`, `ui/vitest.setup.ts`

- [ ] **Step 1: Create `ui/package.json`**

```json
{
  "name": "lowcap-short-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "jsdom": "^25.0.0",
    "postcss": "^8.4.45",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.4",
    "vite": "^5.4.3",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: Create config files**

`ui/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

`ui/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

`ui/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "vitest.setup.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`ui/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts", "tailwind.config.ts"]
}
```

`ui/postcss.config.js`:
```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

`ui/tailwind.config.ts` — **single source of truth for the palette**:
```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#04060a",
        bar: "#070b11",
        panel: "#090d14",
        edge: "#141b27",
        rowdiv: "#0f141d",
        body: "#c9d1d9",
        strong: "#e6edf3",
        muted: "#6e7681",
        muted2: "#5c636d",
        accent: "#2dd4bf",
        up: "#3fb950",
        down: "#f85149",
        warn: "#d29922",
        info: "#58a6ff",
        info2: "#9bbce8",
        violet: "#a78bfa",
      },
      fontFamily: {
        mono: ["'SF Mono'", "Consolas", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 3: Create entry files**

`ui/index.html`:
```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>LowCap Short — Operator Console</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`ui/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body {
  margin: 0;
  background: #04060a;
  color: #c9d1d9;
  font-family: system-ui, "Segoe UI", sans-serif;
  font-size: 13px;
}
```

`ui/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

`ui/src/App.tsx` (temporary stub — replaced in Task 16):
```tsx
export default function App() {
  return <div className="p-4 text-strong">LowCap Short — scaffold OK</div>;
}
```

- [ ] **Step 4: Install and verify build**

Run (from `ui/`): `npm install && npm run build`
Expected: install completes; `tsc -b` reports no errors; `vite build` writes `dist/` with no errors.

- [ ] **Step 5: Verify dev server boots**

Run (from `ui/`): `npm run dev`
Expected: Vite prints a `localhost` URL and starts without error. Stop it (Ctrl-C) after confirming.

- [ ] **Step 6: Commit**

```bash
git add ui/
git commit -m "chore(ui): scaffold Vite + React + TS + Tailwind app"
```

---

## Task 2: Domain types

**Files:**
- Create: `ui/src/mockData/types.ts`

- [ ] **Step 1: Write the types file**

```ts
export type GuardState = "ok" | "caution" | "exit";

export interface Position {
  id: string;
  symbol: string;
  shortQty: number;
  avgPrice: number;
  last: number;
  priorClose: number;       // for intraday-gain calc
  pctFromEntry: number;     // (avg - last)/avg*100; positive = profit on a short
  unrealizedPnl: number;    // (avg - last) * shortQty
  stopPrice: number;
  borrowFeePct: number;
  rvol: number;
  floatM: number;           // float in millions of shares
  guardState: GuardState;
}

export type OrderSide = "SHORT" | "BUY" | "LOCATE";
export type OrderType = "LMT" | "STP" | "REQ";
export type OrderStatus =
  | "working"
  | "partial"
  | "stop-resting"
  | "pending-locate"
  | "filled"
  | "rejected";

export interface Order {
  id: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  qty: number;
  price: number | null;
  filledQty: number;
  ageSec: number;
  status: OrderStatus;
}

export interface LocateInfo {
  ok: boolean;
  costPerShare?: number;
  reason?: string;
}

export interface Candidate {
  id: string;
  symbol: string;
  last: number;
  pctChange: number;        // vs prior close
  rvol: number;
  floatM: number;
  borrowFeePct: number;
  pumpScore: number;        // 0..1
  dilutionScore: number;    // 0..1
  borrowScore: number;      // 0..1
  compositeScore: number;   // 0..1
  locate: LocateInfo;
}

export type LogKind =
  | "DATA" | "SIGNAL" | "GUARD" | "LOCATE"
  | "ORDER" | "FILL" | "EXIT" | "RISK" | "HALT";

export interface LogEvent {
  id: string;
  ts: number;               // epoch ms
  kind: LogKind;
  message: string;
  pnl?: number;
}

export interface Account {
  startEquity: number;
  equity: number;
  dayPnl: number;
  realizedPnl: number;
  grossShort: number;
  grossLimit: number;
  drawdownPct: number;      // <= 0, peak-to-now
  positionsCount: number;
  halted: boolean;
}

export interface SqueezeThresholds {
  gainCautionPct: number;   // default 50
  gainAbortPct: number;     // default 100
  rvolCaution: number;      // default 5
  rvolAbort: number;        // default 10
  feeCautionPct: number;    // default 100
  feeAbortPct: number;      // default 300
  floatCautionM: number;    // default 20
  floatAbortM: number;      // default 5
  adverseExitPct: number;   // default 15
}

export interface UniverseParams {
  capMinM: number;          // 10
  capMaxM: number;          // 500
  priceFloor: number;       // 1
  priceCeiling: number;     // 25
  minDollarVolM: number;    // 3
  minAdvK: number;          // 500
  lowFloatFlagM: number;    // 20
  maxBorrowFeeSoftPct: number; // 100
  maxBorrowFeeHardPct: number; // 300
}

export interface CircuitBreakers {
  perPositionMaxLossPct: number; // 18
  dailyDrawdownLimitPct: number; // -4
  maxPositions: number;          // 6
  maxGrossShort: number;         // 150000
}

export interface Config {
  universe: UniverseParams;
  squeeze: SqueezeThresholds;
  breakers: CircuitBreakers;
}

export interface AppState {
  positions: Position[];
  orders: Order[];
  candidates: Candidate[];
  log: LogEvent[];          // newest first, capped
  account: Account;
  config: Config;
  eventsPerMin: number;
}
```

- [ ] **Step 2: Verify it type-checks**

Run (from `ui/`): `npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add ui/src/mockData/types.ts
git commit -m "feat(ui): domain types for mock data layer"
```

---

## Task 3: Seeded RNG

**Files:**
- Create: `ui/src/mockData/rng.ts`, `ui/src/mockData/__tests__/rng.test.ts`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/rng.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { makeRng } from "../rng";

describe("makeRng", () => {
  it("is deterministic for a given seed", () => {
    const a = makeRng(42);
    const b = makeRng(42);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });

  it("returns values in [0, 1)", () => {
    const r = makeRng(7);
    for (let i = 0; i < 100; i++) {
      const v = r();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it("differs across seeds", () => {
    expect(makeRng(1)()).not.toEqual(makeRng(2)());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- rng`
Expected: FAIL — cannot find module `../rng`.

- [ ] **Step 3: Implement `rng.ts`**

```ts
// Mulberry32 — small deterministic PRNG. Returns a function yielding [0,1).
export function makeRng(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Helpers built on a base rng.
export function randBetween(rng: () => number, lo: number, hi: number): number {
  return lo + (hi - lo) * rng();
}

export function pick<T>(rng: () => number, arr: readonly T[]): T {
  return arr[Math.floor(rng() * arr.length)];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- rng`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/mockData/rng.ts ui/src/mockData/__tests__/rng.test.ts
git commit -m "feat(ui): seeded deterministic RNG"
```

---

## Task 4: Squeeze-guard evaluation (pure)

**Files:**
- Create: `ui/src/mockData/guard.ts`, `ui/src/mockData/__tests__/guard.test.ts`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/guard.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { evaluateGuard, defaultSqueeze, type GuardInput } from "../guard";

const base: GuardInput = {
  intradayGainPct: 10,
  rvol: 2,
  borrowFeePct: 40,
  floatM: 50,
  adverseMovePct: 0,
};

describe("evaluateGuard", () => {
  it("returns ok when all signals are calm", () => {
    expect(evaluateGuard(base, defaultSqueeze)).toBe("ok");
  });

  it("forces exit when adverse move crosses the exit threshold", () => {
    expect(evaluateGuard({ ...base, adverseMovePct: 16 }, defaultSqueeze)).toBe("exit");
  });

  it("forces exit on parabolic gain past the abort threshold", () => {
    expect(evaluateGuard({ ...base, intradayGainPct: 120 }, defaultSqueeze)).toBe("exit");
  });

  it("forces exit when borrow fee passes the abort threshold", () => {
    expect(evaluateGuard({ ...base, borrowFeePct: 320 }, defaultSqueeze)).toBe("exit");
  });

  it("flags caution on elevated RVOL", () => {
    expect(evaluateGuard({ ...base, rvol: 6 }, defaultSqueeze)).toBe("caution");
  });

  it("flags caution on low float", () => {
    expect(evaluateGuard({ ...base, floatM: 12 }, defaultSqueeze)).toBe("caution");
  });

  it("config edits change outcomes: lowering gain abort flips ok->exit", () => {
    const tight = { ...defaultSqueeze, gainAbortPct: 5 };
    expect(evaluateGuard({ ...base, intradayGainPct: 10 }, tight)).toBe("exit");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- guard`
Expected: FAIL — cannot find module `../guard`.

- [ ] **Step 3: Implement `guard.ts`**

```ts
import type { GuardState, SqueezeThresholds } from "./types";

export const defaultSqueeze: SqueezeThresholds = {
  gainCautionPct: 50,
  gainAbortPct: 100,
  rvolCaution: 5,
  rvolAbort: 10,
  feeCautionPct: 100,
  feeAbortPct: 300,
  floatCautionM: 20,
  floatAbortM: 5,
  adverseExitPct: 15,
};

export interface GuardInput {
  intradayGainPct: number;  // stock gain vs prior close
  rvol: number;
  borrowFeePct: number;
  floatM: number;
  adverseMovePct: number;   // positive = price moved against the short since entry
}

// Force-exit dominates; otherwise caution; otherwise ok.
export function evaluateGuard(i: GuardInput, t: SqueezeThresholds): GuardState {
  const exit =
    i.adverseMovePct >= t.adverseExitPct ||
    i.intradayGainPct >= t.gainAbortPct ||
    i.rvol >= t.rvolAbort ||
    i.borrowFeePct >= t.feeAbortPct;
  if (exit) return "exit";

  const caution =
    i.intradayGainPct >= t.gainCautionPct ||
    i.rvol >= t.rvolCaution ||
    i.borrowFeePct >= t.feeCautionPct ||
    i.floatM <= t.floatCautionM;
  return caution ? "caution" : "ok";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- guard`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/mockData/guard.ts ui/src/mockData/__tests__/guard.test.ts
git commit -m "feat(ui): squeeze-guard evaluation"
```

---

## Task 5: P&L and account math (pure)

**Files:**
- Create: `ui/src/mockData/pnl.ts`, `ui/src/mockData/__tests__/pnl.test.ts`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/pnl.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { shortUnrealized, shortPctFromEntry, adverseMovePct } from "../pnl";

describe("short P&L math", () => {
  it("profits when price falls below entry", () => {
    expect(shortUnrealized(4.21, 4.12, 8000)).toBeCloseTo(720, 5);
  });

  it("loses when price rises above entry", () => {
    expect(shortUnrealized(1.98, 2.07, 12000)).toBeCloseTo(-1080, 5);
  });

  it("pctFromEntry is positive when profitable", () => {
    expect(shortPctFromEntry(4.21, 4.12)).toBeCloseTo(2.138, 2);
  });

  it("adverseMovePct is 0 when in profit, positive when against", () => {
    expect(adverseMovePct(4.21, 4.12)).toBe(0);
    expect(adverseMovePct(1.98, 2.07)).toBeCloseTo(4.545, 2);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- pnl`
Expected: FAIL — cannot find module `../pnl`.

- [ ] **Step 3: Implement `pnl.ts`**

```ts
export function shortUnrealized(avg: number, last: number, qty: number): number {
  return (avg - last) * qty;
}

export function shortPctFromEntry(avg: number, last: number): number {
  return ((avg - last) / avg) * 100;
}

// Positive number = how far price has moved against the short (price above entry).
export function adverseMovePct(avg: number, last: number): number {
  return Math.max(0, ((last - avg) / avg) * 100);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- pnl`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/mockData/pnl.ts ui/src/mockData/__tests__/pnl.test.ts
git commit -m "feat(ui): short P&L math helpers"
```

---

## Task 6: Order lifecycle (pure)

**Files:**
- Create: `ui/src/mockData/orders.ts`, `ui/src/mockData/__tests__/orders.test.ts`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/orders.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { advanceOrder } from "../orders";
import type { Order } from "../types";

const working: Order = {
  id: "o1", symbol: "DROP", side: "SHORT", type: "LMT",
  qty: 6000, price: 5.2, filledQty: 0, ageSec: 0, status: "working",
};

describe("advanceOrder", () => {
  it("ages the order by dt seconds", () => {
    const out = advanceOrder(working, 1, () => 0.99);
    expect(out.ageSec).toBe(1);
  });

  it("fills partially when the roll lands mid-range", () => {
    const out = advanceOrder(working, 1, () => 0.5);
    expect(out.status).toBe("partial");
    expect(out.filledQty).toBeGreaterThan(0);
    expect(out.filledQty).toBeLessThan(out.qty);
  });

  it("completes a partial into filled", () => {
    const partial: Order = { ...working, status: "partial", filledQty: 4000 };
    const out = advanceOrder(partial, 1, () => 0.1);
    expect(out.status).toBe("filled");
    expect(out.filledQty).toBe(out.qty);
  });

  it("resolves a pending locate into a working short", () => {
    const locate: Order = {
      ...working, side: "LOCATE", type: "REQ", price: null,
      status: "pending-locate", ageSec: 3,
    };
    const out = advanceOrder(locate, 1, () => 0.1);
    expect(out.status).toBe("working");
    expect(out.side).toBe("SHORT");
  });

  it("leaves resting stops untouched", () => {
    const stop: Order = { ...working, side: "BUY", type: "STP", status: "stop-resting" };
    const out = advanceOrder(stop, 5, () => 0.0);
    expect(out.status).toBe("stop-resting");
    expect(out.ageSec).toBe(5);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- orders`
Expected: FAIL — cannot find module `../orders`.

- [ ] **Step 3: Implement `orders.ts`**

```ts
import type { Order } from "./types";

// Advance one order by dt seconds. `roll` is an injected [0,1) value for determinism.
// - working LMT: roll<0.3 -> filled, roll<0.7 -> partial, else stays working
// - partial:     roll<0.6 -> filled, else stays partial (more fills)
// - pending-locate (REQ) older than 2s: roll<0.8 -> becomes working SHORT LMT
// - stop-resting: unchanged
export function advanceOrder(order: Order, dt: number, roll: number): Order {
  const o: Order = { ...order, ageSec: order.ageSec + dt };

  if (o.status === "stop-resting" || o.status === "filled" || o.status === "rejected") {
    return o;
  }

  if (o.status === "pending-locate") {
    if (o.ageSec >= 2 && roll < 0.8) {
      return { ...o, side: "SHORT", type: "LMT", status: "working", filledQty: 0 };
    }
    return o;
  }

  if (o.status === "working") {
    if (roll < 0.3) return { ...o, status: "filled", filledQty: o.qty };
    if (roll < 0.7) {
      return { ...o, status: "partial", filledQty: Math.round(o.qty * (0.3 + roll * 0.4)) };
    }
    return o;
  }

  if (o.status === "partial") {
    if (roll < 0.6) return { ...o, status: "filled", filledQty: o.qty };
    const add = Math.round((o.qty - o.filledQty) * 0.5);
    return { ...o, filledQty: Math.min(o.qty, o.filledQty + add) };
  }

  return o;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- orders`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/mockData/orders.ts ui/src/mockData/__tests__/orders.test.ts
git commit -m "feat(ui): order lifecycle advance"
```

---

## Task 7: Seed state + generators

**Files:**
- Create: `ui/src/mockData/seed.ts`, `ui/src/mockData/generators.ts`, `ui/src/mockData/__tests__/seed.test.ts`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/seed.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { makeSeedState } from "../seed";

describe("makeSeedState", () => {
  it("is deterministic for the same seed", () => {
    expect(makeSeedState(1)).toEqual(makeSeedState(1));
  });

  it("starts with positions, orders, candidates and a log", () => {
    const s = makeSeedState(1);
    expect(s.positions.length).toBeGreaterThan(0);
    expect(s.orders.length).toBeGreaterThan(0);
    expect(s.candidates.length).toBeGreaterThan(0);
    expect(s.log.length).toBeGreaterThan(0);
    expect(s.account.halted).toBe(false);
  });

  it("derives unrealized P&L on positions", () => {
    const s = makeSeedState(1);
    const p = s.positions[0];
    expect(p.unrealizedPnl).toBeCloseTo((p.avgPrice - p.last) * p.shortQty, 4);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- seed`
Expected: FAIL — cannot find module `../seed`.

- [ ] **Step 3: Implement `generators.ts`**

```ts
import type { Candidate, LocateInfo, LogEvent, LogKind } from "./types";
import { makeRng, randBetween, pick } from "./rng";

const SYMBOLS = ["PLTX", "DROP", "GNSX", "MULN", "CABL", "VRAX", "TICK", "BBLG", "ZKIN", "RGTI"];

export function symbolPool(): string[] {
  return [...SYMBOLS];
}

export function makeCandidate(seed: number, symbol: string): Candidate {
  const rng = makeRng(seed);
  const last = randBetween(rng, 1.2, 12);
  const pumpScore = randBetween(rng, 0.3, 0.95);
  const dilutionScore = randBetween(rng, 0.1, 0.85);
  const borrowFeePct = randBetween(rng, 20, 320);
  const borrowScore = Math.max(0, 1 - borrowFeePct / 320);
  const composite = Number(
    (pumpScore * 0.45 + dilutionScore * 0.3 + borrowScore * 0.25).toFixed(2)
  );
  const noBorrow = borrowFeePct > 290;
  const locate: LocateInfo = noBorrow
    ? { ok: false, reason: "no borrow" }
    : { ok: true, costPerShare: Number(randBetween(rng, 0.01, 0.05).toFixed(2)) };
  return {
    id: `c-${symbol}`,
    symbol,
    last: Number(last.toFixed(2)),
    pctChange: Math.round(randBetween(rng, 18, 110)),
    rvol: Number(randBetween(rng, 3, 14).toFixed(1)),
    floatM: Math.round(randBetween(rng, 3, 40)),
    borrowFeePct: Math.round(borrowFeePct),
    pumpScore: Number(pumpScore.toFixed(2)),
    dilutionScore: Number(dilutionScore.toFixed(2)),
    borrowScore: Number(borrowScore.toFixed(2)),
    compositeScore: composite,
    locate,
  };
}

let logCounter = 0;
export function makeLogEvent(ts: number, kind: LogKind, message: string, pnl?: number): LogEvent {
  return { id: `l-${ts}-${logCounter++}`, ts, kind, message, pnl };
}

export const LOG_KINDS: LogKind[] = [
  "DATA", "SIGNAL", "GUARD", "LOCATE", "ORDER", "FILL", "EXIT", "RISK", "HALT",
];

// Build a small plausible random log line for the tick engine.
export function randomLogLine(seed: number, ts: number): LogEvent {
  const rng = makeRng(seed);
  const sym = pick(rng, SYMBOLS);
  const templates: Array<[LogKind, string]> = [
    ["DATA", `Polygon: ${sym} printed +${Math.round(randBetween(rng, 20, 120))}% on ${randBetween(rng, 3, 13).toFixed(0)}x RVOL`],
    ["SIGNAL", `${sym} pump-fade score ${randBetween(rng, 0.6, 0.95).toFixed(2)} -> candidate`],
    ["LOCATE", `${sym} ${Math.round(randBetween(rng, 4, 14))}k reserved @ $${randBetween(rng, 0.01, 0.05).toFixed(2)}/sh`],
    ["GUARD", `${sym} RVOL ${randBetween(rng, 8, 13).toFixed(0)}x - size capped`],
  ];
  const [kind, message] = pick(rng, templates);
  return makeLogEvent(ts, kind, message);
}
```

- [ ] **Step 4: Implement `seed.ts`**

```ts
import type { AppState, Position } from "./types";
import { shortUnrealized, shortPctFromEntry } from "./pnl";
import { evaluateGuard, defaultSqueeze } from "./guard";
import { defaultUniverse, defaultBreakers } from "./config-defaults";
import { makeCandidate, makeLogEvent, symbolPool } from "./generators";

interface SeedPos {
  symbol: string; shortQty: number; avgPrice: number; last: number;
  priorClose: number; stopPrice: number; borrowFeePct: number; rvol: number; floatM: number;
}

const SEED_POSITIONS: SeedPos[] = [
  { symbol: "TICK", shortQty: 8000, avgPrice: 4.21, last: 4.12, priorClose: 3.4, stopPrice: 4.55, borrowFeePct: 84, rvol: 6, floatM: 22 },
  { symbol: "BBLG", shortQty: 12000, avgPrice: 1.98, last: 2.07, priorClose: 1.5, stopPrice: 2.18, borrowFeePct: 212, rvol: 11, floatM: 9 },
  { symbol: "CABL", shortQty: 5000, avgPrice: 7.4, last: 7.34, priorClose: 6.9, stopPrice: 7.85, borrowFeePct: 41, rvol: 4, floatM: 30 },
  { symbol: "VRAX", shortQty: 3200, avgPrice: 11.1, last: 10.62, priorClose: 9.8, stopPrice: 11.9, borrowFeePct: 67, rvol: 12, floatM: 14 },
];

function buildPosition(p: SeedPos, squeeze = defaultSqueeze): Position {
  const intradayGainPct = ((p.last - p.priorClose) / p.priorClose) * 100;
  const adverse = Math.max(0, ((p.last - p.avgPrice) / p.avgPrice) * 100);
  return {
    id: `p-${p.symbol}`,
    symbol: p.symbol,
    shortQty: p.shortQty,
    avgPrice: p.avgPrice,
    last: p.last,
    priorClose: p.priorClose,
    pctFromEntry: Number(shortPctFromEntry(p.avgPrice, p.last).toFixed(2)),
    unrealizedPnl: Math.round(shortUnrealized(p.avgPrice, p.last, p.shortQty)),
    stopPrice: p.stopPrice,
    borrowFeePct: p.borrowFeePct,
    rvol: p.rvol,
    floatM: p.floatM,
    guardState: evaluateGuard(
      { intradayGainPct, rvol: p.rvol, borrowFeePct: p.borrowFeePct, floatM: p.floatM, adverseMovePct: adverse },
      squeeze
    ),
  };
}

export function makeSeedState(seed: number): AppState {
  const positions = SEED_POSITIONS.map((p) => buildPosition(p));
  const candidates = symbolPool()
    .slice(0, 5)
    .map((s, i) => makeCandidate(seed + i + 1, s))
    .sort((a, b) => b.compositeScore - a.compositeScore);

  const t0 = Date.UTC(2026, 5, 12, 13, 42, 15);
  const log = [
    makeLogEvent(t0, "DATA", "Polygon: VRAX printed +112% on 11x RVOL"),
    makeLogEvent(t0 - 1340, "GUARD", "VRAX crossed force-exit (>100% & accelerating)"),
    makeLogEvent(t0 - 3210, "EXIT", "VRAX buy-to-cover 3,200 @ 10.58", 1664),
    makeLogEvent(t0 - 19000, "SIGNAL", "BBLG pump-fade score 0.81 -> candidate"),
    makeLogEvent(t0 - 35000, "LOCATE", "BBLG 12k reserved @ $0.04/sh (TradeZero)"),
    makeLogEvent(t0 - 68000, "ORDER", "SHORT VRAX 3,200 @ 11.10 - stop 11.90 attached"),
    makeLogEvent(t0 - 202000, "FILL", "SHORT TICK 8,000 @ 4.21"),
    makeLogEvent(t0 - 762000, "RISK", "Session armed - daily DD limit -4.0% - max 6 positions"),
  ];

  const realizedPnl = 1664;
  const unrealized = positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const dayPnl = realizedPnl + unrealized;
  const grossShort = positions.reduce((s, p) => s + p.shortQty * p.last, 0);
  const startEquity = 128400 - dayPnl;

  return {
    positions,
    orders: [
      { id: "o-DROP", symbol: "DROP", side: "SHORT", type: "LMT", qty: 6000, price: 5.2, filledQty: 0, ageSec: 4, status: "working" },
      { id: "o-BBLG", symbol: "BBLG", side: "SHORT", type: "LMT", qty: 12000, price: 1.98, filledQty: 7400, ageSec: 11, status: "partial" },
      { id: "o-TICK", symbol: "TICK", side: "BUY", type: "STP", qty: 8000, price: 4.55, filledQty: 0, ageSec: 660, status: "stop-resting" },
      { id: "o-GNSX", symbol: "GNSX", side: "LOCATE", type: "REQ", qty: 10000, price: null, filledQty: 0, ageSec: 2, status: "pending-locate" },
    ],
    candidates,
    log,
    account: {
      startEquity,
      equity: 128400,
      dayPnl,
      realizedPnl,
      grossShort: Math.round(grossShort),
      grossLimit: 150000,
      drawdownPct: 0,
      positionsCount: positions.length,
      halted: false,
    },
    config: { universe: defaultUniverse, squeeze: defaultSqueeze, breakers: defaultBreakers },
    eventsPerMin: 14,
  };
}
```

- [ ] **Step 5: Create `config-defaults.ts`** (referenced above)

`ui/src/mockData/config-defaults.ts`:
```ts
import type { UniverseParams, CircuitBreakers } from "./types";

export const defaultUniverse: UniverseParams = {
  capMinM: 10, capMaxM: 500, priceFloor: 1, priceCeiling: 25,
  minDollarVolM: 3, minAdvK: 500, lowFloatFlagM: 20,
  maxBorrowFeeSoftPct: 100, maxBorrowFeeHardPct: 300,
};

export const defaultBreakers: CircuitBreakers = {
  perPositionMaxLossPct: 18, dailyDrawdownLimitPct: -4, maxPositions: 6, maxGrossShort: 150000,
};
```

- [ ] **Step 6: Run test to verify it passes**

Run: `npm run test -- seed`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add ui/src/mockData/seed.ts ui/src/mockData/generators.ts ui/src/mockData/config-defaults.ts ui/src/mockData/__tests__/seed.test.ts
git commit -m "feat(ui): deterministic seed state + generators"
```

---

## Task 8: Store + reducer actions

**Files:**
- Create: `ui/src/mockData/store.tsx`, `ui/src/mockData/__tests__/store.test.tsx`

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/store.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { reducer, initialState } from "../store";

describe("store reducer", () => {
  it("KILL halts trading, flattens positions and clears working orders", () => {
    const s = reducer(initialState(), { type: "KILL" });
    expect(s.account.halted).toBe(true);
    expect(s.positions).toHaveLength(0);
    expect(s.orders.every((o) => o.status === "stop-resting" || o.status === "filled")).toBe(true);
    expect(s.log[0].kind).toBe("HALT");
  });

  it("RESUME clears the halt flag", () => {
    const killed = reducer(initialState(), { type: "KILL" });
    expect(reducer(killed, { type: "RESUME" }).account.halted).toBe(false);
  });

  it("CANCEL_ORDER removes a working order", () => {
    const s0 = initialState();
    const id = s0.orders.find((o) => o.status === "working")!.id;
    const s = reducer(s0, { type: "CANCEL_ORDER", id });
    expect(s.orders.find((o) => o.id === id)).toBeUndefined();
  });

  it("COVER_POSITION closes one position and books realized P&L", () => {
    const s0 = initialState();
    const sym = s0.positions[0].symbol;
    const before = s0.account.realizedPnl;
    const s = reducer(s0, { type: "COVER_POSITION", symbol: sym });
    expect(s.positions.find((p) => p.symbol === sym)).toBeUndefined();
    expect(s.account.realizedPnl).not.toBe(before);
  });

  it("UPDATE_CONFIG patches squeeze thresholds and re-evaluates guards", () => {
    const s = reducer(initialState(), {
      type: "UPDATE_CONFIG",
      patch: { squeeze: { gainAbortPct: 1 } },
    });
    expect(s.config.squeeze.gainAbortPct).toBe(1);
    // every position is up vs prior close, so all flip to exit
    expect(s.positions.every((p) => p.guardState === "exit")).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- store`
Expected: FAIL — cannot find module `../store`.

- [ ] **Step 3: Implement `store.tsx`**

```tsx
import React, { createContext, useContext, useReducer } from "react";
import type { AppState, Config, Position } from "./types";
import { makeSeedState } from "./seed";
import { evaluateGuard } from "./guard";
import { adverseMovePct } from "./pnl";
import { makeLogEvent } from "./generators";

export function initialState(): AppState {
  return makeSeedState(1);
}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export type Action =
  | { type: "TICK"; next: AppState }
  | { type: "KILL" }
  | { type: "RESUME" }
  | { type: "CANCEL_ORDER"; id: string }
  | { type: "COVER_POSITION"; symbol: string }
  | { type: "UPDATE_CONFIG"; patch: DeepPartial<Config> };

const CAP = 200;

export function reEvaluateGuards(state: AppState): AppState {
  const positions = state.positions.map((p): Position => {
    const intradayGainPct = ((p.last - p.priorClose) / p.priorClose) * 100;
    return {
      ...p,
      guardState: evaluateGuard(
        {
          intradayGainPct,
          rvol: p.rvol,
          borrowFeePct: p.borrowFeePct,
          floatM: p.floatM,
          adverseMovePct: adverseMovePct(p.avgPrice, p.last),
        },
        state.config.squeeze
      ),
    };
  });
  return { ...state, positions };
}

function mergeConfig(cfg: Config, patch: DeepPartial<Config>): Config {
  return {
    universe: { ...cfg.universe, ...(patch.universe ?? {}) },
    squeeze: { ...cfg.squeeze, ...(patch.squeeze ?? {}) },
    breakers: { ...cfg.breakers, ...(patch.breakers ?? {}) },
  };
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "TICK":
      return action.next;

    case "KILL": {
      const ts = Date.now();
      const exits = state.positions.map((p) =>
        makeLogEvent(ts, "EXIT", `KILL flatten ${p.symbol} ${p.shortQty} @ ${p.last.toFixed(2)}`, p.unrealizedPnl)
      );
      const halt = makeLogEvent(ts, "HALT", "KILL SWITCH — all positions flattened, new orders halted");
      const realized = state.account.realizedPnl + state.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
      return {
        ...state,
        positions: [],
        orders: state.orders.filter((o) => o.status === "stop-resting" || o.status === "filled"),
        account: { ...state.account, halted: true, realizedPnl: realized, positionsCount: 0, grossShort: 0 },
        log: [halt, ...exits, ...state.log].slice(0, CAP),
      };
    }

    case "RESUME":
      return {
        ...state,
        account: { ...state.account, halted: false },
        log: [makeLogEvent(Date.now(), "RISK", "Trading resumed by operator"), ...state.log].slice(0, CAP),
      };

    case "CANCEL_ORDER":
      return { ...state, orders: state.orders.filter((o) => o.id !== action.id) };

    case "COVER_POSITION": {
      const pos = state.positions.find((p) => p.symbol === action.symbol);
      if (!pos) return state;
      const ts = Date.now();
      return {
        ...state,
        positions: state.positions.filter((p) => p.symbol !== action.symbol),
        account: {
          ...state.account,
          realizedPnl: state.account.realizedPnl + pos.unrealizedPnl,
          positionsCount: state.account.positionsCount - 1,
          grossShort: Math.max(0, state.account.grossShort - pos.shortQty * pos.last),
        },
        log: [makeLogEvent(ts, "EXIT", `Cover ${pos.symbol} ${pos.shortQty} @ ${pos.last.toFixed(2)}`, pos.unrealizedPnl), ...state.log].slice(0, CAP),
      };
    }

    case "UPDATE_CONFIG":
      return reEvaluateGuards({ ...state, config: mergeConfig(state.config, action.patch) });

    default:
      return state;
  }
}

interface StoreCtx {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}
const Ctx = createContext<StoreCtx | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  return <Ctx.Provider value={{ state, dispatch }}>{children}</Ctx.Provider>;
}

export function useStore(): StoreCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore must be used within StoreProvider");
  return ctx;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- store`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/mockData/store.tsx ui/src/mockData/__tests__/store.test.tsx
git commit -m "feat(ui): store reducer + actions (kill, cover, cancel, config)"
```

---

## Task 9: Tick engine hook

**Files:**
- Create: `ui/src/mockData/useTickEngine.ts`, `ui/src/mockData/tick.ts`, `ui/src/mockData/__tests__/tick.test.ts`

This splits the pure step (`tick.ts`, tested) from the React interval wrapper (`useTickEngine.ts`).

- [ ] **Step 1: Write the failing test**

`ui/src/mockData/__tests__/tick.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { tickStep } from "../tick";
import { initialState } from "../store";

describe("tickStep", () => {
  it("does not mutate positions when halted", () => {
    const halted = { ...initialState(), account: { ...initialState().account, halted: true } };
    const out = tickStep(halted, 12345);
    expect(out.positions).toHaveLength(halted.positions.length);
  });

  it("moves prices and recomputes unrealized P&L", () => {
    const s0 = initialState();
    const out = tickStep(s0, 999);
    const p = out.positions[0];
    expect(p.unrealizedPnl).toBeCloseTo((p.avgPrice - p.last) * p.shortQty, 0);
  });

  it("keeps the log capped and prepends newest", () => {
    let s = initialState();
    for (let i = 0; i < 250; i++) s = tickStep(s, i);
    expect(s.log.length).toBeLessThanOrEqual(200);
  });

  it("recomputes day P&L as realized + unrealized", () => {
    const out = tickStep(initialState(), 5);
    const unreal = out.positions.reduce((a, p) => a + p.unrealizedPnl, 0);
    expect(out.account.dayPnl).toBeCloseTo(out.account.realizedPnl + unreal, 0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- tick`
Expected: FAIL — cannot find module `../tick`.

- [ ] **Step 3: Implement `tick.ts`**

```ts
import type { AppState, Position, Candidate } from "./types";
import { makeRng } from "./rng";
import { shortUnrealized, shortPctFromEntry, adverseMovePct } from "./pnl";
import { evaluateGuard } from "./guard";
import { advanceOrder } from "./orders";
import { randomLogLine } from "./generators";

const CAP = 200;
const DT = 1;

function drift(rng: () => number, price: number, vol: number): number {
  const pct = (rng() - 0.5) * vol;
  return Math.max(0.5, Number((price * (1 + pct)).toFixed(2)));
}

// One pure tick. `tickSeed` makes it deterministic in tests.
export function tickStep(state: AppState, tickSeed: number): AppState {
  if (state.account.halted) return state;
  const rng = makeRng(tickSeed);
  const now = Date.now();

  const positions: Position[] = state.positions.map((p) => {
    const last = drift(rng, p.last, 0.04);
    const intradayGainPct = ((last - p.priorClose) / p.priorClose) * 100;
    return {
      ...p,
      last,
      pctFromEntry: Number(shortPctFromEntry(p.avgPrice, last).toFixed(2)),
      unrealizedPnl: Math.round(shortUnrealized(p.avgPrice, last, p.shortQty)),
      guardState: evaluateGuard(
        { intradayGainPct, rvol: p.rvol, borrowFeePct: p.borrowFeePct, floatM: p.floatM, adverseMovePct: adverseMovePct(p.avgPrice, last) },
        state.config.squeeze
      ),
    };
  });

  const candidates: Candidate[] = state.candidates
    .map((c) => {
      const last = drift(rng, c.last, 0.05);
      return { ...c, last, pctChange: Math.round(c.pctChange + (rng() - 0.5) * 6) };
    })
    .sort((a, b) => b.compositeScore - a.compositeScore);

  const orders = state.orders
    .map((o) => advanceOrder(o, DT, rng()))
    .filter((o) => o.status !== "filled" || o.type === "STP");

  const realizedPnl = state.account.realizedPnl;
  const unrealized = positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const dayPnl = realizedPnl + unrealized;
  const grossShort = Math.round(positions.reduce((s, p) => s + p.shortQty * p.last, 0));
  const equity = state.account.startEquity + dayPnl;
  const drawdownPct = Number(Math.min(0, (dayPnl / state.account.startEquity) * 100).toFixed(2));

  const log =
    rng() < 0.5
      ? [randomLogLine(tickSeed + 1, now), ...state.log].slice(0, CAP)
      : state.log.slice(0, CAP);

  return {
    ...state,
    positions,
    candidates,
    orders,
    account: { ...state.account, dayPnl, equity, grossShort, drawdownPct, positionsCount: positions.length },
    log,
  };
}
```

- [ ] **Step 4: Implement `useTickEngine.ts`**

```ts
import { useEffect, useRef } from "react";
import { tickStep } from "./tick";
import { useStore } from "./store";

// Drives the store ~once per second. Pauses automatically when halted.
export function useTickEngine(intervalMs = 1000) {
  const { state, dispatch } = useStore();
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const id = setInterval(() => {
      const cur = stateRef.current;
      if (cur.account.halted) return;
      dispatch({ type: "TICK", next: tickStep(cur, Date.now() & 0x7fffffff) });
    }, intervalMs);
    return () => clearInterval(id);
  }, [dispatch, intervalMs]);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm run test -- tick`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add ui/src/mockData/tick.ts ui/src/mockData/useTickEngine.ts ui/src/mockData/__tests__/tick.test.ts
git commit -m "feat(ui): tick engine (pure step + interval hook)"
```

---

## Task 10: Shared primitives

**Files:**
- Create: `ui/src/components/Panel.tsx`, `Pill.tsx`, `StatRow.tsx`, `ProgressBar.tsx`, `DataTable.tsx`, `Sparkline.tsx`, and `ui/src/components/__tests__/primitives.test.tsx`

- [ ] **Step 1: Implement `Panel.tsx`**

```tsx
import type { ReactNode } from "react";

export function Panel({
  label, right, children, accent = "muted", className = "",
}: {
  label: string;
  right?: ReactNode;
  children: ReactNode;
  accent?: "muted" | "warn" | "info";
  className?: string;
}) {
  const labelColor = accent === "warn" ? "text-warn" : accent === "info" ? "text-info2" : "text-muted";
  const border = accent === "warn" ? "border-[#2a1f12]" : "border-edge";
  return (
    <div className={`bg-panel border ${border} rounded-lg ${className}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-edge">
        <span className={`text-[9px] tracking-[1px] ${labelColor}`}>{label}</span>
        {right}
      </div>
      <div>{children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Implement `Pill.tsx`**

```tsx
import type { LogKind } from "../mockData/types";

const KIND_STYLE: Record<LogKind, string> = {
  DATA: "bg-[#0e2a33] text-accent",
  SIGNAL: "bg-[#101f2e] text-info",
  GUARD: "bg-[#2a2110] text-warn",
  LOCATE: "bg-[#1e1530] text-violet",
  ORDER: "bg-[#0f1b2a] text-info2",
  FILL: "bg-[#0c2417] text-up",
  EXIT: "bg-[#2a1414] text-down",
  RISK: "bg-[#2a1414] text-down",
  HALT: "bg-down text-white",
};

export function Pill({ kind }: { kind: LogKind }) {
  return (
    <span className={`px-[5px] rounded-[3px] ${KIND_STYLE[kind]}`}>{kind}</span>
  );
}
```

- [ ] **Step 3: Implement `StatRow.tsx`**

```tsx
import type { ReactNode } from "react";

export function StatRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between text-muted">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
```

- [ ] **Step 4: Implement `ProgressBar.tsx`**

```tsx
// fraction 0..1; color shifts up -> warn -> down as it approaches 1.
export function ProgressBar({ fraction }: { fraction: number }) {
  const f = Math.max(0, Math.min(1, fraction));
  const color = f >= 0.85 ? "bg-down" : f >= 0.6 ? "bg-warn" : "bg-up";
  return (
    <div className="h-[5px] bg-edge rounded-[3px]">
      <div className={`h-full rounded-[3px] ${color}`} style={{ width: `${f * 100}%` }} />
    </div>
  );
}
```

- [ ] **Step 5: Implement `Sparkline.tsx`**

```tsx
export function Sparkline({ values, height = 22 }: { values: number[]; height?: number }) {
  const max = Math.max(...values.map((v) => Math.abs(v)), 1);
  return (
    <div className="flex items-end gap-[2px]" style={{ height }}>
      {values.map((v, i) => (
        <div
          key={i}
          className={v >= 0 ? "bg-up/40" : "bg-down/40"}
          style={{ flex: 1, height: `${(Math.abs(v) / max) * 100}%` }}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Implement `DataTable.tsx`**

```tsx
import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
}

export function DataTable<T>({
  columns, rows, getKey, onRowClick,
}: {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string;
  onRowClick?: (row: T) => void;
}) {
  return (
    <table className="w-full border-collapse font-mono text-[9.5px]">
      <thead>
        <tr className="text-muted2">
          {columns.map((c) => (
            <th
              key={c.key}
              className={`font-medium px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"}`}
            >
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={getKey(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={`border-t border-rowdiv ${onRowClick ? "cursor-pointer hover:bg-[#0c1320]" : ""}`}
          >
            {columns.map((c) => (
              <td key={c.key} className={`px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 7: Write a render smoke test**

`ui/src/components/__tests__/primitives.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Panel } from "../Panel";
import { Pill } from "../Pill";
import { ProgressBar } from "../ProgressBar";
import { DataTable } from "../DataTable";

describe("primitives", () => {
  it("Panel renders label and children", () => {
    render(<Panel label="OPEN POSITIONS"><div>body</div></Panel>);
    expect(screen.getByText("OPEN POSITIONS")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("Pill renders the kind text", () => {
    render(<Pill kind="GUARD" />);
    expect(screen.getByText("GUARD")).toBeInTheDocument();
  });

  it("ProgressBar clamps without throwing", () => {
    expect(() => render(<ProgressBar fraction={2} />)).not.toThrow();
  });

  it("DataTable renders rows", () => {
    render(
      <DataTable
        columns={[{ key: "s", header: "SYM", render: (r: { s: string }) => r.s }]}
        rows={[{ s: "TICK" }]}
        getKey={(r) => r.s}
      />
    );
    expect(screen.getByText("TICK")).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run tests**

Run: `npm run test -- primitives`
Expected: PASS (4 tests).

- [ ] **Step 9: Commit**

```bash
git add ui/src/components/Panel.tsx ui/src/components/Pill.tsx ui/src/components/StatRow.tsx ui/src/components/ProgressBar.tsx ui/src/components/Sparkline.tsx ui/src/components/DataTable.tsx ui/src/components/__tests__/primitives.test.tsx
git commit -m "feat(ui): shared presentational primitives"
```

---

## Task 11: TopBar + KillSwitch

**Files:**
- Create: `ui/src/components/TopBar.tsx`, `ui/src/components/KillSwitch.tsx`, `ui/src/components/__tests__/killswitch.test.tsx`

- [ ] **Step 1: Implement `KillSwitch.tsx`**

```tsx
import { useState } from "react";
import { useStore } from "../mockData/store";

export function KillSwitch() {
  const { state, dispatch } = useStore();
  const [confirming, setConfirming] = useState(false);

  if (state.account.halted) {
    return (
      <button
        onClick={() => dispatch({ type: "RESUME" })}
        className="bg-up text-black font-extrabold tracking-[0.5px] rounded-md px-3 py-[5px]"
      >
        RESUME
      </button>
    );
  }

  return (
    <>
      <button
        onClick={() => setConfirming(true)}
        className="bg-down text-white font-extrabold tracking-[0.5px] rounded-md px-3 py-[5px]"
      >
        KILL&nbsp;SWITCH
      </button>
      {confirming && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-panel border border-down rounded-lg p-5 w-[340px]">
            <div className="text-strong font-bold mb-1">Flatten everything?</div>
            <div className="text-muted text-[12px] mb-4">
              Closes all positions, cancels working orders, and halts new orders. Mock state only.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirming(false)} className="px-3 py-[5px] rounded-md border border-edge text-body">
                Cancel
              </button>
              <button
                onClick={() => { dispatch({ type: "KILL" }); setConfirming(false); }}
                className="px-3 py-[5px] rounded-md bg-down text-white font-bold"
              >
                Confirm flatten
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 2: Implement `TopBar.tsx`**

```tsx
import { useStore } from "../mockData/store";
import { KillSwitch } from "./KillSwitch";

const TABS = ["Cockpit", "Config", "Backtest"] as const;
export type TabName = (typeof TABS)[number];

export function TopBar({ tab, onTab }: { tab: TabName; onTab: (t: TabName) => void }) {
  const { state } = useStore();
  const a = state.account;
  const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

  return (
    <div className="flex items-center gap-[18px] px-[14px] py-[9px] bg-bar border-b border-edge">
      <span className="font-extrabold tracking-[0.5px] text-strong">
        ⚡ LOWCAP<span className="text-accent">SHORT</span>
      </span>
      {TABS.map((t) => (
        <button
          key={t}
          onClick={() => onTab(t)}
          className={t === tab ? "text-accent border-b-2 border-accent pb-[7px] -mb-[9px]" : "text-muted"}
        >
          {t}
        </button>
      ))}
      <div className="ml-auto flex items-center gap-4 font-mono">
        <span className="text-muted">EQUITY <span className="text-strong">${Math.round(a.equity).toLocaleString()}</span></span>
        <span className="text-muted">DAY <span className={`font-bold ${a.dayPnl >= 0 ? "text-up" : "text-down"}`}>{money(a.dayPnl)}</span></span>
        <span className="text-muted">GROSS <span className="text-strong">${Math.round(a.grossShort / 1000)}k</span>/{Math.round(a.grossLimit / 1000)}k</span>
        <KillSwitch />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write the kill-switch test**

`ui/src/components/__tests__/killswitch.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../mockData/store";
import { KillSwitch } from "../KillSwitch";

describe("KillSwitch", () => {
  it("confirms then flattens, showing RESUME", () => {
    render(<StoreProvider><KillSwitch /></StoreProvider>);
    fireEvent.click(screen.getByText("KILL SWITCH"));
    fireEvent.click(screen.getByText("Confirm flatten"));
    expect(screen.getByText("RESUME")).toBeInTheDocument();
  });

  it("cancel dismisses the modal without halting", () => {
    render(<StoreProvider><KillSwitch /></StoreProvider>);
    fireEvent.click(screen.getByText("KILL SWITCH"));
    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.getByText("KILL SWITCH")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run tests**

Run: `npm run test -- killswitch`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/src/components/TopBar.tsx ui/src/components/KillSwitch.tsx ui/src/components/__tests__/killswitch.test.tsx
git commit -m "feat(ui): top bar + kill switch with confirm/resume"
```

---

## Task 12: Cockpit — Positions + Active Orders

**Files:**
- Create: `ui/src/tabs/cockpit/Positions.tsx`, `ui/src/tabs/cockpit/ActiveOrders.tsx`

- [ ] **Step 1: Implement `Positions.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { useStore } from "../../mockData/store";
import type { Position } from "../../mockData/types";

const guardColor = (g: Position["guardState"]) =>
  g === "ok" ? "text-up" : g === "caution" ? "text-warn" : "text-down";
const guardLabel = (g: Position["guardState"]) => (g === "exit" ? "EXIT" : g);
const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

export function Positions() {
  const { state, dispatch } = useStore();
  const cols: Column<Position>[] = [
    { key: "sym", header: "SYM", render: (p) => <span className="text-strong">{p.symbol}</span> },
    { key: "qty", header: "SHORT", align: "right", render: (p) => p.shortQty.toLocaleString() },
    { key: "avg", header: "AVG", align: "right", render: (p) => p.avgPrice.toFixed(2) },
    { key: "last", header: "LAST", align: "right", render: (p) => p.last.toFixed(2) },
    { key: "pct", header: "%", align: "right", render: (p) => <span className={p.pctFromEntry >= 0 ? "text-up" : "text-down"}>{p.pctFromEntry >= 0 ? "+" : ""}{p.pctFromEntry.toFixed(1)}%</span> },
    { key: "upnl", header: "uP&L", align: "right", render: (p) => <span className={p.unrealizedPnl >= 0 ? "text-up" : "text-down"}>{money(p.unrealizedPnl)}</span> },
    { key: "stop", header: "STOP", align: "right", render: (p) => p.stopPrice.toFixed(2) },
    { key: "fee", header: "FEE", align: "right", render: (p) => `${p.borrowFeePct}%` },
    { key: "guard", header: "GUARD", align: "right", render: (p) => <span className={guardColor(p.guardState)}>{guardLabel(p.guardState)}</span> },
  ];
  return (
    <Panel label={`OPEN POSITIONS · ${state.positions.length}`}>
      <DataTable columns={cols} rows={state.positions} getKey={(p) => p.id}
        onRowClick={(p) => dispatch({ type: "COVER_POSITION", symbol: p.symbol })} />
    </Panel>
  );
}
```

- [ ] **Step 2: Implement `ActiveOrders.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { useStore } from "../../mockData/store";
import type { Order, OrderStatus } from "../../mockData/types";

const STATUS: Record<OrderStatus, { dot: string; label: string; cls: string }> = {
  working: { dot: "●", label: "working", cls: "text-info" },
  partial: { dot: "◐", label: "partial", cls: "text-warn" },
  "stop-resting": { dot: "◇", label: "stop resting", cls: "text-muted" },
  "pending-locate": { dot: "⧗", label: "pending locate", cls: "text-violet" },
  filled: { dot: "✓", label: "filled", cls: "text-up" },
  rejected: { dot: "✕", label: "rejected", cls: "text-down" },
};
const sideColor = (s: Order["side"]) => (s === "SHORT" ? "text-down" : s === "BUY" ? "text-up" : "text-violet");

export function ActiveOrders() {
  const { state, dispatch } = useStore();
  const working = state.orders.length;
  const cols: Column<Order>[] = [
    { key: "sym", header: "SYM", render: (o) => <span className="text-strong">{o.symbol}</span> },
    { key: "side", header: "SIDE", align: "right", render: (o) => <span className={sideColor(o.side)}>{o.side}</span> },
    { key: "type", header: "TYPE", align: "right", render: (o) => o.type },
    { key: "qty", header: "QTY", align: "right", render: (o) => o.qty.toLocaleString() },
    { key: "price", header: "PRICE", align: "right", render: (o) => (o.price == null ? "—" : o.price.toFixed(2)) },
    { key: "filled", header: "FILLED", align: "right", render: (o) => (o.status === "stop-resting" ? "—" : `${o.filledQty.toLocaleString()}/${o.qty.toLocaleString()}`) },
    { key: "age", header: "AGE", align: "right", render: (o) => (o.ageSec >= 60 ? `${Math.floor(o.ageSec / 60)}m` : `${o.ageSec}s`) },
    { key: "status", header: "STATUS", align: "right", render: (o) => <span className={STATUS[o.status].cls}>{STATUS[o.status].dot} {STATUS[o.status].label}</span> },
  ];
  return (
    <Panel label={`ACTIVE ORDERS · ${working} working`} accent="info"
      right={<span className="text-[9px] text-muted2">Reg SHO: no short w/o locate</span>}>
      <DataTable columns={cols} rows={state.orders} getKey={(o) => o.id}
        onRowClick={(o) => { if (o.status === "working") dispatch({ type: "CANCEL_ORDER", id: o.id }); }} />
    </Panel>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc -b`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add ui/src/tabs/cockpit/Positions.tsx ui/src/tabs/cockpit/ActiveOrders.tsx
git commit -m "feat(ui): cockpit positions + active orders panels"
```

---

## Task 13: Cockpit — Scanner + Right Rail

**Files:**
- Create: `ui/src/tabs/cockpit/Scanner.tsx`, `ui/src/tabs/cockpit/RightRail.tsx`

- [ ] **Step 1: Implement `Scanner.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { useStore } from "../../mockData/store";
import type { Candidate } from "../../mockData/types";

export function Scanner() {
  const { state } = useStore();
  const top = state.candidates[0]?.id;
  const cols: Column<Candidate>[] = [
    { key: "sym", header: "SYM", render: (c) => <span className={c.id === top ? "text-accent" : "text-strong"}>{c.symbol}</span> },
    { key: "last", header: "LAST", align: "right", render: (c) => c.last.toFixed(2) },
    { key: "chg", header: "%CHG", align: "right", render: (c) => <span className="text-up">+{c.pctChange}%</span> },
    { key: "rvol", header: "RVOL", align: "right", render: (c) => `${c.rvol}×` },
    { key: "fee", header: "FEE", align: "right", render: (c) => `${c.borrowFeePct}%` },
    { key: "pump", header: "PUMP", align: "right", render: (c) => c.pumpScore.toFixed(2) },
    { key: "dil", header: "DIL", align: "right", render: (c) => c.dilutionScore.toFixed(2) },
    { key: "score", header: "SCORE", align: "right", render: (c) => <span className={`font-bold ${c.compositeScore >= 0.8 ? "text-accent" : c.compositeScore < 0.6 ? "text-warn" : ""}`}>{c.compositeScore.toFixed(2)}</span> },
    { key: "locate", header: "LOCATE", align: "right", render: (c) => c.locate.ok ? <span className="text-up">✓ ${c.locate.costPerShare?.toFixed(2)}</span> : <span className="text-down">✕ {c.locate.reason}</span> },
  ];
  return (
    <Panel label="LIVE SCANNER · IN PLAY" right={<span className="text-[9px] text-accent">● streaming</span>}>
      <DataTable columns={cols} rows={state.candidates} getKey={(c) => c.id} />
    </Panel>
  );
}
```

- [ ] **Step 2: Implement `RightRail.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { StatRow } from "../../components/StatRow";
import { ProgressBar } from "../../components/ProgressBar";
import { Sparkline } from "../../components/Sparkline";
import { useStore } from "../../mockData/store";

const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

export function RightRail() {
  const { state } = useStore();
  const a = state.account;
  const alerts = state.positions.filter((p) => p.guardState !== "ok");
  const ddFraction = a.drawdownPct / a.config?.breakers?.dailyDrawdownLimitPct! || 0;

  return (
    <div className="flex flex-col gap-[10px]">
      <Panel label="DAY P&L">
        <div className="p-[10px]">
          <div className={`font-mono text-[22px] font-bold ${a.dayPnl >= 0 ? "text-up" : "text-down"}`}>{money(a.dayPnl)}</div>
          <Sparkline values={[3, 5, -2, 4, 7, a.dayPnl >= 0 ? 9 : -9]} />
        </div>
      </Panel>

      <Panel label="CIRCUIT BREAKERS">
        <div className="p-[10px] font-mono text-[9.5px] space-y-1">
          <StatRow label="Daily drawdown" value={<span className={a.drawdownPct <= state.config.breakers.dailyDrawdownLimitPct * 0.75 ? "text-warn" : "text-up"}>{a.drawdownPct.toFixed(1)}% / {state.config.breakers.dailyDrawdownLimitPct.toFixed(1)}%</span>} />
          <div className="py-1"><ProgressBar fraction={Math.abs(a.drawdownPct / state.config.breakers.dailyDrawdownLimitPct)} /></div>
          <StatRow label="Positions" value={<span className="text-strong">{a.positionsCount} / {state.config.breakers.maxPositions}</span>} />
          <StatRow label="Gross short" value={<span className="text-strong">${Math.round(a.grossShort / 1000)}k / ${Math.round(state.config.breakers.maxGrossShort / 1000)}k</span>} />
        </div>
      </Panel>

      <Panel label={`▲ SQUEEZE ALERTS · ${alerts.length}`} accent="warn">
        <div className="p-[10px] font-mono text-[9px] space-y-1">
          {alerts.length === 0 && <div className="text-muted">none</div>}
          {alerts.map((p) => (
            <div key={p.id} className="flex justify-between">
              <span className="text-strong">{p.symbol}</span>
              <span className={p.guardState === "exit" ? "text-down" : "text-warn"}>
                fee {p.borrowFeePct}% · {p.guardState === "exit" ? "EXIT" : "caution"}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel label="LOCATES RESERVED">
        <div className="p-[10px] font-mono text-[9px] text-muted space-y-1">
          {state.orders.filter((o) => o.side === "LOCATE").map((o) => (
            <div key={o.id} className="flex justify-between"><span className="text-strong">{o.symbol}</span><span>{Math.round(o.qty / 1000)}k · pending</span></div>
          ))}
          <div className="flex justify-between"><span className="text-strong">TICK</span><span>8k @ $0.03</span></div>
          <div className="flex justify-between"><span className="text-strong">PLTX</span><span>10k @ $0.02 · unused</span></div>
        </div>
      </Panel>
    </div>
  );
}
```

> Note: delete the unused `ddFraction` line if `noUnusedLocals` flags it; it is illustrative only. The breaker math uses `state.config.breakers` directly.

- [ ] **Step 3: Remove the illustrative dead line**

Delete this line from `RightRail.tsx` (it exists only to explain the ratio and will fail `noUnusedLocals`):
```tsx
  const ddFraction = a.drawdownPct / a.config?.breakers?.dailyDrawdownLimitPct! || 0;
```

- [ ] **Step 4: Type-check**

Run: `npx tsc -b`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add ui/src/tabs/cockpit/Scanner.tsx ui/src/tabs/cockpit/RightRail.tsx
git commit -m "feat(ui): cockpit scanner + right rail panels"
```

---

## Task 14: Cockpit — Live Log + assembly

**Files:**
- Create: `ui/src/tabs/cockpit/LiveLog.tsx`, `ui/src/tabs/cockpit/Cockpit.tsx`

- [ ] **Step 1: Implement `LiveLog.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { Pill } from "../../components/Pill";
import { useStore } from "../../mockData/store";

function hhmmssms(ts: number): string {
  const d = new Date(ts);
  const p = (n: number, l = 2) => String(n).padStart(l, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

export function LiveLog() {
  const { state } = useStore();
  return (
    <Panel label="LIVE LOG" right={<span className="text-[9px] text-accent">● {state.eventsPerMin} events / min</span>} className="mx-[10px] mb-[10px]">
      <div className="px-3 py-2 font-mono text-[9px] leading-[1.7] max-h-[180px] overflow-y-auto">
        {state.log.map((e) => (
          <div key={e.id}>
            <span className="text-muted2">{hhmmssms(e.ts)}</span> <Pill kind={e.kind} /> {e.message}
            {e.pnl != null && <span className={e.pnl >= 0 ? "text-up" : "text-down"}> · {e.pnl >= 0 ? "+" : "-"}${Math.abs(e.pnl).toLocaleString()} realized</span>}
          </div>
        ))}
      </div>
    </Panel>
  );
}
```

- [ ] **Step 2: Implement `Cockpit.tsx`**

```tsx
import { Positions } from "./Positions";
import { ActiveOrders } from "./ActiveOrders";
import { Scanner } from "./Scanner";
import { RightRail } from "./RightRail";
import { LiveLog } from "./LiveLog";
import { useStore } from "../../mockData/store";

export function Cockpit() {
  const { state } = useStore();
  return (
    <div>
      {state.account.halted && (
        <div className="bg-down/20 border border-down text-down font-bold text-center py-2">
          TRADING HALTED — kill switch engaged. Press RESUME to re-arm.
        </div>
      )}
      <div className="grid grid-cols-[2fr_1fr] gap-[10px] p-[10px]">
        <div className="flex flex-col gap-[10px]">
          <Positions />
          <ActiveOrders />
          <Scanner />
        </div>
        <RightRail />
      </div>
      <LiveLog />
    </div>
  );
}
```

- [ ] **Step 3: Write a cockpit render test**

`ui/src/tabs/cockpit/__tests__/cockpit.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StoreProvider } from "../../../mockData/store";
import { Cockpit } from "../Cockpit";

describe("Cockpit", () => {
  it("renders the major panels with seed data", () => {
    render(<StoreProvider><Cockpit /></StoreProvider>);
    expect(screen.getByText(/OPEN POSITIONS/)).toBeInTheDocument();
    expect(screen.getByText(/ACTIVE ORDERS/)).toBeInTheDocument();
    expect(screen.getByText(/LIVE SCANNER/)).toBeInTheDocument();
    expect(screen.getByText("LIVE LOG")).toBeInTheDocument();
    expect(screen.getByText("TICK")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run test**

Run: `npm run test -- cockpit`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add ui/src/tabs/cockpit/LiveLog.tsx ui/src/tabs/cockpit/Cockpit.tsx ui/src/tabs/cockpit/__tests__/cockpit.test.tsx
git commit -m "feat(ui): live log + cockpit assembly"
```

---

## Task 15: Config tab

**Files:**
- Create: `ui/src/tabs/config/Config.tsx`

- [ ] **Step 1: Implement `Config.tsx`**

```tsx
import { Panel } from "../../components/Panel";
import { useStore } from "../../mockData/store";
import { defaultUniverse, defaultBreakers } from "../../mockData/config-defaults";
import { defaultSqueeze } from "../../mockData/guard";

function NumField({ label, value, hint, onChange }: { label: string; value: number; hint?: string; onChange: (n: number) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 py-[5px]">
      <span className="text-muted" title={hint}>{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 bg-bg border border-edge rounded px-2 py-1 font-mono text-right text-strong focus:border-accent outline-none"
      />
    </label>
  );
}

export function Config() {
  const { state, dispatch } = useStore();
  const { universe, squeeze, breakers } = state.config;
  const u = (patch: Partial<typeof universe>) => dispatch({ type: "UPDATE_CONFIG", patch: { universe: patch } });
  const s = (patch: Partial<typeof squeeze>) => dispatch({ type: "UPDATE_CONFIG", patch: { squeeze: patch } });
  const b = (patch: Partial<typeof breakers>) => dispatch({ type: "UPDATE_CONFIG", patch: { breakers: patch } });

  const reset = () =>
    dispatch({ type: "UPDATE_CONFIG", patch: { universe: defaultUniverse, squeeze: defaultSqueeze, breakers: defaultBreakers } });

  return (
    <div className="p-[10px] grid grid-cols-3 gap-[10px] items-start">
      <Panel label="UNIVERSE (§8)">
        <div className="p-3 text-[11px]">
          <NumField label="Market cap min ($M)" value={universe.capMinM} onChange={(n) => u({ capMinM: n })} />
          <NumField label="Market cap max ($M)" value={universe.capMaxM} onChange={(n) => u({ capMaxM: n })} />
          <NumField label="Price floor" value={universe.priceFloor} onChange={(n) => u({ priceFloor: n })} />
          <NumField label="Price ceiling" value={universe.priceCeiling} onChange={(n) => u({ priceCeiling: n })} />
          <NumField label="Min $ vol (20d, $M)" value={universe.minDollarVolM} onChange={(n) => u({ minDollarVolM: n })} />
          <NumField label="Min ADV (k sh)" value={universe.minAdvK} onChange={(n) => u({ minAdvK: n })} />
          <NumField label="Low-float flag (<M sh)" value={universe.lowFloatFlagM} onChange={(n) => u({ lowFloatFlagM: n })} />
          <NumField label="Max borrow fee soft (%)" value={universe.maxBorrowFeeSoftPct} onChange={(n) => u({ maxBorrowFeeSoftPct: n })} />
          <NumField label="Max borrow fee hard (%)" value={universe.maxBorrowFeeHardPct} onChange={(n) => u({ maxBorrowFeeHardPct: n })} />
        </div>
      </Panel>

      <Panel label="SQUEEZE GUARD (§9)">
        <div className="p-3 text-[11px]">
          <NumField label="Gain caution (%)" hint="reduce size above this intraday gain" value={squeeze.gainCautionPct} onChange={(n) => s({ gainCautionPct: n })} />
          <NumField label="Gain abort/force-exit (%)" value={squeeze.gainAbortPct} onChange={(n) => s({ gainAbortPct: n })} />
          <NumField label="RVOL caution (×)" value={squeeze.rvolCaution} onChange={(n) => s({ rvolCaution: n })} />
          <NumField label="RVOL abort (×)" value={squeeze.rvolAbort} onChange={(n) => s({ rvolAbort: n })} />
          <NumField label="Borrow fee caution (%)" value={squeeze.feeCautionPct} onChange={(n) => s({ feeCautionPct: n })} />
          <NumField label="Borrow fee abort (%)" value={squeeze.feeAbortPct} onChange={(n) => s({ feeAbortPct: n })} />
          <NumField label="Float caution (<M sh)" value={squeeze.floatCautionM} onChange={(n) => s({ floatCautionM: n })} />
          <NumField label="Float abort (<M sh)" value={squeeze.floatAbortM} onChange={(n) => s({ floatAbortM: n })} />
          <NumField label="Adverse-move exit (%)" hint="force-exit when this far against entry" value={squeeze.adverseExitPct} onChange={(n) => s({ adverseExitPct: n })} />
          <p className="text-muted2 text-[10px] mt-2">Lowering abort thresholds flips more cockpit positions to EXIT on the next tick.</p>
        </div>
      </Panel>

      <Panel label="CIRCUIT BREAKERS">
        <div className="p-3 text-[11px]">
          <NumField label="Per-position max loss (%)" value={breakers.perPositionMaxLossPct} onChange={(n) => b({ perPositionMaxLossPct: n })} />
          <NumField label="Daily drawdown limit (%)" value={breakers.dailyDrawdownLimitPct} onChange={(n) => b({ dailyDrawdownLimitPct: n })} />
          <NumField label="Max concurrent positions" value={breakers.maxPositions} onChange={(n) => b({ maxPositions: n })} />
          <NumField label="Max gross short ($)" value={breakers.maxGrossShort} onChange={(n) => b({ maxGrossShort: n })} />
          <button onClick={reset} className="mt-3 w-full border border-edge rounded px-3 py-[6px] text-accent hover:bg-[#0c1320]">
            Reset to design defaults
          </button>
        </div>
      </Panel>
    </div>
  );
}
```

- [ ] **Step 2: Write a config interaction test**

`ui/src/tabs/config/__tests__/config.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../../mockData/store";
import { Config } from "../Config";

describe("Config", () => {
  it("renders the three sections", () => {
    render(<StoreProvider><Config /></StoreProvider>);
    expect(screen.getByText("UNIVERSE (§8)")).toBeInTheDocument();
    expect(screen.getByText("SQUEEZE GUARD (§9)")).toBeInTheDocument();
    expect(screen.getByText("CIRCUIT BREAKERS")).toBeInTheDocument();
  });

  it("edits a squeeze field", () => {
    render(<StoreProvider><Config /></StoreProvider>);
    const input = screen.getByDisplayValue("100") as HTMLInputElement; // gain abort default
    fireEvent.change(input, { target: { value: "80" } });
    expect((screen.getByDisplayValue("80") as HTMLInputElement)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run test**

Run: `npm run test -- config`
Expected: PASS (2 tests). If the second test is ambiguous because two fields share value `100` (gain abort and fee caution both default 100), change the assertion to select by label proximity: query `screen.getAllByDisplayValue("100")[0]`. Apply that fix if the test fails on ambiguity.

- [ ] **Step 4: Commit**

```bash
git add ui/src/tabs/config/Config.tsx ui/src/tabs/config/__tests__/config.test.tsx
git commit -m "feat(ui): config tab (universe / squeeze / breakers)"
```

---

## Task 16: Backtest tab

**Files:**
- Create: `ui/src/tabs/backtest/backtestData.ts`, `ui/src/tabs/backtest/Backtest.tsx`

- [ ] **Step 1: Implement `backtestData.ts`**

```ts
export interface BacktestTrade {
  date: string; symbol: string; side: "SHORT";
  entry: number; exit: number; pnl: number; retPct: number;
  borrowCost: number; holdMin: number; exitReason: "target" | "stop" | "time" | "guard";
}

export interface BacktestResult {
  equityCurve: number[];      // cumulative P&L points
  stats: { label: string; value: string }[];
  trades: BacktestTrade[];
}

// Deterministic sample result set (no live engine).
export const BACKTEST: BacktestResult = {
  equityCurve: [0, 320, 180, 640, 900, 760, 1180, 1020, 1480, 1320, 1760, 2040, 1880, 2360, 2720, 2540, 3010, 3320],
  stats: [
    { label: "Total P&L", value: "+$3,320" },
    { label: "Win rate", value: "58%" },
    { label: "Profit factor", value: "1.74" },
    { label: "Max drawdown", value: "−$420" },
    { label: "Sharpe", value: "1.9" },
    { label: "Avg hold", value: "26m" },
    { label: "Avg borrow cost", value: "$0.03/sh" },
    { label: "Slippage drag", value: "−$610" },
    { label: "# trades", value: "84" },
  ],
  trades: [
    { date: "06-03", symbol: "PLTX", side: "SHORT", entry: 3.9, exit: 3.4, pnl: 980, retPct: 12.8, borrowCost: 42, holdMin: 22, exitReason: "target" },
    { date: "06-04", symbol: "GNSX", side: "SHORT", entry: 2.3, exit: 2.6, pnl: -420, retPct: -13.0, borrowCost: 88, holdMin: 9, exitReason: "guard" },
    { date: "06-05", symbol: "MULN", side: "SHORT", entry: 1.5, exit: 1.32, pnl: 540, retPct: 12.0, borrowCost: 17, holdMin: 41, exitReason: "time" },
    { date: "06-06", symbol: "CABL", side: "SHORT", entry: 7.6, exit: 7.1, pnl: 750, retPct: 6.6, borrowCost: 23, holdMin: 33, exitReason: "target" },
    { date: "06-09", symbol: "BBLG", side: "SHORT", entry: 2.1, exit: 2.0, pnl: 120, retPct: 4.8, borrowCost: 51, holdMin: 18, exitReason: "stop" },
  ],
};
```

- [ ] **Step 2: Implement `Backtest.tsx`** (inline SVG equity curve, no chart lib)

```tsx
import { Panel } from "../../components/Panel";
import { BACKTEST, type BacktestTrade } from "./backtestData";

function EquityCurve({ values }: { values: number[] }) {
  const w = 640, h = 180, pad = 8;
  const max = Math.max(...values), min = Math.min(...values, 0);
  const x = (i: number) => pad + (i / (values.length - 1)) * (w - pad * 2);
  const y = (v: number) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);
  const line = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(values.length - 1).toFixed(1)},${h - pad} L${x(0).toFixed(1)},${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <path d={area} fill="#2dd4bf22" />
      <path d={line} fill="none" stroke="#2dd4bf" strokeWidth={1.5} />
      <line x1={pad} y1={y(0)} x2={w - pad} y2={y(0)} stroke="#141b27" strokeDasharray="3 3" />
    </svg>
  );
}

const reasonColor = (r: BacktestTrade["exitReason"]) =>
  r === "target" ? "text-up" : r === "guard" || r === "stop" ? "text-down" : "text-muted";

export function Backtest() {
  return (
    <div className="p-[10px] flex flex-col gap-[10px]">
      <Panel label="EQUITY CURVE — cumulative P&L"><div className="p-3"><EquityCurve values={BACKTEST.equityCurve} /></div></Panel>

      <Panel label="STATS">
        <div className="p-3 grid grid-cols-3 gap-3 font-mono">
          {BACKTEST.stats.map((s) => (
            <div key={s.label} className="bg-bg border border-edge rounded p-3">
              <div className="text-muted text-[9px] tracking-[1px]">{s.label.toUpperCase()}</div>
              <div className={`text-[16px] font-bold ${s.value.startsWith("−") || s.value.startsWith("-") ? "text-down" : "text-strong"}`}>{s.value}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel label="TRADES">
        <table className="w-full border-collapse font-mono text-[9.5px]">
          <thead><tr className="text-muted2 text-right">
            {["DATE", "SYM", "ENTRY", "EXIT", "P&L", "RET%", "BORROW", "HOLD", "EXIT"].map((h) => (
              <th key={h} className={`font-medium px-3 py-1 ${h === "DATE" || h === "SYM" ? "text-left" : ""}`}>{h}</th>
            ))}
          </tr></thead>
          <tbody className="text-right">
            {BACKTEST.trades.map((t, i) => (
              <tr key={i} className="border-t border-rowdiv">
                <td className="px-3 py-1 text-left">{t.date}</td>
                <td className="px-3 py-1 text-left text-strong">{t.symbol}</td>
                <td className="px-3 py-1">{t.entry.toFixed(2)}</td>
                <td className="px-3 py-1">{t.exit.toFixed(2)}</td>
                <td className={`px-3 py-1 ${t.pnl >= 0 ? "text-up" : "text-down"}`}>{t.pnl >= 0 ? "+" : "-"}${Math.abs(t.pnl)}</td>
                <td className={`px-3 py-1 ${t.retPct >= 0 ? "text-up" : "text-down"}`}>{t.retPct >= 0 ? "+" : ""}{t.retPct.toFixed(1)}%</td>
                <td className="px-3 py-1">${t.borrowCost}</td>
                <td className="px-3 py-1">{t.holdMin}m</td>
                <td className={`px-3 py-1 ${reasonColor(t.exitReason)}`}>{t.exitReason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc -b`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add ui/src/tabs/backtest/backtestData.ts ui/src/tabs/backtest/Backtest.tsx
git commit -m "feat(ui): backtest tab (equity curve, stats, trades)"
```

---

## Task 17: App shell wiring + final verification

**Files:**
- Modify: `ui/src/App.tsx` (replace the Task 1 stub)
- Create: `ui/src/tabs/cockpit/CockpitWithEngine.tsx`

- [ ] **Step 1: Create `CockpitWithEngine.tsx`** (mounts the tick engine only when cockpit is visible)

```tsx
import { Cockpit } from "./Cockpit";
import { useTickEngine } from "../../mockData/useTickEngine";

export function CockpitWithEngine() {
  useTickEngine(1000);
  return <Cockpit />;
}
```

- [ ] **Step 2: Replace `App.tsx`**

```tsx
import { useState } from "react";
import { StoreProvider } from "./mockData/store";
import { TopBar, type TabName } from "./components/TopBar";
import { CockpitWithEngine } from "./tabs/cockpit/CockpitWithEngine";
import { Config } from "./tabs/config/Config";
import { Backtest } from "./tabs/backtest/Backtest";

function Shell() {
  const [tab, setTab] = useState<TabName>("Cockpit");
  return (
    <div className="min-h-full bg-bg text-body">
      <TopBar tab={tab} onTab={setTab} />
      {tab === "Cockpit" && <CockpitWithEngine />}
      {tab === "Config" && <Config />}
      {tab === "Backtest" && <Backtest />}
    </div>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  );
}
```

> The tick engine lives inside `CockpitWithEngine`, so leaving the Cockpit tab stops ticking; the store (and the kill-switch/halt state) persists across tabs because `StoreProvider` wraps the whole shell.

- [ ] **Step 3: Write an app navigation test**

`ui/src/__tests__/app.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import App from "../App";

describe("App", () => {
  it("switches tabs", () => {
    render(<App />);
    expect(screen.getByText(/OPEN POSITIONS/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Backtest"));
    expect(screen.getByText(/EQUITY CURVE/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Config"));
    expect(screen.getByText("UNIVERSE (§8)")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the full test suite**

Run (from `ui/`): `npm run test`
Expected: all suites PASS (rng, guard, pnl, orders, seed, store, tick, primitives, killswitch, cockpit, config, app).

- [ ] **Step 5: Production build**

Run (from `ui/`): `npm run build`
Expected: `tsc -b` clean, `vite build` writes `dist/` with no errors.

- [ ] **Step 6: Manual verification**

Run (from `ui/`): `npm run dev`, open the printed URL, and confirm:
- Cockpit shows positions, active orders, scanner, right rail, live log; prices/P&L/log update ~every second.
- Clicking KILL SWITCH → Confirm flatten → positions clear, "TRADING HALTED" banner appears, log shows HALT; RESUME clears it.
- Config: lower "Gain abort/force-exit (%)" to a small value, return to Cockpit, confirm more positions show GUARD = EXIT.
- Backtest renders equity curve, stat grid, and trades table.

- [ ] **Step 7: Commit**

```bash
git add ui/src/App.tsx ui/src/tabs/cockpit/CockpitWithEngine.tsx ui/src/__tests__/app.test.tsx
git commit -m "feat(ui): app shell wiring + tab navigation"
```

---

## Self-Review

**1. Spec coverage**
- 3 tabs (Cockpit/Config/Backtest) → Tasks 12–17. ✓
- Cockpit panels (positions, active orders, scanner, rail: P&L/breakers/alerts/locates, live log, kill switch) → Tasks 11–14. ✓
- Swappable mock-data layer + tick engine → Tasks 2–9. ✓
- Config = §8/§9 knobs, edits flow into cockpit guard → Tasks 8 (UPDATE_CONFIG re-eval) + 15. ✓
- Backtest equity curve/stats/trades → Task 16. ✓
- Visual tokens single source of truth → Task 1 tailwind.config. ✓
- Vitest on real logic (guard, pnl, orders, store, tick) → Tasks 4–9. ✓
- Run instructions / build verification → Task 17. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code. The one illustrative dead line in Task 13 is explicitly removed in the next step. ✓

**3. Type consistency:** `evaluateGuard(GuardInput, SqueezeThresholds)`, `advanceOrder(order, dt, roll)`, `tickStep(state, seed)`, store actions (`KILL/RESUME/CANCEL_ORDER/COVER_POSITION/UPDATE_CONFIG/TICK`), and `AppState` fields are used identically across seed/store/tick/components. `defaultSqueeze` lives in `guard.ts`; `defaultUniverse`/`defaultBreakers` in `config-defaults.ts` — imports match. ✓
