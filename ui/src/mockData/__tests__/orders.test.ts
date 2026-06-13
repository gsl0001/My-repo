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
