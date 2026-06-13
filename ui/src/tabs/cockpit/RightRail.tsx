import { Panel } from "../../components/Panel";
import { StatRow } from "../../components/StatRow";
import { ProgressBar } from "../../components/ProgressBar";
import { Sparkline } from "../../components/Sparkline";
import { useStore } from "../../mockData/store";

const money = (n: number) => `${n < 0 ? "-" : "+"}$${Math.abs(Math.round(n)).toLocaleString()}`;

export function RightRail() {
  const { state } = useStore();
  const a = state.account;
  const alerts = state.positions.filter((p) => p.guardState !== "ok");

  return (
    <div className="flex flex-col gap-[10px]">
      <Panel label="DAY P&L">
        <div className="p-[10px]">
          <div className={`font-mono text-[22px] font-bold ${a.dayPnl >= 0 ? "text-up" : "text-down"}`}>{money(a.dayPnl)}</div>
          <Sparkline values={[3, 5, -2, 4, 7, a.dayPnl >= 0 ? 9 : -9]} />
        </div>
      </Panel>

      <Panel label="CIRCUIT BREAKERS">
        <div className="p-[10px] font-mono text-[9.5px] space-y-1">
          <StatRow label="Daily drawdown" value={<span className={a.drawdownPct <= state.config.breakers.dailyDrawdownLimitPct * 0.75 ? "text-warn" : "text-up"}>{a.drawdownPct.toFixed(1)}% / {state.config.breakers.dailyDrawdownLimitPct.toFixed(1)}%</span>} />
          <div className="py-1"><ProgressBar fraction={Math.abs(a.drawdownPct / state.config.breakers.dailyDrawdownLimitPct)} /></div>
          <StatRow label="Positions" value={<span className="text-strong">{a.positionsCount} / {state.config.breakers.maxPositions}</span>} />
          <StatRow label="Gross short" value={<span className="text-strong">${Math.round(a.grossShort / 1000)}k / ${Math.round(state.config.breakers.maxGrossShort / 1000)}k</span>} />
        </div>
      </Panel>

      <Panel label={`▲ SQUEEZE ALERTS · ${alerts.length}`} accent="warn">
        <div className="p-[10px] font-mono text-[9px] space-y-1">
          {alerts.length === 0 && <div className="text-muted">none</div>}
          {alerts.map((p) => (
            <div key={p.id} className="flex justify-between">
              <span className="text-strong">{p.symbol}</span>
              <span className={p.guardState === "exit" ? "text-down" : "text-warn"}>
                fee {p.borrowFeePct}% · {p.guardState === "exit" ? "EXIT" : "caution"}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel label="LOCATES RESERVED">
        <div className="p-[10px] font-mono text-[9px] text-muted space-y-1">
          {state.orders.filter((o) => o.side === "LOCATE").map((o) => (
            <div key={o.id} className="flex justify-between"><span className="text-strong">{o.symbol}</span><span>{Math.round(o.qty / 1000)}k · pending</span></div>
          ))}
          <div className="flex justify-between"><span className="text-strong">TICK</span><span>8k @ $0.03</span></div>
          <div className="flex justify-between"><span className="text-strong">PLTX</span><span>10k @ $0.02 · unused</span></div>
        </div>
      </Panel>
    </div>
  );
}
