import type { ReactNode } from "react";

export function Panel({
  label, right, children, accent = "muted", className = "",
}: {
  label: string;
  right?: ReactNode;
  children: ReactNode;
  accent?: "muted" | "warn" | "info";
  className?: string;
}) {
  const labelColor = accent === "warn" ? "text-warn" : accent === "info" ? "text-info2" : "text-muted";
  const border = accent === "warn" ? "border-[#2a1f12]" : "border-edge";
  return (
    <div className={`bg-panel border ${border} rounded-lg ${className}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-edge">
        <span className={`text-[9px] tracking-[1px] ${labelColor}`}>{label}</span>
        {right}
      </div>
      <div>{children}</div>
    </div>
  );
}
