import { Panel } from "../../components/Panel";
import { Pill } from "../../components/Pill";
import { useStore } from "../../mockData/store";

function hhmmssms(ts: number): string {
  const d = new Date(ts);
  const p = (n: number, l = 2) => String(n).padStart(l, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

export function LiveLog() {
  const { state } = useStore();
  return (
    <Panel label="LIVE LOG" right={<span className="text-[9px] text-accent">● {state.eventsPerMin} events / min</span>} className="mx-[10px] mb-[10px]">
      <div className="px-3 py-2 font-mono text-[9px] leading-[1.7] max-h-[180px] overflow-y-auto">
        {state.log.map((e) => (
          <div key={e.id}>
            <span className="text-muted2">{hhmmssms(e.ts)}</span> <Pill kind={e.kind} /> {e.message}
            {e.pnl != null && <span className={e.pnl >= 0 ? "text-up" : "text-down"}> · {e.pnl >= 0 ? "+" : "-"}${Math.abs(e.pnl).toLocaleString()} realized</span>}
          </div>
        ))}
      </div>
    </Panel>
  );
}
