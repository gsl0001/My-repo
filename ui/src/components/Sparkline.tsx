export function Sparkline({ values, height = 22 }: { values: number[]; height?: number }) {
  const max = Math.max(...values.map((v) => Math.abs(v)), 1);
  return (
    <div className="flex items-end gap-[2px]" style={{ height }}>
      {values.map((v, i) => (
        <div
          key={i}
          className={v >= 0 ? "bg-up/40" : "bg-down/40"}
          style={{ flex: 1, height: `${(Math.abs(v) / max) * 100}%` }}
        />
      ))}
    </div>
  );
}
