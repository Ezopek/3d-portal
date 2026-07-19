import { defaultParseSearch, defaultStringifySearch } from "@tanstack/react-router";
import { describe, expect, it } from "vitest";

import { Route as LoginRoute } from "@/routes/login";

import { Route, type CatalogSearch } from "./index";

// TanStack types `Route.options.validateSearch` as a Validator union
// (`Constrain<TSearchValidator, AnyValidator, DefaultValidator>`), so it is not
// directly callable. The established repo precedent (login.test.tsx:341) unwraps
// it with a cast to its declared signature. This cast preserves the
// `CatalogSearch` RETURN type, so it does NOT mask the type-level RED for the
// new `tag_match`/`untagged` fields (property access below still fails to
// compile until the interface gains them); it only makes the validator callable.
const v = Route.options.validateSearch as (raw: Record<string, unknown>) => CatalogSearch;

// Same accessor precedent for the login route (test-only; no login prod change).
const loginValidate = LoginRoute.options.validateSearch as (
  raw: Record<string, unknown>,
) => { next?: string; reset?: "success" };

// Canonical 8-4-4-4-12 UUIDs (as minted by `Tag.id`).
const UUID_A = "11111111-1111-4111-8111-111111111111";
const UUID_B = "22222222-2222-4222-8222-222222222222";
const UUID_UNKNOWN = "99999999-9999-4999-8999-999999999999";
const UUID_UPPER = "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE";

describe("catalog validateSearch — tag_match (Story 43.3 AC #1, Story 44.2 normalization)", () => {
  it("normalizes the non-default 'any' value when ≥2 tags are selected", () => {
    expect(v({ tag_match: "any", tag_ids: [UUID_A, UUID_B] })).toEqual({
      tag_match: "any",
      tag_ids: [UUID_A, UUID_B],
    });
    expect(v({ tag_match: "any", tag_ids: [UUID_A, UUID_B] }).tag_match).toBe("any");
  });

  it("omits the 'all' default", () => {
    expect(v({ tag_match: "all", tag_ids: [UUID_A, UUID_B] })).toEqual({
      tag_ids: [UUID_A, UUID_B],
    });
  });

  it("drops unknown / non-string values", () => {
    expect(v({ tag_match: "both", tag_ids: [UUID_A, UUID_B] })).toEqual({
      tag_ids: [UUID_A, UUID_B],
    });
    expect(v({ tag_match: "AND", tag_ids: [UUID_A, UUID_B] })).toEqual({
      tag_ids: [UUID_A, UUID_B],
    });
    expect(v({ tag_match: 5, tag_ids: [UUID_A, UUID_B] })).toEqual({
      tag_ids: [UUID_A, UUID_B],
    });
    expect(v({})).toEqual({});
  });

  // Story 44.2: `tag_match` is only meaningful with ≥2 tags (AND vs OR is a
  // no-op below that), and the FilterRibbon toggle that sets it hides at <2
  // tags. validateSearch drops a stranded, un-clearable `tag_match` on
  // hand-crafted URLs so URL state stays consistent with `setFilters`.
  it("drops 'any' when fewer than 2 tags are selected", () => {
    expect(v({ tag_match: "any" })).toEqual({});
    expect(v({ tag_match: "any", tag_ids: [UUID_A] })).toEqual({ tag_ids: [UUID_A] });
  });

  it("drops 'any' when tag_ids are present in the raw input but none survive validation", () => {
    expect(v({ tag_match: "any", tag_ids: ["not-a-uuid", ""] })).toEqual({});
  });
});

describe("catalog validateSearch — untagged (AC #2)", () => {
  it("accepts boolean true and string 'true'", () => {
    expect(v({ untagged: true })).toEqual({ untagged: true });
    expect(v({ untagged: "true" })).toEqual({ untagged: true });
    // Type-level RED anchor: `.untagged` is absent from CatalogSearch until T2.
    expect(v({ untagged: true }).untagged).toBe(true);
  });

  it("drops false / falsey / non-boolean values", () => {
    expect(v({ untagged: false })).toEqual({});
    expect(v({ untagged: "false" })).toEqual({});
    expect(v({ untagged: "0" })).toEqual({});
    expect(v({ untagged: "" })).toEqual({});
    expect(v({ untagged: 1 })).toEqual({});
  });
});

