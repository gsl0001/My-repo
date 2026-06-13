import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
  sortable?: boolean;
}

export type SortDir = "asc" | "desc";

export function DataTable<T>({
  columns, rows, getKey, onRowClick, sortKey, sortDir, onSort, isRowClickable,
}: {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  // optional sorting: clickable headers for columns flagged `sortable`
  sortKey?: string;
  sortDir?: SortDir;
  onSort?: (key: string) => void;
  // optional per-row clickability (defaults to: clickable if onRowClick set)
  isRowClickable?: (row: T) => boolean;
}) {
  const indicator = (key: string) => (sortKey === key ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  return (
    <table className="w-full border-collapse font-mono text-[9.5px]">
      <thead>
        <tr className="text-muted2">
          {columns.map((c) => {
            const clickable = c.sortable && onSort;
            return (
              <th
                key={c.key}
                onClick={clickable ? () => onSort!(c.key) : undefined}
                className={`font-medium px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"} ${clickable ? "cursor-pointer hover:text-body select-none" : ""} ${sortKey === c.key ? "text-accent" : ""}`}
              >
                {c.header}{indicator(c.key)}
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const clickable = onRowClick && (isRowClickable ? isRowClickable(row) : true);
          return (
            <tr
              key={getKey(row)}
              onClick={clickable ? () => onRowClick!(row) : undefined}
              className={`border-t border-rowdiv ${clickable ? "cursor-pointer hover:bg-[#0c1320]" : ""}`}
            >
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"}`}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
