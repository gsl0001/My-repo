import { useState } from "react";
import { useStore } from "../mockData/store";

export function KillSwitch() {
  const { state, dispatch } = useStore();
  const [confirming, setConfirming] = useState(false);

  if (state.account.halted) {
    return (
      <button
        onClick={() => dispatch({ type: "RESUME" })}
        className="bg-up text-black font-extrabold tracking-[0.5px] rounded-md px-3 py-[5px]"
      >
        RESUME
      </button>
    );
  }

  return (
    <>
      <button
        onClick={() => setConfirming(true)}
        className="bg-down text-white font-extrabold tracking-[0.5px] rounded-md px-3 py-[5px]"
      >
        KILL&nbsp;SWITCH
      </button>
      {confirming && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-panel border border-down rounded-lg p-5 w-[340px]">
            <div className="text-strong font-bold mb-1">Flatten everything?</div>
            <div className="text-muted text-[12px] mb-4">
              Closes all positions, cancels working orders, and halts new orders. Mock state only.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirming(false)} className="px-3 py-[5px] rounded-md border border-edge text-body">
                Cancel
              </button>
              <button
                onClick={() => { dispatch({ type: "KILL" }); setConfirming(false); }}
                className="px-3 py-[5px] rounded-md bg-down text-white font-bold"
              >
                Confirm flatten
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
