import { describe, expect, it } from "vitest";

import type { TagReadWithCount } from "@/lib/api-types";
import { findDuplicateClusters, levenshtein, normalizeTagText } from "@/modules/admin/duplicateTags";

// Story 46.3 — unit coverage for every I/O Matrix clustering scenario from the
// frozen intent-contract. Pure-logic file: no components rendered, so no
// `cleanup()`/`afterEach` wiring is needed here (per repo convention).

function tag(overrides: Partial<TagReadWithCount> & { id: string }): TagReadWithCount {
  return {
    slug: overrides.id,
    name_en: "",
    name_pl: null,
    group_id: null,
    group_position: 0,
    model_count: 0,
    ...overrides,
  };
}

describe("normalizeTagText", () => {
  it("lowercases, trims, and collapses internal whitespace", () => {
    expect(normalizeTagText("  3D   Printer  ")).toBe("3d printer");
  });

  it("NFD-decomposes and strips combining diacritics", () => {
    expect(normalizeTagText("Materiał")).not.toBe("materiał");
    expect(normalizeTagText("Zażółć")).toBe("zazolc");
  });

  it("maps ł/Ł to l/L (no NFD decomposition exists for those)", () => {
    expect(normalizeTagText("Materiał")).toBe("material");
    expect(normalizeTagText("Łódź")).toBe("lodz");
  });
});

describe("levenshtein", () => {
  it("is 0 for identical strings", () => {
    expect(levenshtein("bracket", "bracket")).toBe(0);
  });

  it("counts a single insertion as distance 1", () => {
    expect(levenshtein("bracket", "brackets")).toBe(1);
  });

  it("handles empty strings", () => {
    expect(levenshtein("", "abc")).toBe(3);
    expect(levenshtein("abc", "")).toBe(3);
  });
});

describe("findDuplicateClusters — I/O Matrix scenarios", () => {
  it("clusters a case-insensitive EN duplicate", () => {
    const tags = [
      tag({ id: "a", name_en: "3D Printer" }),
      tag({ id: "b", name_en: "3d printer" }),
    ];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]?.map((t) => t.id).sort()).toEqual(["a", "b"]);
  });

  it("clusters a near-typo EN duplicate (distance 1, len 8)", () => {
    const tags = [tag({ id: "a", name_en: "Bracket" }), tag({ id: "b", name_en: "Brackets" })];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]?.map((t) => t.id).sort()).toEqual(["a", "b"]);
  });

  it("clusters an exact PL duplicate", () => {
    const tags = [
      tag({ id: "a", name_en: "Alpha", name_pl: "Różne" }),
      tag({ id: "b", name_en: "Beta", name_pl: "różne" }),
    ];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]?.map((t) => t.id).sort()).toEqual(["a", "b"]);
  });

  it("does NOT cluster distinct short tags (PLA/ABS, len 3, distance 3, threshold 0)", () => {
    const tags = [tag({ id: "a", name_en: "PLA" }), tag({ id: "b", name_en: "ABS" })];
    expect(findDuplicateClusters(tags)).toEqual([]);
  });

  it("clusters similar tags across different groups, or one groupless, regardless of group_id", () => {
    const tags = [
      tag({ id: "a", name_en: "Bracket", group_id: "g1" }),
      tag({ id: "b", name_en: "Brackets", group_id: "g2" }),
      tag({ id: "c", name_en: "Bracket ", group_id: null }),
    ];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]?.map((t) => t.id).sort()).toEqual(["a", "b", "c"]);
  });

  it("forms one transitive 3-tag cluster when A~B and B~C but A/C aren't directly similar", () => {
    // A~B matches on name_en only ("Zeta" both sides); B~C matches on name_pl only
    // ("Wspólny"/"wspólny"). A has no name_pl and C's name_en ("Omega") is nothing
    // like A's ("Zeta"), so A and C are not directly similar — the cluster only
    // forms through B, exercising the union-find transitivity.
    const tags = [
      tag({ id: "a", name_en: "Zeta", name_pl: null }),
      tag({ id: "b", name_en: "Zeta", name_pl: "Wspólny" }),
      tag({ id: "c", name_en: "Omega", name_pl: "wspólny" }),
    ];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]?.map((t) => t.id).sort()).toEqual(["a", "b", "c"]);
  });

  it("returns no clusters when all tags are textually distinct", () => {
    const tags = [
      tag({ id: "a", name_en: "PLA" }),
      tag({ id: "b", name_en: "ABS" }),
      tag({ id: "c", name_en: "Resin" }),
    ];
    expect(findDuplicateClusters(tags)).toEqual([]);
  });

  it("never compares an en field against a pl field (no cross-language matching)", () => {
    const tags = [
      tag({ id: "a", name_en: "Bracket", name_pl: null }),
      tag({ id: "b", name_en: "Zupa", name_pl: "Bracket" }),
    ];
    expect(findDuplicateClusters(tags)).toEqual([]);
  });

  it("sorts clusters by descending size, then representative normalized name_en", () => {
    const tags = [
      // 2-tag cluster "zeta"/"zetaa" (should sort after the 3-tag cluster).
      tag({ id: "z1", name_en: "Zeta" }),
      tag({ id: "z2", name_en: "Zetaa" }),
      // 3-tag cluster "bracket" family.
      tag({ id: "a", name_en: "Bracket" }),
      tag({ id: "b", name_en: "Brackets" }),
      tag({ id: "c", name_en: "bracket" }),
    ];
    const clusters = findDuplicateClusters(tags);
    expect(clusters).toHaveLength(2);
    expect(clusters[0]).toHaveLength(3);
    expect(clusters[1]).toHaveLength(2);
  });
});
