import { describe, expect, it } from "vitest";

import type {
  BrowseCategoryAdminRead,
  OverCategorizedResponse,
  TagGroupsResponse,
  TagReadWithCount,
} from "@/lib/api-types";

import {
  computeCurationChecks,
  ROW_CAP,
  type CurationCheckKind,
  type LabelCollisionFinding,
} from "./curationChecks";
import { ADVISORY_MAX, TINY_MAX } from "./curationThresholds";

// Story 52.3 — the six checks as pure computation. Every case here is about the
// DEFINITION of a finding; rendering lives in CurationQaPanel.test.tsx.

function cat(overrides: Partial<BrowseCategoryAdminRead> = {}): BrowseCategoryAdminRead {
  return {
    id: "c1",
    slug: "storage",
    name_en: "Storage",
    name_pl: "Przechowywanie",
    description_en: null,
    description_pl: null,
    position: 0,
    parent_id: null,
    model_count: 10,
    inclusion_criterion: null,
    ...overrides,
  };
}

function tag(overrides: Partial<TagReadWithCount> = {}): TagReadWithCount {
  return {
    id: "t1",
    slug: "vases",
    name_en: "Vases",
    name_pl: "Wazony",
    group_id: "g1",
    group_position: 0,
    model_count: 4,
    ...overrides,
  };
}

function groups(
  grouped: TagReadWithCount[] = [],
  groupless: TagReadWithCount[] = [],
): TagGroupsResponse {
  return {
    groups: [
      { id: "g1", slug: "type", name_en: "Type", name_pl: "Typ", position: 0, tags: grouped },
    ],
    groupless,
  };
}

function over(items: OverCategorizedResponse["items"], total = items.length) {
  return { items, total };
}

function kinds(result: ReturnType<typeof computeCurationChecks>): CurationCheckKind[] {
  return result.groups.map((g) => g.kind);
}

function rowsOf(result: ReturnType<typeof computeCurationChecks>, kind: CurationCheckKind) {
  return result.groups.find((g) => g.kind === kind)?.rows ?? [];
}

