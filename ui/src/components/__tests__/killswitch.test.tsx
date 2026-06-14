import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../mockData/store";
import { KillSwitch } from "../KillSwitch";

describe("KillSwitch", () => {
  it("confirms then flattens, showing RESUME", () => {
    render(<StoreProvider><KillSwitch /></StoreProvider>);
    fireEvent.click(screen.getByText("KILL SWITCH"));
    fireEvent.click(screen.getByText("Confirm flatten"));
    expect(screen.getByText("RESUME")).toBeInTheDocument();
  });

  it("cancel dismisses the modal without halting", () => {
    render(<StoreProvider><KillSwitch /></StoreProvider>);
    fireEvent.click(screen.getByText("KILL SWITCH"));
    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.getByText("KILL SWITCH")).toBeInTheDocument();
  });
});
