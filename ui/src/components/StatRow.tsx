import type { ReactNode } from "react";

export function StatRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between text-muted">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
