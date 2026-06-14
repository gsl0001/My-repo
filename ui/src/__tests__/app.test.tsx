import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import App from "../App";

describe("App", () => {
  it("switches tabs", () => {
    render(<App />);
    expect(screen.getByText(/OPEN POSITIONS/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Backtest"));
    expect(screen.getByText(/EQUITY CURVE/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Config"));
    expect(screen.getByText("UNIVERSE (§8)")).toBeInTheDocument();
  });
});
