import type { AppState, Position } from "./types";
import { shortUnrealized, shortPctFromEntry } from "./pnl";
import { evaluateGuard, defaultSqueeze } from "./guard";
import { defaultUniverse, defaultBreakers } from "./config-defaults";
import { makeCandidate, makeLogEvent, resetLogCounter, symbolPool } from "./generators";

interface SeedPos {
  symbol: string; shortQty: number; avgPrice: number; last: number;
  priorClose: number; stopPrice: number; borrowFeePct: number; rvol: number; floatM: number;
}

const SEED_POSITIONS: SeedPos[] = [
  { symbol: "TICK", shortQty: 8000, avgPrice: 4.21, last: 4.12, priorClose: 3.4, stopPrice: 4.55, borrowFeePct: 84, rvol: 6, floatM: 22 },
  { symbol: "BBLG", shortQty: 12000, avgPrice: 1.98, last: 2.07, priorClose: 1.5, stopPrice: 2.18, borrowFeePct: 212, rvol: 11, floatM: 9 },
  { symbol: "CABL", shortQty: 5000, avgPrice: 7.4, last: 7.34, priorClose: 6.9, stopPrice: 7.85, borrowFeePct: 41, rvol: 4, floatM: 30 },
  { symbol: "VRAX", shortQty: 3200, avgPrice: 11.1, last: 10.62, priorClose: 9.8, stopPrice: 11.9, borrowFeePct: 67, rvol: 12, floatM: 14 },
];

function buildPosition(p: SeedPos, squeeze = defaultSqueeze): Position {
  const intradayGainPct = ((p.last - p.priorClose) / p.priorClose) * 100;
  const adverse = Math.max(0, ((p.last - p.avgPrice) / p.avgPrice) * 100);
  return {
    id: `p-${p.symbol}`,
    symbol: p.symbol,
    shortQty: p.shortQty,
    avgPrice: p.avgPrice,
    last: p.last,
    priorClose: p.priorClose,
    pctFromEntry: Number(shortPctFromEntry(p.avgPrice, p.last).toFixed(2)),
    unrealizedPnl: Math.round(shortUnrealized(p.avgPrice, p.last, p.shortQty)),
    stopPrice: p.stopPrice,
    borrowFeePct: p.borrowFeePct,
    rvol: p.rvol,
    floatM: p.floatM,
    guardState: evaluateGuard(
      { intradayGainPct, rvol: p.rvol, borrowFeePct: p.borrowFeePct, floatM: p.floatM, adverseMovePct: adverse },
      squeeze
    ),
  };
}

export function makeSeedState(seed: number): AppState {
  resetLogCounter();
  const positions = SEED_POSITIONS.map((p) => buildPosition(p));
  const candidates = symbolPool()
    .slice(0, 5)
    .map((s, i) => makeCandidate(seed + i + 1, s))
    .sort((a, b) => b.compositeScore - a.compositeScore);

  const t0 = Date.UTC(2026, 5, 12, 13, 42, 15);
  const log = [
    makeLogEvent(t0, "DATA", "Polygon: VRAX printed +112% on 11x RVOL"),
    makeLogEvent(t0 - 1340, "GUARD", "VRAX crossed force-exit (>100% & accelerating)"),
    makeLogEvent(t0 - 3210, "EXIT", "VRAX buy-to-cover 3,200 @ 10.58", 1664),
    makeLogEvent(t0 - 19000, "SIGNAL", "BBLG pump-fade score 0.81 -> candidate"),
    makeLogEvent(t0 - 35000, "LOCATE", "BBLG 12k reserved @ $0.04/sh (TradeZero)"),
    makeLogEvent(t0 - 68000, "ORDER", "SHORT VRAX 3,200 @ 11.10 - stop 11.90 attached"),
    makeLogEvent(t0 - 202000, "FILL", "SHORT TICK 8,000 @ 4.21"),
    makeLogEvent(t0 - 762000, "RISK", "Session armed - daily DD limit -4.0% - max 6 positions"),
  ];

  const realizedPnl = 1664;
  const unrealized = positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const dayPnl = realizedPnl + unrealized;
  const grossShort = positions.reduce((s, p) => s + p.shortQty * p.last, 0);
  const startEquity = 128400 - dayPnl;

  return {
    positions,
    orders: [
      { id: "o-DROP", symbol: "DROP", side: "SHORT", type: "LMT", qty: 6000, price: 5.2, filledQty: 0, ageSec: 4, status: "working" },
      { id: "o-BBLG", symbol: "BBLG", side: "SHORT", type: "LMT", qty: 12000, price: 1.98, filledQty: 7400, ageSec: 11, status: "partial" },
      { id: "o-TICK", symbol: "TICK", side: "BUY", type: "STP", qty: 8000, price: 4.55, filledQty: 0, ageSec: 660, status: "stop-resting" },
      { id: "o-GNSX", symbol: "GNSX", side: "LOCATE", type: "REQ", qty: 10000, price: null, filledQty: 0, ageSec: 2, status: "pending-locate" },
    ],
    candidates,
    log,
    account: {
      startEquity,
      equity: 128400,
      dayPnl,
      realizedPnl,
      grossShort: Math.round(grossShort),
      grossLimit: 150000,
      drawdownPct: 0,
      positionsCount: positions.length,
      halted: false,
      paused: false,
    },
    config: { universe: defaultUniverse, squeeze: defaultSqueeze, breakers: defaultBreakers },
    eventsPerMin: 14,
    clockMs: t0,
  };
}
