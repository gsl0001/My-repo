import type { AppState, Position, Candidate, Order, LogEvent, SqueezeThresholds } from "./types";
import { makeRng } from "./rng";
import { shortUnrealized, shortPctFromEntry, adverseMovePct } from "./pnl";
import { evaluateGuard } from "./guard";
import { advanceOrder } from "./orders";
import { makeLogEvent, randomLogLine, makeCandidate, symbolPool } from "./generators";
import { recomputeAccount } from "./account";
import { canEnter, shortQtyFor, makeShortOrder } from "./entry";
import { initL2, stepL2, evaluateL2 } from "./l2";

const CAP = 200;
const DT = 1;
const STEP_MS = 1000;
const MAX_CANDIDATES = 6;

function drift(rng: () => number, price: number, vol: number): number {
  const pct = (rng() - 0.5) * vol;
  return Math.max(0.5, Number((price * (1 + pct)).toFixed(2)));
}

function stopFor(avgPrice: number): number {
  return Number((avgPrice * 1.08).toFixed(2)); // 8% above entry for a short
}

function attachStop(symbol: string, avgPrice: number, qty: number, idSuffix: string): Order {
  return {
    id: `stp-${symbol}-${idSuffix}`,
    symbol,
    side: "BUY",
    type: "STP",
    qty,
    price: stopFor(avgPrice),
    filledQty: 0,
    ageSec: 0,
    status: "stop-resting",
  };
}

function positionFromFill(order: Order, cand: Candidate | undefined, sq: SqueezeThresholds): Position {
  const avgPrice = order.price ?? cand?.last ?? 1;
  const pctChange = cand?.pctChange ?? 40;
  const priorClose = Number((avgPrice / (1 + pctChange / 100)).toFixed(2));
  const rvol = cand?.rvol ?? 5;
  const floatM = cand?.floatM ?? 20;
  const borrowFeePct = cand?.borrowFeePct ?? 50;
  const intradayGainPct = ((avgPrice - priorClose) / priorClose) * 100;
  return {
    id: `p-${order.symbol}-${order.id}`,
    symbol: order.symbol,
    shortQty: order.qty,
    avgPrice,
    last: avgPrice,
    priorClose,
    pctFromEntry: 0,
    unrealizedPnl: 0,
    stopPrice: stopFor(avgPrice),
    borrowFeePct,
    rvol,
    floatM,
    guardState: evaluateGuard({ intradayGainPct, rvol, borrowFeePct, floatM, adverseMovePct: 0 }, sq),
  };
}

