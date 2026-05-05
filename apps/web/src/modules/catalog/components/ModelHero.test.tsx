import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import "@/locales/i18n";

import { ModelHero } from "./ModelHero";
import type { ModelDetail } from "@/lib/api-types";

afterEach(() => cleanup());

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    legacy_id: "001",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    category_id: "22222222-2222-2222-2222-222222222222",
    source: "printables",
    status: "printed",
    rating: 4.5,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [
      { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: null },
      { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null },
      { id: "t3", slug: "cool", name_en: "Cool", name_pl: null },
      { id: "t4", slug: "petg", name_en: "PETG", name_pl: null },
      { id: "t5", slug: "supports-off", name_en: "Supports off", name_pl: null },
      { id: "t6", slug: "extra", name_en: "Extra", name_pl: null },
    ],
    category: {
      id: "22222222-2222-2222-2222-222222222222",
      parent_id: null,
      slug: "decorations",
      name_en: "Decorations",
      name_pl: "Dekoracje",
    },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    ...over,
  };
}

describe("ModelHero", () => {
  it("renders breadcrumb with category and title", () => {
    render(<ModelHero detail={makeDetail()} />);
    expect(screen.getByText("Decorations")).toBeTruthy();
    expect(screen.getByText("Dragon")).toBeTruthy();
  });

  it("renders status badge, rating, source, top tags", () => {
    render(<ModelHero detail={makeDetail()} />);
    expect(document.body.textContent?.toLowerCase()).toContain("printed");
    expect(document.body.textContent).toContain("4.5");
    expect(document.body.textContent?.toLowerCase()).toContain("printables");
    // top 5 tag chips
    expect(screen.getAllByTestId("tag-chip").length).toBe(5);
  });

  it("shows overflow indicator when more than 5 tags", () => {
    render(<ModelHero detail={makeDetail()} />);
    expect(document.body.textContent).toContain("+1");
  });

  it("does not render rating when null", () => {
    render(<ModelHero detail={makeDetail({ rating: null })} />);
    expect(document.body.textContent).not.toMatch(/★\s*\d/);
  });
});
