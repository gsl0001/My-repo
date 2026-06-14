import { useState } from "react";
import { StoreProvider } from "./mockData/store";
import { TopBar, type TabName } from "./components/TopBar";
import { CockpitWithEngine } from "./tabs/cockpit/CockpitWithEngine";
import { Config } from "./tabs/config/Config";
import { Backtest } from "./tabs/backtest/Backtest";

function Shell() {
  const [tab, setTab] = useState<TabName>("Cockpit");
  return (
    <div className="min-h-full bg-bg text-body">
      <TopBar tab={tab} onTab={setTab} />
      {tab === "Cockpit" && <CockpitWithEngine />}
      {tab === "Config" && <Config />}
      {tab === "Backtest" && <Backtest />}
    </div>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  );
}
