import { Positions } from "./Positions";
import { ActiveOrders } from "./ActiveOrders";
import { Scanner } from "./Scanner";
import { RightRail } from "./RightRail";
import { LiveLog } from "./LiveLog";
import { useStore } from "../../mockData/store";

export function Cockpit() {
  const { state } = useStore();
  return (
    <div>
      {state.account.halted && (
        <div className="bg-down/20 border border-down text-down font-bold text-center py-2">
          TRADING HALTED — kill switch engaged. Press RESUME to re-arm.
        </div>
      )}
      <div className="grid grid-cols-[2fr_1fr] gap-[10px] p-[10px]">
        <div className="flex flex-col gap-[10px]">
          <Positions />
          <ActiveOrders />
          <Scanner />
        </div>
        <RightRail />
      </div>
      <LiveLog />
    </div>
  );
}
