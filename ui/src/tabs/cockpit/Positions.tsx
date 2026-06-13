import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { useStore } from "../../mockData/store";
import type { Position } from "../../mockData/types";

const guardColor = (g: Position["guardState"]) =>
  g === "ok" ? "text-up" : g === "caution" ? "text-warn" : "text-down";
const guardLabel = (g: Position["guardState"]) => (g === "exit" ? "EXIT" : g);
const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

export function Positions() {
  const { state, dispatch } = useStore();
  const cols: Column<Position>[] = [
    { key: "sym", header: "SYM", render: (p) => <span className="text-strong">{p.symbol}</span> },
    { key: "qty", header: "SHORT", align: "right", render: (p) => p.shortQty.toLocaleString() },
    { key: "avg", header: "AVG", align: "right", render: (p) => p.avgPrice.toFixed(2) },
    { key: "last", header: "LAST", align: "right", render: (p) => p.last.toFixed(2) },
    { key: "pct", header: "%", align: "right", render: (p) => <span className={p.pctFromEntry >= 0 ? "text-up" : "text-down"}>{p.pctFromEntry >= 0 ? "+" : ""}{p.pctFromEntry.toFixed(1)}%</span> },
    { key: "upnl", header: "uP&L", align: "right", render: (p) => <span className={p.unrealizedPnl >= 0 ? "text-up" : "text-down"}>{money(p.unrealizedPnl)}</span> },
    { key: "stop", header: "STOP", align: "right", render: (p) => p.stopPrice.toFixed(2) },
    { key: "fee", header: "FEE", align: "right", render: (p) => `${p.borrowFeePct}%` },
    { key: "guard", header: "GUARD", align: "right", render: (p) => <span className={guardColor(p.guardState)}>{guardLabel(p.guardState)}</span> },
  ];
  return (
    <Panel label={`OPEN POSITIONS · ${state.positions.length}`}>
      <DataTable columns={cols} rows={state.positions} getKey={(p) => p.id}
        onRowClick={(p) => dispatch({ type: "COVER_POSITION", symbol: p.symbol })} />
    </Panel>
  );
}
