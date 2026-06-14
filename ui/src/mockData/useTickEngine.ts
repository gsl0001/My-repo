import { useEffect, useRef } from "react";
import { tickStep } from "./tick";
import { useStore } from "./store";

// Drives the store ~once per second. Pauses automatically when halted.
export function useTickEngine(intervalMs = 1000) {
  const { state, dispatch } = useStore();
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const id = setInterval(() => {
      const cur = stateRef.current;
      if (cur.account.halted) return;
      dispatch({ type: "TICK", next: tickStep(cur, Date.now() & 0x7fffffff) });
    }, intervalMs);
    return () => clearInterval(id);
  }, [dispatch, intervalMs]);
}
