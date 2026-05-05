import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ModelDetail } from "@/lib/api-types";

import { SecondaryTabs } from "./SecondaryTabs";

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
    category: {
      id: "c",
      parent_id: null,
      slug: "c",
      name_en: "C",
      name_pl: null,
    },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    ...over,
  };
}

describe("SecondaryTabs", () => {
  it("renders the three read-only tabs", () => {
    render(<SecondaryTabs detail={makeDetail()} />);
    expect(screen.getByRole("tab", { name: /files/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /prints/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /operational/i })).toBeTruthy();
  });

  it("activates Prints when its tab is clicked", () => {
    render(
      <SecondaryTabs
        detail={makeDetail({
          prints: [
            {
              id: "p1",
              model_id: "m1",
              photo_file_id: null,
              printed_at: "2026-04-30",
              note: "ok",
              created_at: "",
              updated_at: "",
            },
          ],
        })}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: /prints/i }));
    expect(screen.getByText("ok")).toBeTruthy();
  });
});
