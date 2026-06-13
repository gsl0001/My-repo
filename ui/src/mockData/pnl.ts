export function shortUnrealized(avg: number, last: number, qty: number): number {
  return (avg - last) * qty;
}

export function shortPctFromEntry(avg: number, last: number): number {
  return ((avg - last) / avg) * 100;
}

// Positive number = how far price has moved against the short (price above entry).
export function adverseMovePct(avg: number, last: number): number {
  return Math.max(0, ((last - avg) / avg) * 100);
}
