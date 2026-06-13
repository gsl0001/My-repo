export type GuardState = "ok" | "caution" | "exit";

export interface Position {
  id: string;
  symbol: string;
  shortQty: number;
  avgPrice: number;
  last: number;
  priorClose: number;       // for intraday-gain calc
  pctFromEntry: number;     // (avg - last)/avg*100; positive = profit on a short
  unrealizedPnl: number;    // (avg - last) * shortQty
  stopPrice: number;
  borrowFeePct: number;
  rvol: number;
  floatM: number;           // float in millions of shares
  guardState: GuardState;
}

export type OrderSide = "SHORT" | "BUY" | "LOCATE";
export type OrderType = "LMT" | "STP" | "REQ";
export type OrderStatus =
  | "working"
  | "partial"
  | "stop-resting"
  | "pending-locate"
  | "filled"
  | "rejected";

export interface Order {
  id: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  qty: number;
  price: number | null;
  filledQty: number;
  ageSec: number;
  status: OrderStatus;
}

export interface LocateInfo {
  ok: boolean;
  costPerShare?: number;
  reason?: string;
}

export interface Candidate {
  id: string;
  symbol: string;
  last: number;
  pctChange: number;        // vs prior close
  rvol: number;
  floatM: number;
  borrowFeePct: number;
  pumpScore: number;        // 0..1
  dilutionScore: number;    // 0..1
  borrowScore: number;      // 0..1
  compositeScore: number;   // 0..1
  locate: LocateInfo;
}

export type LogKind =
  | "DATA" | "SIGNAL" | "GUARD" | "LOCATE"
  | "ORDER" | "FILL" | "EXIT" | "RISK" | "HALT";

export interface LogEvent {
  id: string;
  ts: number;               // epoch ms
  kind: LogKind;
  message: string;
  pnl?: number;
}

export interface Account {
  startEquity: number;
  equity: number;
  dayPnl: number;
  realizedPnl: number;
  grossShort: number;
  grossLimit: number;
  drawdownPct: number;      // <= 0, peak-to-now
  positionsCount: number;
  halted: boolean;          // kill switch engaged (flat + no new orders)
  paused: boolean;          // simulation clock frozen (state intact)
}

export interface SqueezeThresholds {
  gainCautionPct: number;   // default 50
  gainAbortPct: number;     // default 100
  rvolCaution: number;      // default 5
  rvolAbort: number;        // default 10
  feeCautionPct: number;    // default 100
  feeAbortPct: number;      // default 300
  floatCautionM: number;    // default 20
  floatAbortM: number;      // default 5
  adverseExitPct: number;   // default 15
}

export interface UniverseParams {
  capMinM: number;          // 10
  capMaxM: number;          // 500
  priceFloor: number;       // 1
  priceCeiling: number;     // 25
  minDollarVolM: number;    // 3
  minAdvK: number;          // 500
  lowFloatFlagM: number;    // 20
  maxBorrowFeeSoftPct: number; // 100
  maxBorrowFeeHardPct: number; // 300
}

export interface CircuitBreakers {
  perPositionMaxLossPct: number; // 18
  dailyDrawdownLimitPct: number; // -4
  maxPositions: number;          // 6
  maxGrossShort: number;         // 150000
}

export interface Config {
  universe: UniverseParams;
  squeeze: SqueezeThresholds;
  breakers: CircuitBreakers;
}

export interface AppState {
  positions: Position[];
  orders: Order[];
  candidates: Candidate[];
  log: LogEvent[];          // newest first, capped
  account: Account;
  config: Config;
  eventsPerMin: number;
  clockMs: number;          // simulated session clock (epoch ms)
}
