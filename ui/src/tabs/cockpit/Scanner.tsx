import { useMemo, useState } from "react";
import { Panel } from "../../components/Panel";
import { DataTable, type Column, type SortDir } from "../../components/DataTable";
import { ConfirmModal } from "../../components/ConfirmModal";
import { useStore } from "../../mockData/store";
import { shortQtyFor } from "../../mockData/entry";
import type { Candidate } from "../../mockData/types";

const SORT_VALUE: Record<string, (c: Candidate) => number> = {
  last: (c) => c.last,
  chg: (c) => c.pctChange,
  rvol: (c) => c.rvol,
  fee: (c) => c.borrowFeePct,
  pump: (c) => c.pumpScore,
  dil: (c) => c.dilutionScore,
  score: (c) => c.compositeScore,
};

export function Scanner() {
  const { state, dispatch } = useStore();
  const [sortKey, setSortKey] = useState("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [borrowableOnly, setBorrowableOnly] = useState(false);
  const [target, setTarget] = useState<Candidate | null>(null);

  const rows = useMemo(() => {
    const filtered = borrowableOnly ? state.candidates.filter((c) => c.locate.ok) : state.candidates;
    const val = SORT_VALUE[sortKey] ?? SORT_VALUE.score;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => (val(a) - val(b)) * dir);
  }, [state.candidates, borrowableOnly, sortKey, sortDir]);

  const top = rows[0]?.id;
  const onSort = (key: string) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  const cols: Column<Candidate>[] = [
    { key: "sym", header: "SYM", render: (c) => <span className={c.id === top ? "text-accent" : "text-strong"}>{c.symbol}</span> },
    { key: "last", header: "LAST", align: "right", sortable: true, render: (c) => c.last.toFixed(2) },
    { key: "chg", header: "%CHG", align: "right", sortable: true, render: (c) => <span className={c.pctChange >= 0 ? "text-up" : "text-down"}>{c.pctChange >= 0 ? "+" : ""}{c.pctChange}%</span> },
    { key: "rvol", header: "RVOL", align: "right", sortable: true, render: (c) => `${c.rvol}×` },
    { key: "fee", header: "FEE", align: "right", sortable: true, render: (c) => `${c.borrowFeePct}%` },
    { key: "pump", header: "PUMP", align: "right", sortable: true, render: (c) => c.pumpScore.toFixed(2) },
    { key: "dil", header: "DIL", align: "right", sortable: true, render: (c) => c.dilutionScore.toFixed(2) },
    { key: "score", header: "SCORE", align: "right", sortable: true, render: (c) => <span className={`font-bold ${c.compositeScore >= 0.8 ? "text-accent" : c.compositeScore < 0.6 ? "text-warn" : ""}`}>{c.compositeScore.toFixed(2)}</span> },
    { key: "locate", header: "LOCATE", align: "right", render: (c) => c.locate.ok ? <span className="text-up">✓ ${c.locate.costPerShare?.toFixed(2)}</span> : <span className="text-down">✕ {c.locate.reason}</span> },
  ];

  const qtyPreview = target ? shortQtyFor(target, state.account, state.config.breakers) : 0;

  return (
    <Panel
      label="LIVE SCANNER · IN PLAY"
      right={
        <span className="flex items-center gap-3 text-[9px]">
          <label className="flex items-center gap-1 text-muted cursor-pointer select-none">
            <input type="checkbox" checked={borrowableOnly} onChange={(e) => setBorrowableOnly(e.target.checked)} />
            borrowable only
          </label>
          <span className="text-muted2">click ✓ row to short</span>
          <span className="text-accent">● streaming</span>
        </span>
      }
    >
      <DataTable
        columns={cols}
        rows={rows}
        getKey={(c) => c.id}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={onSort}
        onRowClick={(c) => { if (c.locate.ok) setTarget(c); }}
        isRowClickable={(c) => c.locate.ok}
      />
      {target && (
        <ConfirmModal
          title={`Short ${target.symbol}?`}
          body={<>Place a working SHORT for ~{qtyPreview.toLocaleString()} sh @ {target.last.toFixed(2)} (locate ${target.locate.costPerShare?.toFixed(2)}/sh). Fills into a position with an attached stop. Mock only.</>}
          confirmLabel="Place short"
          onConfirm={() => { dispatch({ type: "SHORT_CANDIDATE", symbol: target.symbol }); setTarget(null); }}
          onCancel={() => setTarget(null)}
        />
      )}
    </Panel>
  );
}
