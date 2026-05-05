import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ModelFileRead } from "@/lib/api-types";

import { FilesTab } from "./FilesTab";

afterEach(() => cleanup());

const MODEL_ID = "m1";
const FILES: ModelFileRead[] = [
  {
    id: "fa",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "a.stl",
    storage_path: "",
    sha256: "",
    size_bytes: 1024,
    mime_type: "",
    position: null,
    created_at: "",
  },
  {
    id: "fb",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "b.stl",
    storage_path: "",
    sha256: "",
    size_bytes: 2048,
    mime_type: "",
    position: null,
    created_at: "",
  },
  {
    id: "fc",
    model_id: MODEL_ID,
    kind: "source",
    original_name: "c.f3d",
    storage_path: "",
    sha256: "",
    size_bytes: 4096,
    mime_type: "",
    position: null,
    created_at: "",
  },
  {
    id: "fd",
    model_id: MODEL_ID,
    kind: "archive_3mf",
    original_name: "d.3mf",
    storage_path: "",
    sha256: "",
    size_bytes: 8192,
    mime_type: "",
    position: null,
    created_at: "",
  },
  {
    id: "fe",
    model_id: MODEL_ID,
    kind: "image",
    original_name: "e.png",
    storage_path: "",
    sha256: "",
    size_bytes: 512,
    mime_type: "",
    position: null,
    created_at: "",
  },
];

describe("FilesTab", () => {
  it("defaults to STL kind and lists STL files only", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />);
    expect(screen.getByText("a.stl")).toBeTruthy();
    expect(screen.getByText("b.stl")).toBeTruthy();
    expect(screen.queryByText("c.f3d")).toBeNull();
    expect(screen.queryByText("e.png")).toBeNull();
  });

  it("clicking Source chip switches to source files", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />);
    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getByText("c.f3d")).toBeTruthy();
    expect(screen.queryByText("a.stl")).toBeNull();
  });

  it("download link points at the content endpoint", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />);
    const link = screen
      .getAllByRole("link")
      .find((a) => a.getAttribute("href")?.includes("fa"));
    expect(link?.getAttribute("href")).toBe(
      `/api/models/${MODEL_ID}/files/fa/content?download=1`,
    );
  });

  it("renders an empty state when no files of the active kind", () => {
    render(<FilesTab modelId={MODEL_ID} files={[FILES[4]!]} />);
    expect(document.body.textContent?.toLowerCase()).toContain("no files");
  });
});
