import React, { createContext, useContext, useEffect, useReducer } from "react";
import type { AppState, Config, Position } from "./types";
import { makeSeedState } from "./seed";
import { evaluateGuard } from "./guard";
import { adverseMovePct } from "./pnl";
import { makeLogEvent } from "./generators";
import { recomputeAccount } from "./account";
import { canEnter, shortQtyFor, makeShortOrder } from "./entry";
import { loadConfig, saveConfig } from "./persist";

export function initialState(): AppState {
  return makeSeedState(1);
}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export type Action =
  | { type: "TICK"; next: AppState }
  | { type: "KILL" }
  | { type: "RESUME" }
  | { type: "TOGGLE_PAUSE" }
  | { type: "CANCEL_ORDER"; id: string }
  | { type: "COVER_POSITION"; symbol: string }
  | { type: "SHORT_CANDIDATE"; symbol: string }
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
        makeLogEvent(ts, "EXIT", `KILL flatten ${p.symbol} ${p.shortQty.toLocaleString()} @ ${p.last.toFixed(2)}`, p.unrealizedPnl)
      );
      const halt = makeLogEvent(ts, "HALT", "KILL SWITCH — all positions flattened, new orders halted");
      const realizedPnl = state.account.realizedPnl + state.positions.reduce((s, p) => s + p.unrealizedPnl, 0);
      // flatten positions and cancel every order (working + protective stops)
      const account = recomputeAccount({ ...state.account, realizedPnl, halted: true }, [], state.account.startEquity);
      return {
        ...state,
        positions: [],
        orders: [],
        account,
        log: [halt, ...exits, ...state.log].slice(0, CAP),
      };
    }

    case "RESUME":
      return {
        ...state,
        account: { ...state.account, halted: false },
        log: [makeLogEvent(Date.now(), "RISK", "Trading resumed by operator"), ...state.log].slice(0, CAP),
      };

    case "TOGGLE_PAUSE":
      return {
        ...state,
        account: { ...state.account, paused: !state.account.paused },
        log: [
          makeLogEvent(Date.now(), "RISK", state.account.paused ? "Simulation resumed" : "Simulation paused"),
          ...state.log,
        ].slice(0, CAP),
      };

    case "CANCEL_ORDER":
      return { ...state, orders: state.orders.filter((o) => o.id !== action.id) };

    case "COVER_POSITION": {
      const pos = state.positions.find((p) => p.symbol === action.symbol);
      if (!pos) return state;
      const ts = Date.now();
      const positions = state.positions.filter((p) => p.symbol !== action.symbol);
      const realizedPnl = state.account.realizedPnl + pos.unrealizedPnl;
      const account = recomputeAccount({ ...state.account, realizedPnl }, positions, state.account.startEquity);
      // cancel the now-orphaned protective stop for this symbol
      const orders = state.orders.filter((o) => !(o.symbol === pos.symbol && o.type === "STP"));
      return {
        ...state,
        positions,
        orders,
        account,
        log: [makeLogEvent(ts, "EXIT", `Cover ${pos.symbol} ${pos.shortQty.toLocaleString()} @ ${pos.last.toFixed(2)}`, pos.unrealizedPnl), ...state.log].slice(0, CAP),
      };
    }

    case "SHORT_CANDIDATE": {
      const ts = Date.now();
      const c = state.candidates.find((x) => x.symbol === action.symbol);
      if (!c) return state;
      const openExposure = state.positions.length;
      const gate = canEnter(c, state.account, state.config.breakers, openExposure);
      if (!gate.ok) {
        return {
          ...state,
          log: [makeLogEvent(ts, "RISK", `SHORT ${c.symbol} blocked — ${gate.reason}`), ...state.log].slice(0, CAP),
        };
      }
      const qty = shortQtyFor(c, state.account, state.config.breakers);
      const order = makeShortOrder(c, qty, `${ts}`);
      const events = [
        makeLogEvent(ts, "ORDER", `SHORT ${c.symbol} ${qty.toLocaleString()} @ ${c.last.toFixed(2)} (working)`),
        makeLogEvent(ts, "LOCATE", `${c.symbol} ${qty.toLocaleString()} reserved @ $${(c.locate.costPerShare ?? 0).toFixed(2)}/sh`),
      ];
      return { ...state, orders: [order, ...state.orders], log: [...events, ...state.log].slice(0, CAP) };
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
  const [state, dispatch] = useReducer(reducer, undefined, () => {
    const base = initialState();
    const saved = loadConfig();
    return saved ? reEvaluateGuards({ ...base, config: saved }) : base;
  });

  // Persist config edits so tuning survives a reload.
  useEffect(() => {
    saveConfig(state.config);
  }, [state.config]);

  return <Ctx.Provider value={{ state, dispatch }}>{children}</Ctx.Provider>;
}

export function useStore(): StoreCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore must be used within StoreProvider");
  return ctx;
}
