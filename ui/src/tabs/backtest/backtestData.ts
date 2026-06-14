export interface BacktestTrade {
  date: string; symbol: string; side: "SHORT";
  entry: number; exit: number; pnl: number; retPct: number;
  borrowCost: number; holdMin: number; exitReason: "target" | "stop" | "time" | "guard";
}

export interface BacktestResult {
  equityCurve: number[];      // cumulative P&L points
  stats: { label: string; value: string }[];
  trades: BacktestTrade[];
}

// Deterministic sample result set (no live engine).
export const BACKTEST: BacktestResult = {
  equityCurve: [0, 320, 180, 640, 900, 760, 1180, 1020, 1480, 1320, 1760, 2040, 1880, 2360, 2720, 2540, 3010, 3320],
  stats: [
    { label: "Total P&L", value: "+$3,320" },
    { label: "Win rate", value: "58%" },
    { label: "Profit factor", value: "1.74" },
    { label: "Max drawdown", value: "−$420" },
    { label: "Sharpe", value: "1.9" },
    { label: "Avg hold", value: "26m" },
    { label: "Avg borrow cost", value: "$0.03/sh" },
    { label: "Slippage drag", value: "−$610" },
    { label: "# trades", value: "84" },
  ],
  trades: [
    { date: "06-03", symbol: "PLTX", side: "SHORT", entry: 3.9, exit: 3.4, pnl: 980, retPct: 12.8, borrowCost: 42, holdMin: 22, exitReason: "target" },
    { date: "06-04", symbol: "GNSX", side: "SHORT", entry: 2.3, exit: 2.6, pnl: -420, retPct: -13.0, borrowCost: 88, holdMin: 9, exitReason: "guard" },
    { date: "06-05", symbol: "MULN", side: "SHORT", entry: 1.5, exit: 1.32, pnl: 540, retPct: 12.0, borrowCost: 17, holdMin: 41, exitReason: "time" },
    { date: "06-06", symbol: "CABL", side: "SHORT", entry: 7.6, exit: 7.1, pnl: 750, retPct: 6.6, borrowCost: 23, holdMin: 33, exitReason: "target" },
    { date: "06-09", symbol: "BBLG", side: "SHORT", entry: 2.1, exit: 2.0, pnl: 120, retPct: 4.8, borrowCost: 51, holdMin: 18, exitReason: "stop" },
  ],
};
