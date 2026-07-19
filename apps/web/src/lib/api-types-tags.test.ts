import { describe, it, expectTypeOf } from "vitest";

import type {
  TagRead,
  TagListItem,
  TagReadWithCount,
  TagGroupRead,
  TagGroupsResponse,
  TagGroupSummary,
} from "@/lib/api-types";

// RED: TagRead.group_id / group_position and the five tag-group types do not
// exist yet — this test fails under `npm run typecheck` (tsc -b compiles
// src/**/*.test.ts) until Story 43.1 GREEN is done. Precedent: Story 35.5
// api-types-profile-source.test.ts. No `as`, no `any`, no unsafe casts.

describe("TagRead facet-membership fields (Story 42.2, additive)", () => {
  it("carries group_id: string | null and group_position: number", () => {
    expectTypeOf<TagRead["group_id"]>().toEqualTypeOf<string | null>();
    expectTypeOf<TagRead["group_position"]>().toEqualTypeOf<number>();
  });

  it("does NOT embed a `group` field (42.2 D-SHAPE-1)", () => {
    expectTypeOf<TagRead>().not.toHaveProperty("group");
  });
});

describe("TagListItem (GET /api/tags item — opt-in count)", () => {
  it("extends TagRead with an OPTIONAL model_count (never | null)", () => {
    // exactOptionalPropertyTypes is NOT set → optional prop widens to
    // `number | undefined`. The serializer drops the key when absent, so it
    // is optional, never null.
    expectTypeOf<TagListItem["model_count"]>().toEqualTypeOf<
      number | undefined
    >();
    expectTypeOf<TagListItem["group_id"]>().toEqualTypeOf<string | null>();
    expectTypeOf<TagListItem["group_position"]>().toEqualTypeOf<number>();
  });
});

describe("TagReadWithCount (per-tag entry in GET /api/tag-groups)", () => {
  it("extends TagRead with a REQUIRED model_count", () => {
    expectTypeOf<TagReadWithCount["model_count"]>().toEqualTypeOf<number>();
    expectTypeOf<TagReadWithCount["group_id"]>().toEqualTypeOf<string | null>();
  });
});

describe("TagGroupRead", () => {
  it("has id/slug/name_en/name_pl/position and tags: TagReadWithCount[]", () => {
    expectTypeOf<TagGroupRead["id"]>().toEqualTypeOf<string>();
    expectTypeOf<TagGroupRead["slug"]>().toEqualTypeOf<string>();
    expectTypeOf<TagGroupRead["name_en"]>().toEqualTypeOf<string>();
    expectTypeOf<TagGroupRead["name_pl"]>().toEqualTypeOf<string | null>();
    expectTypeOf<TagGroupRead["position"]>().toEqualTypeOf<number>();
    expectTypeOf<TagGroupRead["tags"]>().toEqualTypeOf<TagReadWithCount[]>();
  });
});

describe("TagGroupsResponse (GET /api/tag-groups)", () => {
  it("is structurally { groups: TagGroupRead[]; groupless: TagReadWithCount[] }", () => {
    expectTypeOf<TagGroupsResponse>().toEqualTypeOf<{
      groups: TagGroupRead[];
      groupless: TagReadWithCount[];
    }>();
  });

  it("accepts a real 42.2 wire body via `satisfies` (no cast)", () => {
    const wire = {
      groups: [
        {
          id: "11111111-1111-4111-8111-111111111111",
          slug: "material",
          name_en: "Material",
          name_pl: "Materiał",
          position: 0,
          tags: [
            {
              id: "22222222-2222-4222-8222-222222222222",
              slug: "pla",
              name_en: "PLA",
              name_pl: null,
              group_id: "11111111-1111-4111-8111-111111111111",
              group_position: 0,
              model_count: 12,
            },
          ],
        },
      ],
      groupless: [
        {
          id: "33333333-3333-4333-8333-333333333333",
          slug: "misc",
          name_en: "Misc",
          name_pl: null,
          group_id: null,
          group_position: 0,
          model_count: 3,
        },
      ],
    } satisfies TagGroupsResponse;

    expectTypeOf(wire).toMatchTypeOf<TagGroupsResponse>();
  });
});

describe("TagGroupSummary (flat admin write-response, Story 42.4)", () => {
  it("is the flat shape with NO tags[]", () => {
    expectTypeOf<TagGroupSummary>().toEqualTypeOf<{
      id: string;
      slug: string;
      name_en: string;
      name_pl: string | null;
      position: number;
    }>();
    expectTypeOf<TagGroupSummary>().not.toHaveProperty("tags");
  });
});
