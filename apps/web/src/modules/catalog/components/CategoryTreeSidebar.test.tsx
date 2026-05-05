import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import "@/locales/i18n";
import { CategoryTreeSidebar } from "./CategoryTreeSidebar";
import type { CategoryTree } from "@/lib/api-types";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

beforeEach(() => sessionStorage.clear());

const TREE: CategoryTree = {
  roots: [
    {
      id: "a",
      parent_id: null,
      slug: "decorations",
      name_en: "Decorations",
      name_pl: "Dekoracje",
      children: [
        {
          id: "a1",
          parent_id: "a",
          slug: "vases",
          name_en: "Vases",
          name_pl: null,
          children: [],
          model_count: 5,
        },
      ],
      model_count: 14,
    },
    {
      id: "b",
      parent_id: null,
      slug: "tools",
      name_en: "Tools",
      name_pl: "Narzędzia",
      children: [],
      model_count: 23,
    },
  ],
};

describe("CategoryTreeSidebar", () => {
  it("renders the All row with total count (sum of root model_counts)", () => {
    render(<CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={() => {}} />);
    // 14 (decorations) + 23 (tools) = 37
    expect(screen.getByText(/37/)).toBeTruthy();
  });

  it("renders root nodes with their counts from node.model_count", () => {
    render(<CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText(/Decorations/)).toBeTruthy();
    expect(screen.getByText(/14/)).toBeTruthy();
    expect(screen.getByText(/Tools/)).toBeTruthy();
    expect(screen.getByText(/23/)).toBeTruthy();
  });

  it("does not render children unless the parent is expanded", () => {
    render(<CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={() => {}} />);
    expect(screen.queryByText(/Vases/)).toBeNull();
  });

  it("expands a parent on caret click and persists state", () => {
    render(<CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={() => {}} />);
    const caret = screen.getByLabelText("expand decorations");
    fireEvent.click(caret);
    expect(screen.getByText(/Vases/)).toBeTruthy();
    expect(sessionStorage.getItem("catalog:tree-expand")).toContain("decorations");
  });

  it("rehydrates expand state from sessionStorage on mount", () => {
    sessionStorage.setItem("catalog:tree-expand", JSON.stringify(["decorations"]));
    render(<CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText(/Vases/)).toBeTruthy();
  });

  it("calls onSelect with category id when row clicked", () => {
    const calls: (string | null)[] = [];
    render(
      <CategoryTreeSidebar tree={TREE} selectedId={null} onSelect={(id) => calls.push(id)} />,
    );
    fireEvent.click(screen.getByText(/Tools/));
    expect(calls).toEqual(["b"]);
  });

  it("calls onSelect(null) when All row clicked", () => {
    const calls: (string | null)[] = [];
    render(
      <CategoryTreeSidebar tree={TREE} selectedId="a" onSelect={(id) => calls.push(id)} />,
    );
    fireEvent.click(screen.getByLabelText("select all categories"));
    expect(calls).toEqual([null]);
  });
});
