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
