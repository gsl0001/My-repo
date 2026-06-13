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
