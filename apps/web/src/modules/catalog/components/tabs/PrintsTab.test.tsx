import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { PrintRead } from "@/lib/api-types";

import { PrintsTab } from "./PrintsTab";

afterEach(() => cleanup());

const MODEL_ID = "m1";
const PRINT: PrintRead = {
  id: "p1",
  model_id: MODEL_ID,
  photo_file_id: "img1",
  printed_at: "2026-04-30",
  note: "Printed in PETG 0.2mm",
  created_at: "",
  updated_at: "",
};

describe("PrintsTab", () => {
  it("renders each print with date and note", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />);
    expect(screen.getByText(/2026-04-30/)).toBeTruthy();
    expect(screen.getByText(/PETG/)).toBeTruthy();
  });

  it("renders thumbnail img when photo_file_id is set", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />);
    const img = document.querySelector("img") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe(
      `/api/models/${MODEL_ID}/files/img1/content`,
    );
  });

  it("renders empty state when no prints", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[]} />);
    expect(document.body.textContent?.toLowerCase()).toContain("no prints");
  });
});
