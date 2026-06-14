import { Cockpit } from "./Cockpit";
import { useTickEngine } from "../../mockData/useTickEngine";

export function CockpitWithEngine() {
  useTickEngine(1000);
  return <Cockpit />;
}
