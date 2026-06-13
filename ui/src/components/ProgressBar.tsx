// fraction 0..1; color shifts up -> warn -> down as it approaches 1.
export function ProgressBar({ fraction }: { fraction: number }) {
  const f = Math.max(0, Math.min(1, fraction));
  const color = f >= 0.85 ? "bg-down" : f >= 0.6 ? "bg-warn" : "bg-up";
  return (
    <div className="h-[5px] bg-edge rounded-[3px]">
      <div className={`h-full rounded-[3px] ${color}`} style={{ width: `${f * 100}%` }} />
    </div>
  );
}
