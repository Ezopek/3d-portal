import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DescriptionPanel } from "./DescriptionPanel";
import type { NoteRead } from "@/lib/api-types";

afterEach(() => cleanup());

const MODEL_ID = "m1";

function note(over: Partial<NoteRead> = {}): NoteRead {
  return {
    id: "n1",
    model_id: MODEL_ID,
    kind: "description",
    body: "Articulated dragon for Bambu A1.",
    author_id: null,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

describe("DescriptionPanel", () => {
  it("renders the description body", () => {
    render(<DescriptionPanel notes={[note()]} />);
    expect(screen.getByText(/Articulated dragon/)).toBeTruthy();
  });

  it("ignores non-description notes", () => {
    render(<DescriptionPanel notes={[note({ kind: "operational", body: "tip" })]} />);
    expect(document.body.textContent).not.toContain("tip");
  });

  it("renders fallback when no description", () => {
    render(<DescriptionPanel notes={[]} />);
    expect(document.body.textContent?.toLowerCase()).toContain("no description");
  });
});
