import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../mockData/store";
import { TopBar } from "../TopBar";

describe("TopBar", () => {
  it("toggles pause/resume", () => {
    render(<StoreProvider><TopBar tab="Cockpit" onTab={() => {}} /></StoreProvider>);
    fireEvent.click(screen.getByText("⏸ Pause"));
    expect(screen.getByText("▶ Resume")).toBeInTheDocument();
    fireEvent.click(screen.getByText("▶ Resume"));
    expect(screen.getByText("⏸ Pause")).toBeInTheDocument();
  });

  it("shows a session clock", () => {
    render(<StoreProvider><TopBar tab="Cockpit" onTab={() => {}} /></StoreProvider>);
    expect(screen.getByText(/⏱/)).toBeInTheDocument();
  });
});
