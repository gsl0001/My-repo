import { describe, it, expect } from "vitest";
import { recomputeAccount } from "../account";
import type { Account, Position } from "../types";

const baseAccount: Account = {
  startEquity: 100000,
  equity: 100000,
  dayPnl: 0,
  realizedPnl: 500,
  grossShort: 0,
  grossLimit: 150000,
  drawdownPct: 0,
  positionsCount: 0,
  halted: false,
  paused: false,
};

const pos = (over: Partial<Position>): Position => ({
  id: "p", symbol: "X", shortQty: 1000, avgPrice: 10, last: 9, priorClose: 7,
  pctFromEntry: 10, unrealizedPnl: 1000, stopPrice: 11, borrowFeePct: 40,
  rvol: 3, floatM: 30, guardState: "ok", ...over,
});

describe("recomputeAccount", () => {
  it("dayPnl = realized + unrealized", () => {
    const a = recomputeAccount(baseAccount, [pos({ unrealizedPnl: 1000 })], 100000);
    expect(a.dayPnl).toBe(1500); // 500 realized + 1000 unrealized
  });

  it("equity = startEquity + dayPnl, gross = sum(qty*last), count = positions", () => {
    const a = recomputeAccount(baseAccount, [pos({ shortQty: 1000, last: 9 })], 100000);
    expect(a.equity).toBe(101500);
    expect(a.grossShort).toBe(9000);
    expect(a.positionsCount).toBe(1);
  });

  it("with no positions, dayPnl equals realized only", () => {
    const a = recomputeAccount(baseAccount, [], 100000);
    expect(a.dayPnl).toBe(500);
    expect(a.grossShort).toBe(0);
    expect(a.positionsCount).toBe(0);
  });

  it("preserves halted/paused flags", () => {
    const a = recomputeAccount({ ...baseAccount, halted: true, paused: true }, [], 100000);
    expect(a.halted).toBe(true);
    expect(a.paused).toBe(true);
  });

  it("drawdown is negative when underwater, clamped to 0 when up", () => {
    const down = recomputeAccount({ ...baseAccount, realizedPnl: -4000 }, [], 100000);
    expect(down.drawdownPct).toBeCloseTo(-4, 2);
    const up = recomputeAccount({ ...baseAccount, realizedPnl: 4000 }, [], 100000);
    expect(up.drawdownPct).toBe(0);
  });
});
