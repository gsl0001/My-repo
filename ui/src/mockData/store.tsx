import React, { createContext, useContext, useReducer } from "react";
import type { AppState, Config, Position } from "./types";
import { makeSeedState } from "./seed";
import { evaluateGuard } from "./guard";
import { adverseMovePct } from "./pnl";
import { makeLogEvent } from "./generators";

export function initialState(): AppState {
  return makeSeedState(1);
}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export type Action =
  | { type: "TICK"; next: AppState }
  | { type: "KILL" }
  | { type: "RESUME" }
  | { type: "CANCEL_ORDER"; id: string }
  | { type: "COVER_POSITION"; symbol: string }
  | { type: "UPDATE_CONFIG"; patch: DeepPartial<Config> };

const CAP = 200;

export function reEvaluateGuards(state: AppState): AppState {
  const positions = state.positions.map((p): Position => {
    const intradayGainPct = ((p.last - p.priorClose) / p.priorClose) * 100;
    return {
      ...p,
      guardState: evaluateGuard(
        {
          intradayGainPct,
          rvol: p.rvol,
          borrowFeePct: p.borrowFeePct,
          floatM: p.floatM,
          adverseMovePct: adverseMovePct(p.avgPrice, p.last),
        },
        state.config.squeeze
      ),
    };
  });
  return { ...state, positions };
}

function mergeConfig(cfg: Config, patch: DeepPartial<Config>): Config {
  return {
    universe: { ...cfg.universe, ...(patch.universe ?? {}) },
    squeeze: { ...cfg.squeeze, ...(patch.squeeze ?? {}) },
    breakers: { ...cfg.breakers, ...(patch.breakers ?? {}) },
  };
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "TICK":
      return action.next;

    case "KILL": {
      const ts = Date.now();
      const exits = state.positions.map((p) =>
        makeLogEvent(ts, "EXIT", `KILL flatten ${p.symbol} ${p.shortQty} @ ${p.last.toFixed(2)}`, p.unrealizedPnl)
      );
      const halt = makeLogEvent(ts, "HALT", "KILL SWITCH — all positions flattened, new orders halted");
      const realized = state.account.realizedPnl + state.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
      return {
        ...state,
        positions: [],
        orders: state.orders.filter((o) => o.status === "stop-resting" || o.status === "filled"),
        account: { ...state.account, halted: true, realizedPnl: realized, positionsCount: 0, grossShort: 0 },
        log: [halt, ...exits, ...state.log].slice(0, CAP),
      };
    }

    case "RESUME":
      return {
        ...state,
        account: { ...state.account, halted: false },
        log: [makeLogEvent(Date.now(), "RISK", "Trading resumed by operator"), ...state.log].slice(0, CAP),
      };

    case "CANCEL_ORDER":
      return { ...state, orders: state.orders.filter((o) => o.id !== action.id) };

    case "COVER_POSITION": {
      const pos = state.positions.find((p) => p.symbol === action.symbol);
      if (!pos) return state;
      const ts = Date.now();
      return {
        ...state,
        positions: state.positions.filter((p) => p.symbol !== action.symbol),
        account: {
          ...state.account,
          realizedPnl: state.account.realizedPnl + pos.unrealizedPnl,
          positionsCount: state.account.positionsCount - 1,
          grossShort: Math.max(0, state.account.grossShort - pos.shortQty * pos.last),
        },
        log: [makeLogEvent(ts, "EXIT", `Cover ${pos.symbol} ${pos.shortQty} @ ${pos.last.toFixed(2)}`, pos.unrealizedPnl), ...state.log].slice(0, CAP),
      };
    }

    case "UPDATE_CONFIG":
      return reEvaluateGuards({ ...state, config: mergeConfig(state.config, action.patch) });

    default:
      return state;
  }
}

interface StoreCtx {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}
const Ctx = createContext<StoreCtx | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  return <Ctx.Provider value={{ state, dispatch }}>{children}</Ctx.Provider>;
}

export function useStore(): StoreCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore must be used within StoreProvider");
  return ctx;
}
