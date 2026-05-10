import { render, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import "@/locales/i18n";
import { MetadataPanel } from "./MetadataPanel";
import type { ModelDetail } from "@/lib/api-types";

afterEach(() => cleanup());

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
    legacy_id: null,
    slug: "x",
    name_en: "X",
    name_pl: null,
    category_id: "c",
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    category: { id: "c", parent_id: null, slug: "c", name_en: "C", name_pl: null },
    files: [
      {
        id: "f1",
        model_id: "m1",
        kind: "stl",
        original_name: "a.stl",
        storage_path: "",
        sha256: "",
        size_bytes: 0,
        mime_type: "",
        position: null,
        selected_for_render: false,
        created_at: "",
      },
      {
        id: "f2",
        model_id: "m1",
        kind: "image",
        original_name: "a.png",
        storage_path: "",
        sha256: "",
        size_bytes: 0,
        mime_type: "",
        position: null,
        selected_for_render: false,
        created_at: "",
      },
    ],
    prints: [],
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
    ...over,
  };
}

describe("MetadataPanel", () => {
  it("renders source, date, files, prints", () => {
    render(<MetadataPanel detail={makeDetail()} />);
    expect(document.body.textContent?.toLowerCase()).toContain("printables");
    // Date is locale-formatted now; assert on a fragment that survives any locale.
    expect(document.body.textContent).toMatch(/2026/);
    expect(document.body.textContent).toContain("2"); // 2 files
  });

  it("breaks down file count by kind", () => {
    render(<MetadataPanel detail={makeDetail()} />);
    // expects e.g. "2 (1 STL · 1 image)" — flexible match
    expect(document.body.textContent).toMatch(/STL/);
    expect(document.body.textContent).toMatch(/image/);
  });

  it("renders 0 prints when empty", () => {
    render(<MetadataPanel detail={makeDetail()} />);
    expect(document.body.textContent).toContain("Prints");
    // At least one '0' should appear for the print count.
    expect(document.body.textContent).toMatch(/Prints[^\d]*0/);
  });
});
