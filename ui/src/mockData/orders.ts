import type { Order } from "./types";

// Advance one order by dt seconds. `roll` is an injected [0,1) value for determinism.
// - working LMT: roll<0.3 -> filled, roll<0.7 -> partial, else stays working
// - partial:     roll<0.6 -> filled, else stays partial (more fills)
// - pending-locate (REQ) older than 2s: roll<0.8 -> becomes working SHORT LMT
// - stop-resting: unchanged
export function advanceOrder(order: Order, dt: number, roll: () => number): Order {
  const o: Order = { ...order, ageSec: order.ageSec + dt };

  if (o.status === "stop-resting" || o.status === "filled" || o.status === "rejected") {
    return o;
  }

  if (o.status === "pending-locate") {
    if (o.ageSec >= 2 && roll() < 0.8) {
      return { ...o, side: "SHORT", type: "LMT", status: "working", filledQty: 0 };
    }
    return o;
  }

  if (o.status === "working") {
    const r = roll();
    if (r < 0.3) return { ...o, status: "filled", filledQty: o.qty };
    if (r < 0.7) {
      return { ...o, status: "partial", filledQty: Math.round(o.qty * (0.3 + r * 0.4)) };
    }
    return o;
  }

  if (o.status === "partial") {
    if (roll() < 0.6) return { ...o, status: "filled", filledQty: o.qty };
    const add = Math.round((o.qty - o.filledQty) * 0.5);
    return { ...o, filledQty: Math.min(o.qty, o.filledQty + add) };
  }

  return o;
}