// One pure tick. `tickSeed` makes it deterministic in tests. Frozen when halted
// (kill switch) or paused (sim clock). Emits real log events for every state
// transition it causes (force-exit, fill, locate resolve, auto-entry, new in-play).
export function tickStep(state: AppState, tickSeed: number): AppState {
  if (state.account.halted || state.account.paused) return state;
  const rng = makeRng(tickSeed);
  const now = Date.now();
  const sq = state.config.squeeze;
  const events: LogEvent[] = [];

  // 1. drift + re-evaluate guard on open positions
  let positions: Position[] = state.positions.map((p) => {
    const last = drift(rng, p.last, 0.04);
    const intradayGainPct = ((last - p.priorClose) / p.priorClose) * 100;
    return {
      ...p,
      last,
      pctFromEntry: Number(shortPctFromEntry(p.avgPrice, last).toFixed(2)),
      unrealizedPnl: Math.round(shortUnrealized(p.avgPrice, last, p.shortQty)),
      guardState: evaluateGuard(
        { intradayGainPct, rvol: p.rvol, borrowFeePct: p.borrowFeePct, floatM: p.floatM, adverseMovePct: adverseMovePct(p.avgPrice, last) },
        sq
      ),
    };
  });

  // 2. force-exit on stop-hit or guard EXIT; book realized P&L
  let realizedPnl = state.account.realizedPnl;
  const exitedSymbols = new Set<string>();
  positions = positions.filter((p) => {
    const stopHit = p.last >= p.stopPrice;
    if (stopHit || p.guardState === "exit") {
      realizedPnl += p.unrealizedPnl;
      exitedSymbols.add(p.symbol);
      const reason = stopHit ? "stop hit" : "squeeze force-exit";
      events.push(makeLogEvent(now, "GUARD", `${p.symbol} ${reason} — buy-to-cover ${p.shortQty.toLocaleString()}`));
      events.push(makeLogEvent(now, "EXIT", `cover ${p.symbol} ${p.shortQty.toLocaleString()} @ ${p.last.toFixed(2)}`, p.unrealizedPnl));
      return false;
    }
    return true;
  });

  // 3. advance orders; fills open positions (+ attach stop); locate resolves -> log;
  //    drop protective stops whose position just exited
  const orders: Order[] = [];
  for (const o of state.orders) {
    if (o.type === "STP" && exitedSymbols.has(o.symbol)) continue;
    const adv = advanceOrder(o, DT, rng);
    if (adv.status === "filled") {
      if (adv.side === "SHORT") {
        const cand = state.candidates.find((c) => c.symbol === adv.symbol);
        const existing = positions.find((p) => p.symbol === adv.symbol);
        if (existing) {
          const totalQty = existing.shortQty + adv.qty;
          const fillPrice = adv.price ?? existing.avgPrice;
          existing.avgPrice = Number(((existing.avgPrice * existing.shortQty + fillPrice * adv.qty) / totalQty).toFixed(2));
          existing.shortQty = totalQty;
          existing.unrealizedPnl = Math.round(shortUnrealized(existing.avgPrice, existing.last, totalQty));
        } else {
          const np = positionFromFill(adv, cand, sq);
          positions.push(np);
          orders.push(attachStop(adv.symbol, np.avgPrice, adv.qty, adv.id));
          events.push(makeLogEvent(now, "ORDER", `stop ${np.stopPrice.toFixed(2)} attached on ${adv.symbol}`));
        }
        events.push(makeLogEvent(now, "FILL", `SHORT ${adv.symbol} ${adv.qty.toLocaleString()} @ ${(adv.price ?? 0).toFixed(2)}`));
      }
      // filled orders are consumed (not re-queued)
    } else {
      if (o.status === "pending-locate" && adv.status === "working") {
        events.push(makeLogEvent(now, "LOCATE", `${adv.symbol} ${adv.qty.toLocaleString()} reserved — short armed`));
      }
      orders.push(adv);
    }
  }

  // 4. drift candidates; occasionally a new name comes into play, weakest ages out
  let candidates: Candidate[] = state.candidates.map((c) => {
    const last = drift(rng, c.last, 0.05);
    const pctChange = Math.max(-20, Math.round(c.pctChange + (rng() - 0.5) * 6));
    return { ...c, last, pctChange };
  });
  if (rng() < 0.12) {
    const used = new Set([...candidates.map((c) => c.symbol), ...positions.map((p) => p.symbol)]);
    const free = symbolPool().filter((s) => !used.has(s));
    if (free.length) {
      const sym = free[Math.floor(rng() * free.length)];
      const fresh = makeCandidate(tickSeed + sym.length + 7, sym);
      candidates.push(fresh);
      events.push(makeLogEvent(now, "DATA", `${sym} now in play — +${fresh.pctChange}% on ${fresh.rvol}× RVOL`));
    }
  }
  candidates.sort((a, b) => b.compositeScore - a.compositeScore);
  if (candidates.length > MAX_CANDIDATES) candidates = candidates.slice(0, MAX_CANDIDATES);

  // 5. occasional auto-entry on the strongest borrowable candidate (keeps the book live)
  const openExposure = positions.length;
  if (rng() < 0.18) {
    const acctNow = recomputeAccount({ ...state.account, realizedPnl }, positions, state.account.startEquity);
    const target = candidates.find(
      (c) => c.locate.ok && !positions.some((p) => p.symbol === c.symbol) && !orders.some((o) => o.symbol === c.symbol)
    );
    if (target && canEnter(target, acctNow, state.config.breakers, openExposure).ok) {
      const qty = shortQtyFor(target, acctNow, state.config.breakers);
      orders.push(makeShortOrder(target, qty, `${tickSeed}`));
      events.push(makeLogEvent(now, "SIGNAL", `${target.symbol} score ${target.compositeScore.toFixed(2)} — auto-short ${qty.toLocaleString()} @ ${target.last.toFixed(2)}`));
    }
  }

  // 6. ambient flavor line if nothing else happened, so the log always flows
  if (events.length === 0 && rng() < 0.4) {
    events.push(randomLogLine(tickSeed + 1, now));
  }

  // 6b. step the L2 microstructure sim for the focused in-play name
  const focusSym = candidates[0]?.symbol ?? positions[0]?.symbol ?? state.l2.symbol;
  const focusRef =
    candidates.find((c) => c.symbol === focusSym)?.last ??
    positions.find((p) => p.symbol === focusSym)?.last ??
    state.l2.ref;
  const l2 = state.l2.symbol === focusSym ? stepL2(state.l2, tickSeed) : initL2(focusSym, focusRef);
  const l2Eval = evaluateL2(
    l2.book, l2.tape, l2.now, positions.some((p) => p.symbol === focusSym), l2.spoof
  );

  // 7. recompute account from new positions + realized
  const account = recomputeAccount({ ...state.account, realizedPnl }, positions, state.account.startEquity);

  // 8. assemble log (newest first); measure events/min from real-time stamps
  const log = [...events, ...state.log].slice(0, CAP);
  const cutoff = now - 60000;
  const eventsPerMin = log.filter((e) => e.ts >= cutoff).length;

  return {
    ...state,
    clockMs: state.clockMs + STEP_MS,
    positions,
    candidates,
    orders,
    account,
    log,
    eventsPerMin,
    l2,
    l2Eval,
  };
}
