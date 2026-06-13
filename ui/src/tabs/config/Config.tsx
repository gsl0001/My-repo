import { Panel } from "../../components/Panel";
import { useStore } from "../../mockData/store";
import { defaultUniverse, defaultBreakers } from "../../mockData/config-defaults";
import { defaultSqueeze } from "../../mockData/guard";

function NumField({ label, value, hint, onChange }: { label: string; value: number; hint?: string; onChange: (n: number) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 py-[5px]">
      <span className="text-muted" title={hint}>{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 bg-bg border border-edge rounded px-2 py-1 font-mono text-right text-strong focus:border-accent outline-none"
      />
    </label>
  );
}

export function Config() {
  const { state, dispatch } = useStore();
  const { universe, squeeze, breakers } = state.config;
  const u = (patch: Partial<typeof universe>) => dispatch({ type: "UPDATE_CONFIG", patch: { universe: patch } });
  const s = (patch: Partial<typeof squeeze>) => dispatch({ type: "UPDATE_CONFIG", patch: { squeeze: patch } });
  const b = (patch: Partial<typeof breakers>) => dispatch({ type: "UPDATE_CONFIG", patch: { breakers: patch } });

  const reset = () =>
    dispatch({ type: "UPDATE_CONFIG", patch: { universe: defaultUniverse, squeeze: defaultSqueeze, breakers: defaultBreakers } });

  return (
    <div className="p-[10px] grid grid-cols-3 gap-[10px] items-start">
      <Panel label="UNIVERSE (§8)">
        <div className="p-3 text-[11px]">
          <NumField label="Market cap min ($M)" value={universe.capMinM} onChange={(n) => u({ capMinM: n })} />
          <NumField label="Market cap max ($M)" value={universe.capMaxM} onChange={(n) => u({ capMaxM: n })} />
          <NumField label="Price floor" value={universe.priceFloor} onChange={(n) => u({ priceFloor: n })} />
          <NumField label="Price ceiling" value={universe.priceCeiling} onChange={(n) => u({ priceCeiling: n })} />
          <NumField label="Min $ vol (20d, $M)" value={universe.minDollarVolM} onChange={(n) => u({ minDollarVolM: n })} />
          <NumField label="Min ADV (k sh)" value={universe.minAdvK} onChange={(n) => u({ minAdvK: n })} />
          <NumField label="Low-float flag (<M sh)" value={universe.lowFloatFlagM} onChange={(n) => u({ lowFloatFlagM: n })} />
          <NumField label="Max borrow fee soft (%)" value={universe.maxBorrowFeeSoftPct} onChange={(n) => u({ maxBorrowFeeSoftPct: n })} />
          <NumField label="Max borrow fee hard (%)" value={universe.maxBorrowFeeHardPct} onChange={(n) => u({ maxBorrowFeeHardPct: n })} />
        </div>
      </Panel>

      <Panel label="SQUEEZE GUARD (§9)">
        <div className="p-3 text-[11px]">
          <NumField label="Gain caution (%)" hint="reduce size above this intraday gain" value={squeeze.gainCautionPct} onChange={(n) => s({ gainCautionPct: n })} />
          <NumField label="Gain abort/force-exit (%)" value={squeeze.gainAbortPct} onChange={(n) => s({ gainAbortPct: n })} />
          <NumField label="RVOL caution (×)" value={squeeze.rvolCaution} onChange={(n) => s({ rvolCaution: n })} />
          <NumField label="RVOL abort (×)" value={squeeze.rvolAbort} onChange={(n) => s({ rvolAbort: n })} />
          <NumField label="Borrow fee caution (%)" value={squeeze.feeCautionPct} onChange={(n) => s({ feeCautionPct: n })} />
          <NumField label="Borrow fee abort (%)" value={squeeze.feeAbortPct} onChange={(n) => s({ feeAbortPct: n })} />
          <NumField label="Float caution (<M sh)" value={squeeze.floatCautionM} onChange={(n) => s({ floatCautionM: n })} />
          <NumField label="Float abort (<M sh)" value={squeeze.floatAbortM} onChange={(n) => s({ floatAbortM: n })} />
          <NumField label="Adverse-move exit (%)" hint="force-exit when this far against entry" value={squeeze.adverseExitPct} onChange={(n) => s({ adverseExitPct: n })} />
          <p className="text-muted2 text-[10px] mt-2">Lowering abort thresholds flips more cockpit positions to EXIT on the next tick.</p>
        </div>
      </Panel>

      <Panel label="CIRCUIT BREAKERS">
        <div className="p-3 text-[11px]">
          <NumField label="Per-position max loss (%)" value={breakers.perPositionMaxLossPct} onChange={(n) => b({ perPositionMaxLossPct: n })} />
          <NumField label="Daily drawdown limit (%)" value={breakers.dailyDrawdownLimitPct} onChange={(n) => b({ dailyDrawdownLimitPct: n })} />
          <NumField label="Max concurrent positions" value={breakers.maxPositions} onChange={(n) => b({ maxPositions: n })} />
          <NumField label="Max gross short ($)" value={breakers.maxGrossShort} onChange={(n) => b({ maxGrossShort: n })} />
          <button onClick={reset} className="mt-3 w-full border border-edge rounded px-3 py-[6px] text-accent hover:bg-[#0c1320]">
            Reset to design defaults
          </button>
        </div>
      </Panel>
    </div>
  );
}
