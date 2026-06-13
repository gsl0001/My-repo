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