describe("curationChecks — empty and tiny categories (AC-10, AC-11)", () => {
  it("flags a zero-count category as EMPTY and never also as tiny", () => {
    const result = computeCurationChecks({
      categories: [cat({ model_count: 0 })],
      tagGroups: groups(),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(kinds(result)).toEqual(["empty_category"]);
    expect(result.totalFindings).toBe(1);
  });

  it("flags 1..TINY_MAX as tiny and TINY_MAX+1 as nothing", () => {
    const categories = [
      cat({ id: "a", slug: "a", model_count: 1 }),
      cat({ id: "b", slug: "b", model_count: TINY_MAX }),
      cat({ id: "c", slug: "c", model_count: TINY_MAX + 1 }),
    ];
    const result = computeCurationChecks({
      categories,
      tagGroups: groups(),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(kinds(result)).toEqual(["tiny_category"]);
    expect(rowsOf(result, "tiny_category").map((f) => f.id)).toEqual(["tiny:a", "tiny:b"]);
  });

  it("preserves the server's (position, slug) order within a check", () => {
    const result = computeCurationChecks({
      categories: [
        cat({ id: "p0", slug: "p0", position: 0, model_count: 0 }),
        cat({ id: "p1", slug: "p1", position: 1, model_count: 0 }),
      ],
      tagGroups: groups(),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(result, "empty_category").map((f) => f.id)).toEqual(["empty:p0", "empty:p1"]);
  });
});

describe("curationChecks — label collision (AC-12, D-4)", () => {
  it("matches an identical label and names the tag's group", () => {
    const result = computeCurationChecks({
      categories: [cat({ name_en: "Vases", name_pl: "Wazony" })],
      tagGroups: groups([tag()]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    const rows = rowsOf(result, "label_collision") as LabelCollisionFinding[];
    expect(rows).toHaveLength(1);
    expect(rows[0]?.group?.name_en).toBe("Type");
  });

  it("carries a null group for a groupless tag — never a placeholder", () => {
    const result = computeCurationChecks({
      categories: [cat({ name_en: "Vases", name_pl: null })],
      tagGroups: groups([], [tag({ id: "t9", group_id: null })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    const rows = rowsOf(result, "label_collision") as LabelCollisionFinding[];
    expect(rows).toHaveLength(1);
    expect(rows[0]?.group).toBeNull();
  });

  it("normalizes diacritics and Polish ł the way the shipped detector does", () => {
    const result = computeCurationChecks({
      categories: [cat({ name_en: "Zzz", name_pl: "Świeczniki" })],
      tagGroups: groups([tag({ name_en: "Qqq", name_pl: "swieczniki" })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(result, "label_collision")).toHaveLength(1);
  });

  it("never compares en against pl", () => {
    // "Vases" (en) vs "Vases" (pl) would collide only across languages.
    const result = computeCurationChecks({
      categories: [cat({ name_en: "Zzzzzzzz", name_pl: "Vases" })],
      tagGroups: groups([tag({ name_en: "Vases", name_pl: "Qqqqqqqq" })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(result, "label_collision")).toHaveLength(0);
  });

  it("never produces a finding from an empty or null name_pl on either side", () => {
    const bothNull = computeCurationChecks({
      categories: [cat({ name_en: "Zzzzzzzz", name_pl: null })],
      tagGroups: groups([tag({ name_en: "Qqqqqqqq", name_pl: null })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(bothNull, "label_collision")).toHaveLength(0);

    const emptyString = computeCurationChecks({
      categories: [cat({ name_en: "Zzzzzzzz", name_pl: "" })],
      tagGroups: groups([tag({ name_en: "Qqqqqqqq", name_pl: "" })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(emptyString, "label_collision")).toHaveLength(0);
  });

  it("keeps the shipped short-string rule: <=4 chars cluster only on an exact match", () => {
    const near = computeCurationChecks({
      categories: [cat({ name_en: "PLA", name_pl: null })],
      tagGroups: groups([tag({ name_en: "ABS", name_pl: null })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(rowsOf(near, "label_collision")).toHaveLength(0);
  });

  it("reports each (category, tag) pair exactly once", () => {
    const result = computeCurationChecks({
      categories: [cat({ id: "c1", name_en: "Vases", name_pl: "Wazony" })],
      // The same tag is only ever visited once per category.
      tagGroups: groups([tag({ id: "t1" }), tag({ id: "t2", slug: "vase", name_en: "Vase" })]),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    const ids = rowsOf(result, "label_collision").map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("curationChecks — count rows (AC-14, AC-15)", () => {
  it("omits both count rows at zero", () => {
    const result = computeCurationChecks({
      categories: [cat()],
      tagGroups: groups(),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    expect(result.groups).toHaveLength(0);
    expect(result.totalFindings).toBe(0);
  });

  it("renders one count row each, carrying the true counts", () => {
    const result = computeCurationChecks({
      categories: [cat()],
      tagGroups: groups([], [tag({ id: "x1", group_id: null }), tag({ id: "x2", group_id: null })]),
      overCategorized: over([]),
      uncategorizedTotal: 17,
    });
    expect(kinds(result)).toEqual(["uncategorized_models", "ungrouped_tags"]);
    const uncategorized = rowsOf(result, "uncategorized_models")[0];
    const ungrouped = rowsOf(result, "ungrouped_tags")[0];
    expect(uncategorized?.kind === "uncategorized_models" && uncategorized.count).toBe(17);
    expect(ungrouped?.kind === "ungrouped_tags" && ungrouped.count).toBe(2);
  });
});

describe("curationChecks — order, cap and totals (AC-16, AC-17, D-7, D-8)", () => {
  const ALL = {
    categories: [
      cat({ id: "e", slug: "e", model_count: 0 }),
      cat({ id: "t", slug: "t", model_count: 1, name_en: "Vases", name_pl: "Wazony" }),
    ],
    tagGroups: groups([tag()], [tag({ id: "gl", slug: "loose", name_en: "Loose", group_id: null })]),
    overCategorized: over([
      {
        model_id: "m1",
        slug: "spiral-vase",
        name_en: "Spiral vase",
        name_pl: "Wazon spiralny",
        category_count: ADVISORY_MAX + 1,
      },
    ]),
    uncategorizedTotal: 17,
  };

  it("orders the checks exactly as D-7 fixes them", () => {
    expect(kinds(computeCurationChecks(ALL))).toEqual([
      "empty_category",
      "tiny_category",
      "label_collision",
      "over_categorized",
      "uncategorized_models",
      "ungrouped_tags",
    ]);
  });

  it("caps rows per check at ROW_CAP while the group total stays true", () => {
    const many = Array.from({ length: ROW_CAP + 3 }, (_, i) =>
      cat({ id: `c${i}`, slug: `c${i}`, position: i, model_count: 0 }),
    );
    const result = computeCurationChecks({
      categories: many,
      tagGroups: groups(),
      overCategorized: over([]),
      uncategorizedTotal: 0,
    });
    const group = result.groups[0];
    expect(group?.rows).toHaveLength(ROW_CAP);
    expect(group?.total).toBe(ROW_CAP + 3);
    // AC-9/AC-17 — the heading counts FINDINGS, not rendered rows.
    expect(result.totalFindings).toBe(ROW_CAP + 3);
  });

  it("uses the server's total for the over-categorized check, not the page length", () => {
    // The endpoint caps `items` at `limit`; the overflow line must state the
    // true remaining count rather than the page size.
    const result = computeCurationChecks({
      categories: [],
      tagGroups: groups(),
      overCategorized: over(
        [
          {
            model_id: "m1",
            slug: "a",
            name_en: "A",
            name_pl: null,
            category_count: 9,
          },
        ],
        42,
      ),
      uncategorizedTotal: 0,
    });
    expect(result.groups[0]?.total).toBe(42);
    expect(result.totalFindings).toBe(42);
  });

  it("contributes nothing from a source that has not resolved", () => {
    const result = computeCurationChecks({
      categories: undefined,
      tagGroups: undefined,
      overCategorized: undefined,
      uncategorizedTotal: undefined,
    });
    expect(result.groups).toHaveLength(0);
    expect(result.totalFindings).toBe(0);
  });

  it("still computes every OTHER check when one source is missing", () => {
    const result = computeCurationChecks({ ...ALL, tagGroups: undefined });
    expect(kinds(result)).toEqual([
      "empty_category",
      "tiny_category",
      "over_categorized",
      "uncategorized_models",
    ]);
  });
});
