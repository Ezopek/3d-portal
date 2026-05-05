import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { NoteRead } from "@/lib/api-types";

import { OperationalNotesTab } from "./OperationalNotesTab";

afterEach(() => cleanup());

function note(kind: NoteRead["kind"], body: string, id: string): NoteRead {
  return {
    id,
    model_id: "m1",
    kind,
    body,
    author_id: null,
    created_at: "",
    updated_at: "",
  };
}

describe("OperationalNotesTab", () => {
  it("renders operational, ai_review, other notes (not description)", () => {
    render(
      <OperationalNotesTab
        notes={[
          note("description", "should NOT show", "n0"),
          note("operational", "tip 1", "n1"),
          note("ai_review", "AI says", "n2"),
          note("other", "misc", "n3"),
        ]}
      />,
    );
    expect(screen.getByText("tip 1")).toBeTruthy();
    expect(screen.getByText("AI says")).toBeTruthy();
    expect(screen.getByText("misc")).toBeTruthy();
    expect(screen.queryByText("should NOT show")).toBeNull();
  });

  it("renders kind labels", () => {
    render(<OperationalNotesTab notes={[note("operational", "x", "n1")]} />);
    expect(document.body.textContent?.toLowerCase()).toContain("operational");
  });

  it("renders empty state when no non-description notes", () => {
    render(<OperationalNotesTab notes={[note("description", "x", "n1")]} />);
    expect(document.body.textContent?.toLowerCase()).toContain("no notes");
  });
});
