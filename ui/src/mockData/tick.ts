import type { AppState, Position, Candidate } from "./types";
import { makeRng } from "./rng";
import { shortUnrealized, shortPctFromEntry, adverseMovePct } from "./pnl";
import { evaluateGuard } from "./guard";
import { advanceOrder } from "./orders";
import { randomLogLine } from "./generators";

const CAP = 200;
const DT = 1;

function drift(rng: () => number, price: number, vol: number): number {
  const pct = (rng() - 0.5) * vol;
  return Math.max(0.5, Number((price * (1 + pct)).toFixed(2)));
}

// One pure tick. `tickSeed` makes it deterministic in tests.
export function tickStep(state: AppState, tickSeed: number): AppState {
  if (state.account.halted) return state;
  const rng = makeRng(tickSeed);
  const now = Date.now();

  const positions: Position[] = state.positions.map((p) => {
    const last = drift(rng, p.last, 0.04);
    const intradayGainPct = ((last - p.priorClose) / p.priorClose) * 100;
    return {
      ...p,
      last,
      pctFromEntry: Number(shortPctFromEntry(p.avgPrice, last).toFixed(2)),
      unrealizedPnl: Math.round(shortUnrealized(p.avgPrice, last, p.shortQty)),
      guardState: evaluateGuard(
        { intradayGainPct, rvol: p.rvol, borrowFeePct: p.borrowFeePct, floatM: p.floatM, adverseMovePct: adverseMovePct(p.avgPrice, last) },
        state.config.squeeze
      ),
    };
  });

  const candidates: Candidate[] = state.candidates
    .map((c) => {
      const last = drift(rng, c.last, 0.05);
      return { ...c, last, pctChange: Math.round(c.pctChange + (rng() - 0.5) * 6) };
    })
    .sort((a, b) => b.compositeScore - a.compositeScore);

  const orders = state.orders
    .map((o) => advanceOrder(o, DT, rng))
    .filter((o) => o.status !== "filled" || o.type === "STP");

  const realizedPnl = state.account.realizedPnl;
  const unrealized = positions.reduce((s, p) => s + p.unrealizedPnl, 0);
  const dayPnl = realizedPnl + unrealized;
  const grossShort = Math.round(positions.reduce((s, p) => s + p.shortQty * p.last, 0));
  const equity = state.account.startEquity + dayPnl;
  const drawdownPct = Number(Math.min(0, (dayPnl / state.account.startEquity) * 100).toFixed(2));

  const log =
    rng() < 0.5
      ? [randomLogLine(tickSeed + 1, now), ...state.log].slice(0, CAP)
      : state.log.slice(0, CAP);

  return {
    ...state,
    positions,
    candidates,
    orders,
    account: { ...state.account, dayPnl, equity, grossShort, drawdownPct, positionsCount: positions.length },
    log,
  };
}
