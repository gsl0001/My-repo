import { describe, it, expect } from "vitest";
import { canEnter, shortQtyFor, makeShortOrder } from "../entry";
import { defaultBreakers } from "../config-defaults";
import type { Account, Candidate } from "../types";

const acct: Account = {
  startEquity: 100000, equity: 100000, dayPnl: 0, realizedPnl: 0,
  grossShort: 0, grossLimit: 150000, drawdownPct: 0, positionsCount: 0,
  halted: false, paused: false,
};

const cand = (over: Partial<Candidate>): Candidate => ({
  id: "c", symbol: "PLTX", last: 4, pctChange: 60, rvol: 9, floatM: 6,
  borrowFeePct: 80, pumpScore: 0.8, dilutionScore: 0.4, borrowScore: 0.7,
  compositeScore: 0.82, locate: { ok: true, costPerShare: 0.02 }, ...over,
});

describe("entry gates", () => {
  it("blocks shorts with no confirmed locate (Reg SHO)", () => {
    const r = canEnter(cand({ locate: { ok: false, reason: "no borrow" } }), acct, defaultBreakers, 0);
    expect(r.ok).toBe(false);
    expect(r.reason).toMatch(/locate/i);
  });

  it("blocks when at max positions", () => {
    const r = canEnter(cand({}), acct, defaultBreakers, defaultBreakers.maxPositions);
    expect(r.ok).toBe(false);
    expect(r.reason).toMatch(/max positions/i);
  });

  it("blocks when gross-short cap is reached", () => {
    const r = canEnter(cand({}), { ...acct, grossShort: 150000 }, defaultBreakers, 0);
    expect(r.ok).toBe(false);
  });

  it("allows when locate ok and within caps", () => {
    expect(canEnter(cand({}), acct, defaultBreakers, 0).ok).toBe(true);
  });
});

describe("shortQtyFor", () => {
  it("sizes to ~$20k notional rounded to 100s", () => {
    expect(shortQtyFor(cand({ last: 4 }), acct, defaultBreakers)).toBe(5000); // 20000/4
  });

  it("is capped by remaining gross capacity", () => {
    const qty = shortQtyFor(cand({ last: 4 }), { ...acct, grossShort: 149000 }, defaultBreakers);
    expect(qty * 4).toBeLessThanOrEqual(1000 + 4 * 100); // ~remaining $1k worth, min lot
  });
});

describe("makeShortOrder", () => {
  it("creates a working SHORT LMT at the candidate's last", () => {
    const o = makeShortOrder(cand({ last: 4 }), 5000, "x");
    expect(o.side).toBe("SHORT");
    expect(o.type).toBe("LMT");
    expect(o.status).toBe("working");
    expect(o.price).toBe(4);
    expect(o.qty).toBe(5000);
  });
});
