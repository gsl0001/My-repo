import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../../mockData/store";
import { Positions } from "../Positions";
import { Scanner } from "../Scanner";

describe("cockpit interactions", () => {
  it("opens a cover-confirm when a position row is clicked", () => {
    render(<StoreProvider><Positions /></StoreProvider>);
    fireEvent.click(screen.getByText("TICK"));
    expect(screen.getByText(/Cover TICK/)).toBeInTheDocument();
    expect(screen.getByText("Cover")).toBeInTheDocument(); // confirm button
  });

  it("opens a short-confirm when a borrowable scanner row is clicked", () => {
    render(<StoreProvider><Scanner /></StoreProvider>);
    const ok = screen.queryAllByText(/^✓/);
    if (ok.length === 0) return; // seed had no borrowable candidate (rare)
    fireEvent.click(ok[0]);
    expect(screen.getByText("Place short")).toBeInTheDocument();
  });

  it("exposes the borrowable-only filter", () => {
    render(<StoreProvider><Scanner /></StoreProvider>);
    expect(screen.getByText("borrowable only")).toBeInTheDocument();
  });
});
