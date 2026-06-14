import { useState } from "react";
import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { ConfirmModal } from "../../components/ConfirmModal";
import { useStore } from "../../mockData/store";
import type { Order, OrderStatus } from "../../mockData/types";

const STATUS: Record<OrderStatus, { dot: string; label: string; cls: string }> = {
  working: { dot: "●", label: "working", cls: "text-info" },
  partial: { dot: "◐", label: "partial", cls: "text-warn" },
  "stop-resting": { dot: "◇", label: "stop resting", cls: "text-muted" },
  "pending-locate": { dot: "⧗", label: "pending locate", cls: "text-violet" },
  filled: { dot: "✓", label: "filled", cls: "text-up" },
  rejected: { dot: "✕", label: "rejected", cls: "text-down" },
};
const sideColor = (s: Order["side"]) => (s === "SHORT" ? "text-down" : s === "BUY" ? "text-up" : "text-violet");
const cancellable = (o: Order) => o.status === "working" || o.status === "partial";

export function ActiveOrders() {
  const { state, dispatch } = useStore();
  const [target, setTarget] = useState<Order | null>(null);

  const cols: Column<Order>[] = [
    { key: "sym", header: "SYM", render: (o) => <span className="text-strong">{o.symbol}</span> },
    { key: "side", header: "SIDE", align: "right", render: (o) => <span className={sideColor(o.side)}>{o.side}</span> },
    { key: "type", header: "TYPE", align: "right", render: (o) => o.type },
    { key: "qty", header: "QTY", align: "right", render: (o) => o.qty.toLocaleString() },
    { key: "price", header: "PRICE", align: "right", render: (o) => (o.price == null ? "—" : o.price.toFixed(2)) },
    { key: "filled", header: "FILLED", align: "right", render: (o) => (o.status === "stop-resting" ? "—" : `${o.filledQty.toLocaleString()}/${o.qty.toLocaleString()}`) },
    { key: "age", header: "AGE", align: "right", render: (o) => (o.ageSec >= 60 ? `${Math.floor(o.ageSec / 60)}m` : `${o.ageSec}s`) },
    { key: "status", header: "STATUS", align: "right", render: (o) => <span className={STATUS[o.status].cls}>{STATUS[o.status].dot} {STATUS[o.status].label}</span> },
  ];

  return (
    <Panel label={`ACTIVE ORDERS · ${state.orders.length}`} accent="info"
      right={<span className="text-[9px] text-muted2">Reg SHO: no short w/o locate</span>}>
      <DataTable columns={cols} rows={state.orders} getKey={(o) => o.id}
        onRowClick={(o) => { if (cancellable(o)) setTarget(o); }} />
      {target && (
        <ConfirmModal
          title={`Cancel order — ${target.symbol}?`}
          body={<>Cancel the {target.status} {target.side} {target.qty.toLocaleString()} @ {target.price?.toFixed(2)}. Mock only.</>}
          confirmLabel="Cancel order"
          danger
          onConfirm={() => { dispatch({ type: "CANCEL_ORDER", id: target.id }); setTarget(null); }}
          onCancel={() => setTarget(null)}
        />
      )}
    </Panel>
  );
}
