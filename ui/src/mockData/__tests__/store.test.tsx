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
