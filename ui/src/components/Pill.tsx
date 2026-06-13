import type { LogKind } from "../mockData/types";

const KIND_STYLE: Record<LogKind, string> = {
  DATA: "bg-[#0e2a33] text-accent",
  SIGNAL: "bg-[#101f2e] text-info",
  GUARD: "bg-[#2a2110] text-warn",
  LOCATE: "bg-[#1e1530] text-violet",
  ORDER: "bg-[#0f1b2a] text-info2",
  FILL: "bg-[#0c2417] text-up",
  EXIT: "bg-[#2a1414] text-down",
  RISK: "bg-[#2a1414] text-down",
  HALT: "bg-down text-white",
};

export function Pill({ kind }: { kind: LogKind }) {
  return (
    <span className={`px-[5px] rounded-[3px] ${KIND_STYLE[kind]}`}>{kind}</span>
  );
}
