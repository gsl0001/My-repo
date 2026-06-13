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

  it("COVER_POSITION closes one position, books realized P&L, recomputes dayPnl, cancels its stop", () => {
    const s0 = initialState();
    const sym = s0.positions[0].symbol;
    const before = s0.account.realizedPnl;
    const s = reducer(s0, { type: "COVER_POSITION", symbol: sym });
    expect(s.positions.find((p) => p.symbol === sym)).toBeUndefined();
    expect(s.account.realizedPnl).not.toBe(before);
    // dayPnl stays consistent with realized + remaining unrealized (no stale value)
    const unreal = s.positions.reduce((a, p) => a + p.unrealizedPnl, 0);
    expect(s.account.dayPnl).toBe(s.account.realizedPnl + unreal);
    // the symbol's resting stop is gone
    expect(s.orders.some((o) => o.symbol === sym && o.type === "STP")).toBe(false);
  });

  it("KILL leaves no orders (no orphaned stops) and a consistent dayPnl", () => {
    const s = reducer(initialState(), { type: "KILL" });
    expect(s.orders).toHaveLength(0);
    expect(s.account.dayPnl).toBe(s.account.realizedPnl);
  });

  it("TOGGLE_PAUSE flips the paused flag and logs it", () => {
    const s = reducer(initialState(), { type: "TOGGLE_PAUSE" });
    expect(s.account.paused).toBe(true);
    expect(reducer(s, { type: "TOGGLE_PAUSE" }).account.paused).toBe(false);
  });

  it("SHORT_CANDIDATE places a working short for a borrowable candidate", () => {
    const s0 = initialState();
    const c = s0.candidates.find((x) => x.locate.ok)!;
    const s = reducer(s0, { type: "SHORT_CANDIDATE", symbol: c.symbol });
    const order = s.orders.find((o) => o.symbol === c.symbol && o.side === "SHORT");
    expect(order).toBeDefined();
    expect(order!.status).toBe("working");
    expect(s.log[0].kind).toBe("ORDER");
  });

  it("SHORT_CANDIDATE is blocked (Reg SHO) when the locate is unavailable", () => {
    const s0 = initialState();
    const noBorrow = s0.candidates.find((x) => !x.locate.ok);
    if (!noBorrow) return; // seed may not always include one; skip if absent
    const before = s0.orders.length;
    const s = reducer(s0, { type: "SHORT_CANDIDATE", symbol: noBorrow.symbol });
    expect(s.orders).toHaveLength(before); // no order placed
    expect(s.log[0].kind).toBe("RISK");
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
