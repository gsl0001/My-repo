import { useState } from "react";
import { useStore } from "../mockData/store";
import { ConfirmModal } from "./ConfirmModal";

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
        <ConfirmModal
          title="Flatten everything?"
          body="Closes all positions, cancels working orders, and halts new orders. Mock state only."
          confirmLabel="Confirm flatten"
          danger
          onConfirm={() => { dispatch({ type: "KILL" }); setConfirming(false); }}
          onCancel={() => setConfirming(false)}
        />
      )}
    </>
  );
}
