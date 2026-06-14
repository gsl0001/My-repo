import type { Config } from "./types";
import { defaultUniverse, defaultBreakers } from "./config-defaults";
import { defaultSqueeze } from "./guard";

const KEY = "lowcap.config.v1";

type KV = Pick<Storage, "getItem" | "setItem" | "removeItem">;

// Resilient storage: real localStorage when it works (the browser), else an
// in-memory map (jsdom without origin, private browsing, SSR). The probe avoids
// envs where localStorage exists but throws on use.
const memory: Record<string, string> = {};
const memStore: KV = {
  getItem: (k) => (k in memory ? memory[k] : null),
  setItem: (k, v) => { memory[k] = v; },
  removeItem: (k) => { delete memory[k]; },
};

function store(): KV {
  try {
    const ls = globalThis.localStorage;
    if (ls) {
      const probe = "__lc_probe__";
      ls.setItem(probe, "1");
      ls.removeItem(probe);
      return ls;
    }
  } catch {
    /* fall through to in-memory */
  }
  return memStore;
}

// Merge a (possibly partial / older-shape) stored config over current defaults,
// so newly-added fields always have a value even if the stored blob predates them.
export function mergeConfigWithDefaults(saved: Partial<Config> | null | undefined): Config {
  return {
    universe: { ...defaultUniverse, ...(saved?.universe ?? {}) },
    squeeze: { ...defaultSqueeze, ...(saved?.squeeze ?? {}) },
    breakers: { ...defaultBreakers, ...(saved?.breakers ?? {}) },
  };
}

export function loadConfig(): Config | null {
  try {
    const raw = store().getItem(KEY);
    if (!raw) return null;
    return mergeConfigWithDefaults(JSON.parse(raw) as Partial<Config>);
  } catch {
    return null;
  }
}

export function saveConfig(config: Config): void {
  try {
    store().setItem(KEY, JSON.stringify(config));
  } catch {
    /* non-fatal for a prototype */
  }
}

export function clearConfig(): void {
  try {
    store().removeItem(KEY);
  } catch {
    /* ignore */
  }
}
