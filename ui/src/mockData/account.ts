import type { Account, Position } from "./types";

// Recompute account aggregates from the current positions + booked realized P&L.
// Single source of truth so the top bar never shows a stale day-P&L after a
// cover/kill (which only change realized) — used by both the reducer and the tick.
export function recomputeAccount(
  account: Account,
  positions: Position[],
  startEquity: number
): Account {
  const unrealized = positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const dayPnl = account.realizedPnl + unrealized;
  const grossShort = Math.round(positions.reduce((s, p) => s + p.shortQty * p.last, 0));
  return {
    ...account,
    startEquity,
    dayPnl,
    equity: startEquity + dayPnl,
    grossShort,
    drawdownPct: Number(Math.min(0, (dayPnl / startEquity) * 100).toFixed(2)),
    positionsCount: positions.length,
  };
}
