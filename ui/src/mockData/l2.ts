// Level 2 microstructure — a lightweight TypeScript mirror of the Python engine
// (lowcap_short_system/microstructure) for the cockpit's L2 panel. Pure feature
// functions + a synthetic depth/tape generator driven by the tick engine.
import { makeRng } from "./rng";

export interface L2Level {
  price: number;
  size: number;
}
export interface L2Book {
  symbol: string;
  bids: L2Level[]; // sorted price desc
  asks: L2Level[]; // sorted price asc
}
export interface TapePrint {
  ts: number;
  price: number;
  size: number;
  aggressor: "buy" | "sell";
}
export interface L2Features {
  imbalance: number; // [-1,1], + bid-heavy, - ask-heavy (offer pressure)
  absorption: boolean; // hidden seller absorbing buys at the ask
  sweep: boolean; // buy sweep across rising prices
  exhaustion: boolean; // tape sped up then dropped off
  spoof: boolean; // flickering fake wall present
}
export type L2SignalKind = "enter" | "exit" | "none";
export interface L2Signal {
  kind: L2SignalKind;
  strength: number; // 0..1
  reasons: string[];
}

const ENTER_IMBALANCE = 0.35;
const ABSORB_MIN_VOL = 5000;
const SWEEP_LEVELS = 3;
const TAPE_WINDOW_S = 4;
const MIN_CONVICTION = 0.6;

export function imbalance(book: L2Book, depth = 5): number {
  const weighted = (levels: L2Level[]) =>
    levels.slice(0, depth).reduce((s, lvl, i) => s + lvl.size / (i + 1), 0);
  const bw = weighted(book.bids);
  const aw = weighted(book.asks);
  return bw + aw > 0 ? (bw - aw) / (bw + aw) : 0;
}

export function sweepBuy(tape: TapePrint[], now: number): boolean {
  const recent = tape.filter((p) => p.aggressor === "buy" && now - p.ts <= 1.0);
  return new Set(recent.map((p) => p.price)).size >= SWEEP_LEVELS;
}

export function exhaustion(tape: TapePrint[], now: number): boolean {
  const win = tape.filter((p) => now - p.ts <= TAPE_WINDOW_S);
  if (win.length === 0) return false;
  const half = now - TAPE_WINDOW_S / 2;
  const first = win.filter((p) => p.ts < half).length;
  const second = win.filter((p) => p.ts >= half).length;
  return first > 0 && second <= 0.5 * first;
}

export function absorptionAtAsk(book: L2Book, tape: TapePrint[], now: number): boolean {
  const bestAsk = book.asks[0];
  if (!bestAsk) return false;
  const buyVol = tape
    .filter((p) => p.aggressor === "buy" && p.price >= bestAsk.price && now - p.ts <= TAPE_WINDOW_S)
    .reduce((s, p) => s + p.size, 0);
  // hidden seller: heavy buying lifted the ask yet the ask level is still deep (refreshed)
  return buyVol >= ABSORB_MIN_VOL && bestAsk.size >= ABSORB_MIN_VOL * 0.6;
}

export function evaluateL2(
  book: L2Book,
  tape: TapePrint[],
  now: number,
  inPosition: boolean,
  spoof: boolean
): { features: L2Features; signal: L2Signal } {
  const imb = imbalance(book);
  const sweep = sweepBuy(tape, now);
  const exh = exhaustion(tape, now);
  const absorb = absorptionAtAsk(book, tape, now);
  const features: L2Features = { imbalance: imb, absorption: absorb, sweep, exhaustion: exh, spoof };

  // exit dominates while short
  if (inPosition && sweep) {
    return { features, signal: { kind: "exit", strength: 0.8, reasons: ["up-sweep against short"] } };
  }
  // entry confirmation (vetoed by spoof)
  const reasons: string[] = [];
  let score = 0;
  if (absorb) {
    score += 0.8;
    reasons.push("hidden-seller absorption");
  }
  if (imb <= -ENTER_IMBALANCE) {
    score += Math.min(1, Math.abs(imb));
    reasons.push(`ask-heavy imbalance ${imb.toFixed(2)}`);
  }
  if (exh && sweep) {
    score += 0.7;
    reasons.push("buy exhaustion after sweep");
  }
  const confidence = spoof ? 0 : 1;
  score *= confidence;
  if (!inPosition && reasons.length > 0 && score >= MIN_CONVICTION) {
    return { features, signal: { kind: "enter", strength: Math.min(1, score), reasons } };
  }
  return { features, signal: { kind: "none", strength: 0, reasons: spoof ? ["spoofy book — vetoed"] : [] } };
}

// ---- synthetic generator (drives the cockpit panel) ----

export interface L2Sim {
  symbol: string;
  ref: number; // reference (mid) price
  book: L2Book;
  tape: TapePrint[];
  now: number;
  spoof: boolean;
}

function buildBook(rng: () => number, symbol: string, ref: number, askHeavy: boolean): L2Book {
  const tick = Math.max(0.01, Number((ref * 0.001).toFixed(2)) || 0.01);
  const lvl = (base: number, dir: number, biasUp: boolean) =>
    Array.from({ length: 6 }, (_, i) => ({
      price: Number((base + dir * tick * (i + 1)).toFixed(2)),
      size: Math.round((300 + rng() * 1700) * (biasUp ? 1.6 : 1)),
    }));
  return {
    symbol,
    bids: lvl(ref, -1, !askHeavy),
    asks: lvl(ref, +1, askHeavy),
  };
}

export function initL2(symbol: string, ref: number): L2Sim {
  const rng = makeRng(symbol.length * 131 + Math.round(ref * 100));
  return { symbol, ref, book: buildBook(rng, symbol, ref, true), tape: [], now: 0, spoof: false };
}

// Advance the L2 sim one step. `seed` keeps it deterministic in tests.
export function stepL2(sim: L2Sim, seed: number): L2Sim {
  const rng = makeRng(seed);
  const now = sim.now + 1;
  const ref = Math.max(0.5, Number((sim.ref * (1 + (rng() - 0.5) * 0.01)).toFixed(2)));
  const askHeavy = rng() < 0.6; // low-caps fading: offer pressure common
  const book = buildBook(rng, sim.symbol, ref, askHeavy);

  // tape: a burst of buys lifting the ask; occasionally a multi-price sweep
  const tape = sim.tape.filter((p) => now - p.ts <= TAPE_WINDOW_S + 1);
  const bestAsk = book.asks[0]?.price ?? ref;
  const sweeping = rng() < 0.25;
  const n = 1 + Math.floor(rng() * 4);
  for (let i = 0; i < n; i++) {
    tape.push({
      ts: now,
      price: sweeping ? Number((bestAsk + i * 0.01).toFixed(2)) : bestAsk,
      size: Math.round(800 + rng() * 4000),
      aggressor: "buy",
    });
  }
  if (sweeping) {
    // make the ask deep so it reads as absorption (hidden seller refreshing)
    book.asks[0].size = Math.round(ABSORB_MIN_VOL * (1 + rng()));
  }
  const spoof = rng() < 0.15; // occasional flickering fake wall
  return { symbol: sim.symbol, ref, book, tape, now, spoof };
}
