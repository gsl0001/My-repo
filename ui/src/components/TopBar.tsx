import { useStore } from "../mockData/store";
import { KillSwitch } from "./KillSwitch";

const TABS = ["Cockpit", "Config", "Backtest"] as const;
export type TabName = (typeof TABS)[number];

function clock(ms: number): string {
  const d = new Date(ms);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

export function TopBar({ tab, onTab }: { tab: TabName; onTab: (t: TabName) => void }) {
  const { state, dispatch } = useStore();
  const a = state.account;
  const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

  return (
    <div className="flex items-center gap-[18px] px-[14px] py-[9px] bg-bar border-b border-edge">
      <span className="font-extrabold tracking-[0.5px] text-strong">
        ⚡ LOWCAP<span className="text-accent">SHORT</span>
      </span>
      {TABS.map((t) => (
        <button
          key={t}
          onClick={() => onTab(t)}
          className={t === tab ? "text-accent border-b-2 border-accent pb-[7px] -mb-[9px]" : "text-muted"}
        >
          {t}
        </button>
      ))}
      <div className="ml-auto flex items-center gap-4 font-mono">
        <span className={`text-muted ${a.paused ? "text-warn" : ""}`} title="Simulated session clock">
          ⏱ {clock(state.clockMs)}{a.paused ? " PAUSED" : ""}
        </span>
        <span className="text-muted">EQUITY <span className="text-strong">${Math.round(a.equity).toLocaleString()}</span></span>
        <span className="text-muted">DAY <span className={`font-bold ${a.dayPnl >= 0 ? "text-up" : "text-down"}`}>{money(a.dayPnl)}</span></span>
        <span className="text-muted">GROSS <span className="text-strong">${Math.round(a.grossShort / 1000)}k</span>/{Math.round(a.grossLimit / 1000)}k</span>
        <button
          onClick={() => dispatch({ type: "TOGGLE_PAUSE" })}
          className="rounded-md px-3 py-[5px] border border-edge text-body hover:bg-[#0c1320]"
        >
          {a.paused ? "▶ Resume" : "⏸ Pause"}
        </button>
        <KillSwitch />
      </div>
    </div>
  );
}
