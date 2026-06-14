import type { GuardState, SqueezeThresholds } from "./types";

export const defaultSqueeze: SqueezeThresholds = {
  gainCautionPct: 50,
  gainAbortPct: 100,
  rvolCaution: 5,
  rvolAbort: 10,
  feeCautionPct: 100,
  feeAbortPct: 300,
  floatCautionM: 20,
  floatAbortM: 5,
  adverseExitPct: 15,
};

export interface GuardInput {
  intradayGainPct: number;  // stock gain vs prior close
  rvol: number;
  borrowFeePct: number;
  floatM: number;
  adverseMovePct: number;   // positive = price moved against the short since entry
}

// Force-exit dominates; otherwise caution; otherwise ok.
export function evaluateGuard(i: GuardInput, t: SqueezeThresholds): GuardState {
  const exit =
    i.adverseMovePct >= t.adverseExitPct ||
    i.intradayGainPct >= t.gainAbortPct ||
    i.rvol >= t.rvolAbort ||
    i.borrowFeePct >= t.feeAbortPct;
  if (exit) return "exit";

  const caution =
    i.intradayGainPct >= t.gainCautionPct ||
    i.rvol >= t.rvolCaution ||
    i.borrowFeePct >= t.feeCautionPct ||
    i.floatM <= t.floatCautionM;
  return caution ? "caution" : "ok";
}
