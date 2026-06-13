import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StoreProvider } from "../../../mockData/store";
import { Cockpit } from "../Cockpit";

describe("Cockpit", () => {
  it("renders the major panels with seed data", () => {
    render(<StoreProvider><Cockpit /></StoreProvider>);
    expect(screen.getByText(/OPEN POSITIONS/)).toBeInTheDocument();
    expect(screen.getByText(/ACTIVE ORDERS/)).toBeInTheDocument();
    expect(screen.getByText(/LIVE SCANNER/)).toBeInTheDocument();
    expect(screen.getByText("LIVE LOG")).toBeInTheDocument();
    expect(screen.getAllByText("TICK").length).toBeGreaterThan(0);
  });
});
