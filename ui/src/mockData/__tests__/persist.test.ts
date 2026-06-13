import { describe, it, expect, beforeEach } from "vitest";
import { loadConfig, saveConfig, clearConfig, mergeConfigWithDefaults } from "../persist";
import { defaultUniverse, defaultBreakers } from "../config-defaults";
import { defaultSqueeze } from "../guard";

describe("config persistence", () => {
  beforeEach(() => clearConfig());

  it("returns null when nothing is stored", () => {
    expect(loadConfig()).toBeNull();
  });

  it("round-trips a saved config", () => {
    const cfg = { universe: defaultUniverse, squeeze: { ...defaultSqueeze, gainAbortPct: 42 }, breakers: defaultBreakers };
    saveConfig(cfg);
    expect(loadConfig()?.squeeze.gainAbortPct).toBe(42);
  });

  it("fills missing fields from defaults (forward-compatible)", () => {
    const merged = mergeConfigWithDefaults({ squeeze: { gainAbortPct: 7 } as never });
    expect(merged.squeeze.gainAbortPct).toBe(7);
    expect(merged.squeeze.rvolAbort).toBe(defaultSqueeze.rvolAbort);
    expect(merged.universe.capMinM).toBe(defaultUniverse.capMinM);
  });

  it("clearConfig removes the stored value", () => {
    saveConfig({ universe: defaultUniverse, squeeze: defaultSqueeze, breakers: defaultBreakers });
    clearConfig();
    expect(loadConfig()).toBeNull();
  });
});
