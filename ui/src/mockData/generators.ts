import type { Candidate, LocateInfo, LogEvent, LogKind } from "./types";
import { makeRng, randBetween, pick } from "./rng";

const SYMBOLS = ["PLTX", "DROP", "GNSX", "MULN", "CABL", "VRAX", "TICK", "BBLG", "ZKIN", "RGTI"];

export function symbolPool(): string[] {
  return [...SYMBOLS];
}

export function makeCandidate(seed: number, symbol: string): Candidate {
  const rng = makeRng(seed);
  const last = randBetween(rng, 1.2, 12);
  const pumpScore = randBetween(rng, 0.3, 0.95);
  const dilutionScore = randBetween(rng, 0.1, 0.85);
  const borrowFeePct = randBetween(rng, 20, 320);
  const borrowScore = Math.max(0, 1 - borrowFeePct / 320);
  const composite = Number(
    (pumpScore * 0.45 + dilutionScore * 0.3 + borrowScore * 0.25).toFixed(2)
  );
  const noBorrow = borrowFeePct > 290;
  const locate: LocateInfo = noBorrow
    ? { ok: false, reason: "no borrow" }
    : { ok: true, costPerShare: Number(randBetween(rng, 0.01, 0.05).toFixed(2)) };
  return {
    id: `c-${symbol}`,
    symbol,
    last: Number(last.toFixed(2)),
    pctChange: Math.round(randBetween(rng, 18, 110)),
    rvol: Number(randBetween(rng, 3, 14).toFixed(1)),
    floatM: Math.round(randBetween(rng, 3, 40)),
    borrowFeePct: Math.round(borrowFeePct),
    pumpScore: Number(pumpScore.toFixed(2)),
    dilutionScore: Number(dilutionScore.toFixed(2)),
    borrowScore: Number(borrowScore.toFixed(2)),
    compositeScore: composite,
    locate,
  };
}

let logCounter = 0;
export function resetLogCounter() { logCounter = 0; }
export function makeLogEvent(ts: number, kind: LogKind, message: string, pnl?: number): LogEvent {
  return { id: `l-${ts}-${logCounter++}`, ts, kind, message, pnl };
}

export const LOG_KINDS: LogKind[] = [
  "DATA", "SIGNAL", "GUARD", "LOCATE", "ORDER", "FILL", "EXIT", "RISK", "HALT",
];

// Build a small plausible random log line for the tick engine.
export function randomLogLine(seed: number, ts: number): LogEvent {
  const rng = makeRng(seed);
  const sym = pick(rng, SYMBOLS);
  const templates: Array<[LogKind, string]> = [
    ["DATA", `Polygon: ${sym} printed +${Math.round(randBetween(rng, 20, 120))}% on ${randBetween(rng, 3, 13).toFixed(0)}x RVOL`],
    ["SIGNAL", `${sym} pump-fade score ${randBetween(rng, 0.6, 0.95).toFixed(2)} -> candidate`],
    ["LOCATE", `${sym} ${Math.round(randBetween(rng, 4, 14))}k reserved @ $${randBetween(rng, 0.01, 0.05).toFixed(2)}/sh`],
    ["GUARD", `${sym} RVOL ${randBetween(rng, 8, 13).toFixed(0)}x - size capped`],
  ];
  const [kind, message] = pick(rng, templates);
  return makeLogEvent(ts, kind, message);
}
