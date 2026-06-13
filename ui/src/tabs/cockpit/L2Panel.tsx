import { Panel } from "../../components/Panel";
import { useStore } from "../../mockData/store";
import type { L2Level, L2SignalKind } from "../../mockData/l2";

const badge: Record<L2SignalKind, { label: string; cls: string }> = {
  enter: { label: "FADE ENTER", cls: "bg-down text-white" },
  exit: { label: "EXIT", cls: "bg-warn text-black" },
  none: { label: "watching", cls: "bg-edge text-muted" },
};

function flag(on: boolean) {
  return on ? <span className="text-accent">✓</span> : <span className="text-muted2">–</span>;
}

export function L2Panel() {
  const { state } = useStore();
  const { l2, l2Eval } = state;
  const f = l2Eval.features;
  const sig = l2Eval.signal;
  const maxSize = Math.max(1, ...l2.book.bids.map((b) => b.size), ...l2.book.asks.map((a) => a.size));
  const asks = l2.book.asks.slice(0, 5).reverse(); // worst ask on top, best ask just above spread
  const bids = l2.book.bids.slice(0, 5);

  const Row = ({ lvl, side }: { lvl: L2Level; side: "ask" | "bid" }) => (
    <div className="relative flex justify-between px-2 font-mono text-[9px] leading-[15px]">
      <div
        className={`absolute inset-y-0 right-0 ${side === "ask" ? "bg-down/15" : "bg-up/15"}`}
        style={{ width: `${(lvl.size / maxSize) * 100}%` }}
      />
      <span className={`relative z-10 ${side === "ask" ? "text-down" : "text-up"}`}>{lvl.price.toFixed(2)}</span>
      <span className="relative z-10 text-body">{lvl.size.toLocaleString()}</span>
    </div>
  );

  return (
    <Panel
      label={`L2 · ${l2.symbol}`}
      right={<span className={`text-[8px] px-[5px] rounded-[3px] ${badge[sig.kind].cls}`}>{badge[sig.kind].label}</span>}
    >
      <div className="py-1">
        {asks.map((a) => <Row key={`a${a.price}`} lvl={a} side="ask" />)}
        <div className="flex justify-between px-2 py-[2px] font-mono text-[9px] text-muted2 border-y border-rowdiv">
          <span>spread</span>
          <span>{((l2.book.asks[0]?.price ?? 0) - (l2.book.bids[0]?.price ?? 0)).toFixed(2)}</span>
        </div>
        {bids.map((b) => <Row key={`b${b.price}`} lvl={b} side="bid" />)}
      </div>
      <div className="px-2 py-[6px] border-t border-edge font-mono text-[9px] text-muted flex flex-wrap gap-x-3 gap-y-1">
        <span>imb <span className={f.imbalance >= 0 ? "text-up" : "text-down"}>{f.imbalance.toFixed(2)}</span></span>
        <span>absorb {flag(f.absorption)}</span>
        <span>sweep {flag(f.sweep)}</span>
        <span>exh {flag(f.exhaustion)}</span>
        <span>spoof {f.spoof ? <span className="text-warn">✓</span> : <span className="text-muted2">–</span>}</span>
      </div>
      {sig.reasons.length > 0 && (
        <div className="px-2 pb-2 font-mono text-[8.5px] text-muted2">{sig.reasons.join(" · ")}</div>
      )}
    </Panel>
  );
}
