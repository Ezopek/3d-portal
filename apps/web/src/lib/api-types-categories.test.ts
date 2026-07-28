import { describe, it, expectTypeOf } from "vitest";

import type {
  BrowseCategoryRead,
  BrowseCategorySummary,
  ModelDetail,
  ModelSummary,
} from "@/lib/api-types";

// RED: BrowseCategorySummary / BrowseCategoryRead and ModelDetail.categories do
// not exist yet — this test fails under `npm run typecheck` (tsc -b compiles
// src/**/*.test.ts) until Story 50.1 GREEN is done. It does NOT fail under
// `vitest run`: esbuild erases `import type` and expectTypeOf at runtime, so
// tsc -b is the RED gate here (43.1 AC-6, 35.5 precedent).
// Precedent: api-types-tags.test.ts. No `as`, no `any`, no unsafe casts.

describe("BrowseCategorySummary (embeddable shape — Story 49.3, Decision AY)", () => {
  it("is structurally the exact six-key shape", () => {
    // Structural equality also fails if an extra key is ever added.
    expectTypeOf<BrowseCategorySummary>().toEqualTypeOf<{
      id: string;
      slug: string;
      name_en: string;
      name_pl: string | null;
      position: number;
      parent_id: string | null;
    }>();
  });

  it("deliberately carries NO model_count and NO nested children", () => {
    // Decision AY: embedding a count here would cost an aggregate per detail
    // read for a number the detail view never renders. The contract is FLAT —
    // `parent_id` is a scalar FK, there is no children/subcategories key.
    expectTypeOf<BrowseCategorySummary>().not.toHaveProperty("model_count");
    expectTypeOf<BrowseCategorySummary>().not.toHaveProperty("children");
    expectTypeOf<BrowseCategorySummary>().not.toHaveProperty("subcategories");
  });
});

describe("BrowseCategoryRead (GET /api/categories[/{slug}] item)", () => {
  it("extends BrowseCategorySummary with a REQUIRED model_count", () => {
    // Required and unconditional here, unlike TagListItem's opt-in
    // `?with_counts` count — browse IA and curation QA always need it.
    expectTypeOf<BrowseCategoryRead["model_count"]>().toEqualTypeOf<number>();
    expectTypeOf<BrowseCategoryRead["description_en"]>().toEqualTypeOf<
      string | null
    >();
    expectTypeOf<BrowseCategoryRead["description_pl"]>().toEqualTypeOf<
      string | null
    >();
    expectTypeOf<BrowseCategoryRead["parent_id"]>().toEqualTypeOf<
      string | null
    >();
  });

  it("does NOT carry inclusion_criterion (that is the admin contract, D-2)", () => {
    expectTypeOf<BrowseCategoryRead>().not.toHaveProperty(
      "inclusion_criterion",
    );
  });

  it("accepts a real GET /api/categories body via `satisfies` (no cast)", () => {
    const wire = [
      // top-level, both descriptions present
      {
        id: "11111111-1111-4111-8111-111111111111",
        slug: "kitchen",
        name_en: "Kitchen",
        name_pl: "Kuchnia",
        position: 0,
        parent_id: null,
        description_en: "Kitchen gadgets",
        description_pl: "Gadżety kuchenne",
        model_count: 12,
      },
      // child of the above — parent_id is a scalar FK, not a nested node
      {
        id: "22222222-2222-4222-8222-222222222222",
        slug: "kitchen-storage",
        name_en: "Storage",
        name_pl: "Przechowywanie",
        position: 1,
        parent_id: "11111111-1111-4111-8111-111111111111",
        description_en: null,
        description_pl: null,
        model_count: 4,
      },
      // untranslated label
      {
        id: "33333333-3333-4333-8333-333333333333",
        slug: "tools",
        name_en: "Tools",
        name_pl: null,
        position: 2,
        parent_id: null,
        description_en: "Workshop tools",
        description_pl: null,
        model_count: 7,
      },
      // the empty category the curation surface must still see (FR26-CAT-2)
      {
        id: "44444444-4444-4444-8444-444444444444",
        slug: "unsorted",
        name_en: "Unsorted",
        name_pl: null,
        position: 3,
        parent_id: null,
        description_en: null,
        description_pl: null,
        model_count: 0,
      },
    ] satisfies BrowseCategoryRead[];

    expectTypeOf(wire).toMatchTypeOf<BrowseCategoryRead[]>();
  });
});

describe("ModelDetail.categories (FR26-CAT-2)", () => {
  it("is a REQUIRED BrowseCategorySummary[] — never optional, never null", () => {
    // D-1: api-types.ts mirrors the WIRE, not the OpenAPI document. The single
    // get_model_detail constructor always writes the key, so `[]` is ordinary
    // rather than exceptional. exactOptionalPropertyTypes is NOT set, so an
    // optional key would widen to `| undefined` and fail this assertion —
    // which is precisely the requiredness proof.
    expectTypeOf<ModelDetail["categories"]>().toEqualTypeOf<
      BrowseCategorySummary[]
    >();
  });

  it("is declared on ModelDetail only — ModelSummary does NOT gain it", () => {
    // List cards render no categories in the MVP IA (Decision AY / AC-20).
    expectTypeOf<ModelSummary>().not.toHaveProperty("categories");
  });
});
