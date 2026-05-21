import "@/locales/i18n";

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Vector3 } from "three";

import { MeasureSummary } from "./MeasureSummary";
import type { Measurement, Plane } from "../types";

afterEach(() => cleanup());

const fakePlane = (idTag: string): Plane => ({
  centroid: new Vector3(),
  normal: new Vector3(0, 0, 1),
  triangleIds: [Number(idTag) || 0],
  seedTriangleId: Number(idTag) || 0,
  weak: false,
});

const m1: Measurement = {
  kind: "p2p",
  id: "1",
  colorIndex: 0,
  a: new Vector3(),
  b: new Vector3(10, 0, 0),
  distanceMm: 10,
};

const m2: Measurement = {
  kind: "pl2pl",
  id: "2",
  colorIndex: 1,
  planeA: fakePlane("1"),
  planeB: fakePlane("2"),
  distanceMm: 5,
  angleDeg: 0,
  pl2plKind: "parallel",
  approximate: false,
  weakA: false,
  weakB: false,
};

describe("MeasureSummary — TB-015 host integration", () => {
  it("returns null when no measurements (no overlay obscures canvas)", () => {
    const { container } = render(
      <MeasureSummary measurements={[]} onClear={() => {}} onDelete={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the Clear button when at least one measurement is present", () => {
    render(
      <MeasureSummary measurements={[m1]} onClear={() => {}} onDelete={() => {}} />,
    );
    // Button labeled via t("viewer3d.measure.clear") — match by role + accessible name
    // tolerant to either Polish or English locale resolution.
    expect(screen.getByRole("button", { name: /wyczy|clear/i })).toBeTruthy();
  });

  it("invokes onClear exactly once when Clear button is clicked", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();
    render(
      <MeasureSummary
        measurements={[m1, m2]}
        onClear={onClear}
        onDelete={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: /wyczy|clear/i }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it("invokes onDelete with the row id when the row #1 × button is clicked (regression guard for per-row delete)", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <MeasureSummary
        measurements={[m1, m2]}
        onClear={() => {}}
        onDelete={onDelete}
      />,
    );
    // Scope by row position. List rows render in insertion order; row #1 = m1.id "1".
    const rows = screen.getAllByRole("listitem");
    expect(rows.length).toBe(2);
    const row1DeleteButton = within(rows[0]!).getByRole("button");
    await user.click(row1DeleteButton);
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledWith("1");
  });

  it("Clear button remains clickable when MeasureSummary is mounted under a pointer-events-none ancestor (TB-015 fix invariant — simulates Viewer3DModal:390 canvas-overlay scenario)", async () => {
    // This is the actual TB-015 regression guard: a `pointer-events-auto` ancestor
    // must exist somewhere between the Clear button and the `pointer-events-none`
    // wrapper, so the click reaches the handler. parentElement is fragile (shadcn
    // Button could acquire a Tooltip/Slot wrapper later — see Edge-Case-Hunter
    // review 2026-05-21); query the ancestor chain via closest() to stay robust.
    const user = userEvent.setup();
    const onClear = vi.fn();
    render(
      <div className="pointer-events-none">
        <MeasureSummary measurements={[m1]} onClear={onClear} onDelete={() => {}} />
      </div>,
    );
    const clearButton = screen.getByRole("button", { name: /wyczy|clear/i });
    // The fix invariant: an ancestor with pointer-events-auto exists between the
    // button and our outer pointer-events-none host, so the click is captured.
    const reEnablingAncestor = clearButton.closest(".pointer-events-auto");
    expect(reEnablingAncestor).not.toBeNull();
    // Functional consequence: the click reaches the handler.
    await user.click(clearButton);
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
