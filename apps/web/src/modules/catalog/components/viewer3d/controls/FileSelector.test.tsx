import "@/locales/i18n";

import { afterEach, describe, it, expect } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FileSelector } from "./FileSelector";
import type { StlFile } from "../types";

afterEach(() => cleanup());

const m = "11111111-1111-1111-1111-111111111111";
const files: StlFile[] = [
  { id: "a", modelId: m, name: "alpha.stl", size: 1000 },
  { id: "b", modelId: m, name: "bravo.stl", size: 2000 },
  { id: "c", modelId: m, name: "charlie.stl", size: 3000 },
];

describe("FileSelector", () => {
  it("renders trigger with active file name and position", () => {
    render(<FileSelector files={files} activeId="b" onSelect={() => {}} />);
    expect(screen.getByText("bravo.stl")).toBeTruthy();
    expect(screen.getByText("2 / 3")).toBeTruthy();
  });

  it("opens dropdown and lists all files when trigger clicked", async () => {
    const user = userEvent.setup();
    render(<FileSelector files={files} activeId="a" onSelect={() => {}} />);
    await user.click(screen.getByRole("button", { name: /alpha\.stl/i }));
    // active row + listed rows: alpha appears twice (in trigger + list).
    expect(screen.getAllByText("alpha.stl").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("bravo.stl")).toBeTruthy();
    expect(screen.getByText("charlie.stl")).toBeTruthy();
  });

  it("filters list by search query", async () => {
    const user = userEvent.setup();
    render(<FileSelector files={files} activeId="a" onSelect={() => {}} />);
    await user.click(screen.getByRole("button", { name: /alpha\.stl/i }));
    const search = screen.getByPlaceholderText(/filtruj|filter/i);
    await user.type(search, "char");
    // alpha still appears in the trigger but not the list — listbox should only
    // contain charlie now.
    const list = screen.getByRole("listbox");
    expect(list.querySelectorAll('[role="option"]').length).toBe(1);
    expect(list.textContent).toContain("charlie.stl");
  });

  it("invokes onSelect with id when item clicked", async () => {
    const user = userEvent.setup();
    let chosen = "";
    render(
      <FileSelector files={files} activeId="a" onSelect={(id) => (chosen = id)} />,
    );
    await user.click(screen.getByRole("button", { name: /alpha\.stl/i }));
    await user.click(screen.getByText("charlie.stl"));
    expect(chosen).toBe("c");
  });
});
