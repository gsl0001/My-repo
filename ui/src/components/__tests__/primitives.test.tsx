import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Panel } from "../Panel";
import { Pill } from "../Pill";
import { ProgressBar } from "../ProgressBar";
import { DataTable } from "../DataTable";

describe("primitives", () => {
  it("Panel renders label and children", () => {
    render(<Panel label="OPEN POSITIONS"><div>body</div></Panel>);
    expect(screen.getByText("OPEN POSITIONS")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("Pill renders the kind text", () => {
    render(<Pill kind="GUARD" />);
    expect(screen.getByText("GUARD")).toBeInTheDocument();
  });

  it("ProgressBar clamps without throwing", () => {
    expect(() => render(<ProgressBar fraction={2} />)).not.toThrow();
  });

  it("DataTable renders rows", () => {
    render(
      <DataTable
        columns={[{ key: "s", header: "SYM", render: (r: { s: string }) => r.s }]}
        rows={[{ s: "TICK" }]}
        getKey={(r) => r.s}
      />
    );
    expect(screen.getByText("TICK")).toBeInTheDocument();
  });
});
