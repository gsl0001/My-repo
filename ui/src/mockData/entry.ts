import type { Account, Candidate, CircuitBreakers, Order } from "./types";

// Target dollar notional per new short (mock sizing). Real sizing would be
// % of ADV + vol-based; this keeps positions plausibly sized for the demo.
export const TARGET_NOTIONAL = 20000;

// Whether a new short may be opened on this candidate, given current exposure.
// Mirrors the design's Reg SHO + circuit-breaker gates.
export function canEnter(
  cand: Candidate,
  account: Account,
  breakers: CircuitBreakers,
  openCount: number
): { ok: boolean; reason?: string } {
  if (!cand.locate.ok) return { ok: false, reason: "no confirmed locate (Reg SHO)" };
  if (openCount >= breakers.maxPositions) return { ok: false, reason: "max positions reached" };
  if (account.grossShort >= breakers.maxGrossShort) return { ok: false, reason: "gross-short cap reached" };
  return { ok: true };
}

// Share count for a new short, capped by remaining gross-short capacity.
export function shortQtyFor(cand: Candidate, account: Account, breakers: CircuitBreakers): number {
  const remainingGross = breakers.maxGrossShort - account.grossShort;
  if (remainingGross <= 0) return 0;
  const notional = Math.min(TARGET_NOTIONAL, remainingGross);
  const qty = Math.round(notional / cand.last / 100) * 100;
  return Math.max(100, qty);
}

export function makeShortOrder(cand: Candidate, qty: number, idSuffix: string): Order {
  return {
    id: `o-${cand.symbol}-${idSuffix}`,
    symbol: cand.symbol,
    side: "SHORT",
    type: "LMT",
    qty,
    price: cand.last,
    filledQty: 0,
    ageSec: 0,
    status: "working",
  };
}
