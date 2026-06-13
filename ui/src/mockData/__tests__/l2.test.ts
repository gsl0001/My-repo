import { describe, it, expect } from "vitest";
import {
  imbalance, sweepBuy, exhaustion, absorptionAtAsk, evaluateL2, initL2, stepL2,
  type L2Book, type TapePrint,
} from "../l2";

const book = (bids: [number, number][], asks: [number, number][]): L2Book => ({
  symbol: "X",
  bids: bids.map(([price, size]) => ({ price, size })),
  asks: asks.map(([price, size]) => ({ price, size })),
});

describe("L2 features", () => {
  it("imbalance sign reflects depth", () => {
    expect(imbalance(book([[4.1, 2000]], [[4.2, 200]]))).toBeGreaterThan(0.5);
    expect(imbalance(book([[4.1, 200]], [[4.2, 2000]]))).toBeLessThan(-0.5);
  });

  it("sweepBuy needs >= 3 distinct buy prices within 1s", () => {
    const tape: TapePrint[] = [
      { ts: 10, price: 4.12, size: 100, aggressor: "buy" },
      { ts: 10.1, price: 4.13, size: 100, aggressor: "buy" },
      { ts: 10.2, price: 4.14, size: 100, aggressor: "buy" },
    ];
    expect(sweepBuy(tape, 10.3)).toBe(true);
    expect(sweepBuy(tape.slice(0, 2), 10.3)).toBe(false);
  });

  it("exhaustion fires when the tape slows in the second half", () => {
    const tape: TapePrint[] = [
      ...Array.from({ length: 6 }, (_, i) => ({ ts: 10 + i * 0.1, price: 4.1, size: 100, aggressor: "buy" as const })),
      { ts: 13.5, price: 4.1, size: 100, aggressor: "buy" },
    ];
    expect(exhaustion(tape, 13.6)).toBe(true);
  });

  it("absorption detects heavy buying into a deep, refreshing ask", () => {
    const b = book([[4.1, 500]], [[4.12, 6000]]);
    const tape: TapePrint[] = [{ ts: 10, price: 4.12, size: 6000, aggressor: "buy" }];
    expect(absorptionAtAsk(b, tape, 10.5)).toBe(true);
  });
});

describe("evaluateL2", () => {
  it("enters on hidden-seller absorption", () => {
    const b = book([[4.1, 500]], [[4.12, 6000]]);
    const tape: TapePrint[] = [{ ts: 10, price: 4.12, size: 6000, aggressor: "buy" }];
    const { signal } = evaluateL2(b, tape, 10.5, false, false);
    expect(signal.kind).toBe("enter");
  });

  it("exits on an up-sweep while in position", () => {
    const tape: TapePrint[] = [
      { ts: 10, price: 4.12, size: 100, aggressor: "buy" },
      { ts: 10.1, price: 4.13, size: 100, aggressor: "buy" },
      { ts: 10.2, price: 4.14, size: 100, aggressor: "buy" },
    ];
    const { signal } = evaluateL2(book([[4.1, 100]], [[4.12, 100]]), tape, 10.3, true, false);
    expect(signal.kind).toBe("exit");
  });

  it("is vetoed by a spoofy book", () => {
    const b = book([[4.1, 500]], [[4.12, 6000]]);
    const tape: TapePrint[] = [{ ts: 10, price: 4.12, size: 6000, aggressor: "buy" }];
    const { signal } = evaluateL2(b, tape, 10.5, false, true); // spoof = true
    expect(signal.kind).toBe("none");
  });
});

describe("L2 generator", () => {
  it("initL2 builds a 6-level book", () => {
    const sim = initL2("TICK", 4.0);
    expect(sim.book.bids).toHaveLength(6);
    expect(sim.book.asks).toHaveLength(6);
  });

  it("stepL2 is deterministic for a seed and advances the clock", () => {
    const sim = initL2("TICK", 4.0);
    const a = stepL2(sim, 42);
    const b = stepL2(sim, 42);
    expect(a.now).toBe(sim.now + 1);
    expect(a.ref).toBe(b.ref);
    expect(a.book.asks[0].price).toBe(b.book.asks[0].price);
  });
});
