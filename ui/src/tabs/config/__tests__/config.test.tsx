import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StoreProvider } from "../../../mockData/store";
import { Config } from "../Config";

describe("Config", () => {
  it("renders the three sections", () => {
    render(<StoreProvider><Config /></StoreProvider>);
    expect(screen.getByText("UNIVERSE (§8)")).toBeInTheDocument();
    expect(screen.getByText("SQUEEZE GUARD (§9)")).toBeInTheDocument();
    expect(screen.getByText("CIRCUIT BREAKERS")).toBeInTheDocument();
  });

  it("edits a squeeze field", () => {
    render(<StoreProvider><Config /></StoreProvider>);
    const input = screen.getAllByDisplayValue("100")[0] as HTMLInputElement; // gain abort default (multiple fields may be 100)
    fireEvent.change(input, { target: { value: "80" } });
    expect((screen.getByDisplayValue("80") as HTMLInputElement)).toBeInTheDocument();
  });
});
