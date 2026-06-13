import { Panel } from "../../components/Panel";
import { BACKTEST, type BacktestTrade } from "./backtestData";

function EquityCurve({ values }: { values: number[] }) {
  const w = 640, h = 180, pad = 8;
  const max = Math.max(...values), min = Math.min(...values, 0);
  const x = (i: number) => pad + (i / (values.length - 1)) * (w - pad * 2);
  const y = (v: number) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);
  const line = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(values.length - 1).toFixed(1)},${h - pad} L${x(0).toFixed(1)},${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <path d={area} fill="#2dd4bf22" />
      <path d={line} fill="none" stroke="#2dd4bf" strokeWidth={1.5} />
      <line x1={pad} y1={y(0)} x2={w - pad} y2={y(0)} stroke="#141b27" strokeDasharray="3 3" />
    </svg>
  );
}

const reasonColor = (r: BacktestTrade["exitReason"]) =>
  r === "target" ? "text-up" : r === "guard" || r === "stop" ? "text-down" : "text-muted";

export function Backtest() {
  return (
    <div className="p-[10px] flex flex-col gap-[10px]">
      <Panel label="EQUITY CURVE — cumulative P&L"><div className="p-3"><EquityCurve values={BACKTEST.equityCurve} /></div></Panel>

      <Panel label="STATS">
        <div className="p-3 grid grid-cols-3 gap-3 font-mono">
          {BACKTEST.stats.map((s) => (
            <div key={s.label} className="bg-bg border border-edge rounded p-3">
              <div className="text-muted text-[9px] tracking-[1px]">{s.label.toUpperCase()}</div>
              <div className={`text-[16px] font-bold ${s.value.startsWith("−") || s.value.startsWith("-") ? "text-down" : "text-strong"}`}>{s.value}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel label="TRADES">
        <table className="w-full border-collapse font-mono text-[9.5px]">
          <thead><tr className="text-muted2 text-right">
            {["DATE", "SYM", "ENTRY", "EXIT", "P&L", "RET%", "BORROW", "HOLD", "EXIT"].map((h) => (
              <th key={h} className={`font-medium px-3 py-1 ${h === "DATE" || h === "SYM" ? "text-left" : ""}`}>{h}</th>
            ))}
          </tr></thead>
          <tbody className="text-right">
            {BACKTEST.trades.map((t, i) => (
              <tr key={i} className="border-t border-rowdiv">
                <td className="px-3 py-1 text-left">{t.date}</td>
                <td className="px-3 py-1 text-left text-strong">{t.symbol}</td>
                <td className="px-3 py-1">{t.entry.toFixed(2)}</td>
                <td className="px-3 py-1">{t.exit.toFixed(2)}</td>
                <td className={`px-3 py-1 ${t.pnl >= 0 ? "text-up" : "text-down"}`}>{t.pnl >= 0 ? "+" : "-"}${Math.abs(t.pnl)}</td>
                <td className={`px-3 py-1 ${t.retPct >= 0 ? "text-up" : "text-down"}`}>{t.retPct >= 0 ? "+" : ""}{t.retPct.toFixed(1)}%</td>
                <td className="px-3 py-1">${t.borrowCost}</td>
                <td className="px-3 py-1">{t.holdMin}m</td>
                <td className={`px-3 py-1 ${reasonColor(t.exitReason)}`}>{t.exitReason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
