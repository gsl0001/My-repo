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
