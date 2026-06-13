import { Panel } from "../../components/Panel";
import { DataTable, type Column } from "../../components/DataTable";
import { useStore } from "../../mockData/store";
import type { Candidate } from "../../mockData/types";

export function Scanner() {
  const { state } = useStore();
  const top = state.candidates[0]?.id;
  const cols: Column<Candidate>[] = [
    { key: "sym", header: "SYM", render: (c) => <span className={c.id === top ? "text-accent" : "text-strong"}>{c.symbol}</span> },
    { key: "last", header: "LAST", align: "right", render: (c) => c.last.toFixed(2) },
    { key: "chg", header: "%CHG", align: "right", render: (c) => <span className="text-up">+{c.pctChange}%</span> },
    { key: "rvol", header: "RVOL", align: "right", render: (c) => `${c.rvol}×` },
    { key: "fee", header: "FEE", align: "right", render: (c) => `${c.borrowFeePct}%` },
    { key: "pump", header: "PUMP", align: "right", render: (c) => c.pumpScore.toFixed(2) },
    { key: "dil", header: "DIL", align: "right", render: (c) => c.dilutionScore.toFixed(2) },
    { key: "score", header: "SCORE", align: "right", render: (c) => <span className={`font-bold ${c.compositeScore >= 0.8 ? "text-accent" : c.compositeScore < 0.6 ? "text-warn" : ""}`}>{c.compositeScore.toFixed(2)}</span> },
    { key: "locate", header: "LOCATE", align: "right", render: (c) => c.locate.ok ? <span className="text-up">✓ ${c.locate.costPerShare?.toFixed(2)}</span> : <span className="text-down">✕ {c.locate.reason}</span> },
  ];
  return (
    <Panel label="LIVE SCANNER · IN PLAY" right={<span className="text-[9px] text-accent">● streaming</span>}>
      <DataTable columns={cols} rows={state.candidates} getKey={(c) => c.id} />
    </Panel>
  );
}