describe("catalog validateSearch — tag_ids hardening [H] (AC #3)", () => {
  it("preserves canonical UUIDs in first-seen order", () => {
    expect(v({ tag_ids: [UUID_A, UUID_B] })).toEqual({ tag_ids: [UUID_A, UUID_B] });
  });

  it("coerces a single UUID string to a one-element array", () => {
    expect(v({ tag_ids: UUID_A })).toEqual({ tag_ids: [UUID_A] });
  });

  it("dedupes preserving first-seen order", () => {
    expect(v({ tag_ids: [UUID_A, UUID_A, UUID_B] })).toEqual({ tag_ids: [UUID_A, UUID_B] });
  });

  it("drops non-UUID and empty entries", () => {
    expect(v({ tag_ids: [UUID_A, "not-a-uuid", "", UUID_B] })).toEqual({
      tag_ids: [UUID_A, UUID_B],
    });
  });

  it("omits the key when nothing canonical remains", () => {
    expect(v({ tag_ids: ["not-a-uuid"] })).toEqual({});
    expect(v({ tag_ids: [""] })).toEqual({});
    expect(v({ tag_ids: [] })).toEqual({});
  });

  it("retains unknown-but-valid canonical UUIDs (backend owns match semantics)", () => {
    expect(v({ tag_ids: [UUID_UNKNOWN] })).toEqual({ tag_ids: [UUID_UNKNOWN] });
  });

  it("accepts upper-case canonical UUIDs (UUID_RE is case-insensitive)", () => {
    expect(v({ tag_ids: [UUID_UPPER] })).toEqual({ tag_ids: [UUID_UPPER] });
  });

  it("trims surrounding whitespace before matching", () => {
    expect(v({ tag_ids: [` ${UUID_A} `] })).toEqual({ tag_ids: [UUID_A] });
  });
});

describe("catalog validateSearch — serialization & omit-default (AC #4, #5)", () => {
  it("round-trips through the TanStack default (de)serializers", () => {
    const round = { tag_ids: [UUID_A, UUID_B], tag_match: "any", untagged: true };
    const qs = defaultStringifySearch(round);
    // Canonical browser wire = URL-encoded JSON array (`%5B` = `[`), NOT repeated params.
    expect(qs).toContain("tag_ids=%5B");
    expect(qs).toContain("tag_match=any");
    expect(qs).toContain("untagged=true");
    expect(v(defaultParseSearch(qs))).toEqual(round);
  });

  it("omits defaults from the serialized normalized object", () => {
    const normalized = v({ tag_match: "all", untagged: false, tag_ids: [] });
    expect(normalized).toEqual({});
    const qs = defaultStringifySearch(normalized);
    expect(qs).not.toContain("tag_match");
    expect(qs).not.toContain("untagged");
    expect(qs).not.toContain("tag_ids");
  });

  it("normalizes a parsed default-carrying query back to empty", () => {
    expect(v(defaultParseSearch("?tag_match=all&untagged=false"))).toEqual({});
  });
});

describe("catalog validateSearch — coexistence with category_id + unrelated keys (AC #6)", () => {
  it("preserves category_id and every unrelated key alongside the new params", () => {
    const full = {
      category_id: "cat-1",
      // Two tags so the non-default `tag_match` survives normalization
      // (Story 44.2 requires ≥2 tags for `tag_match` to be meaningful).
      tag_ids: [UUID_A, UUID_B],
      tag_match: "any",
      untagged: true,
      q: "vase",
      status: "printed",
      source: "printables",
      sort: "name_asc",
      page: 2,
    };
    expect(v(full)).toEqual(full);
  });

  it("keeps a category-only URL valid", () => {
    expect(v({ category_id: "cat-1" })).toEqual({ category_id: "cat-1" });
  });
});

describe("catalog params survive login redirect `next` (AC #7, test-only)", () => {
  it("keeps a catalog URL carrying the new params as a safe next", () => {
    const next = "/catalog?tag_ids=%5B%22" + UUID_A + "%22%5D&tag_match=any&untagged=true";
    expect(loginValidate({ next })).toEqual({ next });
  });
});
