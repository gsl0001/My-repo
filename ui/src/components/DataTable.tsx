import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
}

export function DataTable<T>({
  columns, rows, getKey, onRowClick,
}: {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string;
  onRowClick?: (row: T) => void;
}) {
  return (
    <table className="w-full border-collapse font-mono text-[9.5px]">
      <thead>
        <tr className="text-muted2">
          {columns.map((c) => (
            <th
              key={c.key}
              className={`font-medium px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"}`}
            >
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={getKey(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={`border-t border-rowdiv ${onRowClick ? "cursor-pointer hover:bg-[#0c1320]" : ""}`}
          >
            {columns.map((c) => (
              <td key={c.key} className={`px-3 py-1 ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
