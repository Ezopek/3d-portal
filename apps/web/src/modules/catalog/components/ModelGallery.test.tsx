import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import "@/locales/i18n";
import { ModelGallery } from "./ModelGallery";
import type { ModelFileRead } from "@/lib/api-types";

afterEach(() => cleanup());

const MODEL_ID = "11111111-1111-1111-1111-111111111111";
const FILES: ModelFileRead[] = [
  {
    id: "f1",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "x.stl",
    storage_path: "x",
    sha256: "",
    size_bytes: 0,
    mime_type: "model/stl",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "f2",
    model_id: MODEL_ID,
    kind: "image",
    original_name: "iso.png",
    storage_path: "y",
    sha256: "",
    size_bytes: 0,
    mime_type: "image/png",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "f3",
    model_id: MODEL_ID,
    kind: "print",
    original_name: "print.jpg",
    storage_path: "z",
    sha256: "",
    size_bytes: 0,
    mime_type: "image/jpeg",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
];

describe("ModelGallery", () => {
  it("renders 'no preview' when no image/print files", () => {
    render(<ModelGallery modelId={MODEL_ID} files={[FILES[0]!]} />);
    expect(screen.getByText("no preview")).toBeTruthy();
  });

  it("renders main image from first image/print file", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const main = screen.getByTestId("gallery-main") as HTMLImageElement;
    expect(main.getAttribute("src")).toContain(`/api/models/${MODEL_ID}/files/f2/content`);
  });

  it("renders thumbnail strip with all image/print files", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const thumbs = screen.getAllByTestId("gallery-thumb");
    expect(thumbs).toHaveLength(2);
  });

  it("clicking a thumbnail switches the main image", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const thumbs = screen.getAllByTestId("gallery-thumb");
    fireEvent.click(thumbs[1]!);
    const main = screen.getByTestId("gallery-main") as HTMLImageElement;
    expect(main.getAttribute("src")).toContain(`/api/models/${MODEL_ID}/files/f3/content`);
  });
});
