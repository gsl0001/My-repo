import { describe, it, expect } from "vitest";
import { tickStep } from "../tick";
import { initialState } from "../store";
import type { AppState, Order } from "../types";

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

  it("advances the sim clock by 1s per active tick", () => {
    const s0 = initialState();
    expect(tickStep(s0, 7).clockMs).toBe(s0.clockMs + 1000);
  });

  it("is frozen (unchanged) when paused", () => {
    const paused = { ...initialState(), account: { ...initialState().account, paused: true } };
    const out = tickStep(paused, 7);
    expect(out).toBe(paused);
  });

  it("force-exits a guard-EXIT position, booking it to realized and logging it", () => {
    const base = initialState();
    // BBLG (index 1) has rvol 11 >= rvolAbort 10 -> always guard EXIT
    const bblg = base.positions.find((p) => p.symbol === "BBLG")!;
    const s = { ...base, positions: [bblg], orders: [], candidates: [] };
    const out = tickStep(s, 3);
    expect(out.positions).toHaveLength(0);
    expect(out.account.positionsCount).toBe(0);
    expect(out.log.some((e) => e.kind === "EXIT")).toBe(true);
  });

  it("fills a working SHORT order into a position with an attached stop", () => {
    const base = initialState();
    const order: Order = {
      id: "o-ZTST", symbol: "ZTST", side: "SHORT", type: "LMT",
      qty: 1000, price: 3, filledQty: 0, ageSec: 0, status: "working",
    };
    let s: AppState = { ...base, positions: [], orders: [order], candidates: [] };
    let opened = false;
    for (let i = 0; i < 60 && !opened; i++) {
      s = tickStep(s, 1000 + i);
      opened = s.positions.some((p) => p.symbol === "ZTST");
    }
    expect(opened).toBe(true);
    expect(s.orders.some((o) => o.symbol === "ZTST" && o.type === "STP")).toBe(true);
    expect(s.log.some((e) => e.kind === "FILL")).toBe(true);
  });
});
