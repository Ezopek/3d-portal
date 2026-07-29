import type {
  BrowseCategoryAdminRead,
  OverCategorizedModelRead,
  OverCategorizedResponse,
  TagGroupsResponse,
  TagReadWithCount,
} from "@/lib/api-types";

import { TINY_MAX } from "./curationThresholds";
import { fieldsSimilar, normalizeTagText } from "./duplicateTags";

// Story 52.3 — the six curation-QA checks, as a PURE function over data the
// `/admin/categories` route already holds or loads from shipped endpoints.
// No hooks, no JSX, no fetch: everything here is separately unit-testable.
//
// Six checks, never a seventh (D-3). "Behaving like a narrow tag" is what the
// admin CONCLUDES from the tiny-category and label-collision rows — it is not
// its own detector.
//
// Every finding is advisory. Nothing here is an error, a failure or a defect,
// and no category membership is ever inferred from tags in either direction.

/**
 * Rows rendered per check before the overflow line takes over (D-8).
 *
 * This serves AC-8's mount position: the panel sits between the page header and
 * the category list, so it is an advisory PREFACE to the primary surface. Six
 * checks x 5 rows already fills a viewport against the shipped eight-category
 * vocabulary; letting any single check run unbounded would push the category
 * list — the thing the panel is advising about — below the fold, inverting the
 * advisory-not-primary posture. Deliberately NOT aligned to the suggestion
 * panel's 8-row cap, which is sized for a listbox that owns its whole popover.
 */
export const ROW_CAP = 5;

export type CurationCheckKind =
  | "empty_category"
  | "tiny_category"
  | "label_collision"
  | "over_categorized"
  | "uncategorized_models"
  | "ungrouped_tags";

export interface EmptyCategoryFinding {
  kind: "empty_category";
  id: string;
  category: BrowseCategoryAdminRead;
}

export interface TinyCategoryFinding {
  kind: "tiny_category";
  id: string;
  category: BrowseCategoryAdminRead;
}

export interface LabelCollisionFinding {
  kind: "label_collision";
  id: string;
  category: BrowseCategoryAdminRead;
  tag: TagReadWithCount;
  /** The tag's group, or null for a groupless tag — which renders with NO suffix. */
  group: { name_en: string; name_pl: string | null } | null;
}

export interface OverCategorizedFinding {
  kind: "over_categorized";
  id: string;
  model: OverCategorizedModelRead;
}

export interface CountFinding {
  kind: "uncategorized_models" | "ungrouped_tags";
  id: string;
  count: number;
}

export type CurationFinding =
  | EmptyCategoryFinding
  | TinyCategoryFinding
  | LabelCollisionFinding
  | OverCategorizedFinding
  | CountFinding;

export interface CurationCheckGroup {
  kind: CurationCheckKind;
  /** At most ROW_CAP rows. */
  rows: CurationFinding[];
  /** The TRUE finding count for this check — what the overflow line reports. */
  total: number;
}

export interface CurationResult {
  /** Non-empty checks only, in the D-7 order. */
  groups: CurationCheckGroup[];
  /** Findings, not rendered rows (AC-9/AC-17). */
  totalFindings: number;
}

export interface CurationInputs {
  categories: BrowseCategoryAdminRead[] | undefined;
  tagGroups: TagGroupsResponse | undefined;
  overCategorized: OverCategorizedResponse | undefined;
  uncategorizedTotal: number | undefined;
}

interface TagWithGroup {
  tag: TagReadWithCount;
  group: { name_en: string; name_pl: string | null } | null;
}

/** Every tag in the vocabulary, each carrying its group (null when groupless). */
function flattenTags(tagGroups: TagGroupsResponse): TagWithGroup[] {
  const out: TagWithGroup[] = [];
  for (const group of tagGroups.groups) {
    for (const tag of group.tags) {
      out.push({ tag, group: { name_en: group.name_en, name_pl: group.name_pl } });
    }
  }
  for (const tag of tagGroups.groupless) {
    out.push({ tag, group: null });
  }
  return out;
}

/**
 * D-4 — reuses the shipped similarity from `duplicateTags.ts` unchanged:
 * normalize (NFD, l/L map, lowercase, collapse whitespace) then compare with the
 * length-scaled Levenshtein threshold. en-vs-en and pl-vs-pl INDEPENDENTLY,
 * never en-vs-pl, and only when both sides are non-empty — so a null or empty
 * `name_pl` can never produce a finding.
 */
function labelsCollide(category: BrowseCategoryAdminRead, tag: TagReadWithCount): boolean {
  const catEn = normalizeTagText(category.name_en);
  const tagEn = normalizeTagText(tag.name_en);
  if (catEn !== "" && tagEn !== "" && fieldsSimilar(catEn, tagEn)) return true;

  const catPl = category.name_pl !== null ? normalizeTagText(category.name_pl) : "";
  const tagPl = tag.name_pl !== null ? normalizeTagText(tag.name_pl) : "";
  if (catPl !== "" && tagPl !== "" && fieldsSimilar(catPl, tagPl)) return true;

  return false;
}

function group(kind: CurationCheckKind, findings: CurationFinding[]): CurationCheckGroup | null {
  if (findings.length === 0) return null;
  return { kind, rows: findings.slice(0, ROW_CAP), total: findings.length };
}

/**
 * Compute the ordered curation findings. Every input is independently optional:
 * a source that has not resolved (or failed with no cache) simply contributes
 * nothing, so the panel can still render what the other sources produced. The
 * caller — never this function — decides whether that partial state is honest
 * to present (D-6).
 */
export function computeCurationChecks({
  categories,
  tagGroups,
  overCategorized,
  uncategorizedTotal,
}: CurationInputs): CurationResult {
  const cats = categories ?? [];

  // (a) + (b). `model_count === 0` is EMPTY and produces the (a) row only —
  // never also a tiny row, which starts at 1.
  const empty: CurationFinding[] = cats
    .filter((c) => c.model_count === 0)
    .map((c) => ({ kind: "empty_category", id: `empty:${c.id}`, category: c }));

  const tiny: CurationFinding[] = cats
    .filter((c) => c.model_count >= 1 && c.model_count <= TINY_MAX)
    .map((c) => ({ kind: "tiny_category", id: `tiny:${c.id}`, category: c }));

  // (c). Ordered by (category position, tag name) — the categories arrive in
  // server (position, slug) order, and the tags are sorted per category.
  const collisions: CurationFinding[] = [];
  if (tagGroups) {
    const tags = flattenTags(tagGroups).sort((x, y) => {
      const byName = x.tag.name_en.localeCompare(y.tag.name_en);
      return byName !== 0 ? byName : x.tag.slug.localeCompare(y.tag.slug);
    });
    for (const category of cats) {
      for (const { tag, group: tagGroup } of tags) {
        if (!labelsCollide(category, tag)) continue;
        collisions.push({
          kind: "label_collision",
          // One row per (category, tag) pair — the pair is visited once, so no
          // pair can be reported twice.
          id: `collision:${category.id}:${tag.id}`,
          category,
          tag,
          group: tagGroup,
        });
      }
    }
  }

  // (d). Already ordered (category_count DESC, slug ASC) by the server.
  const over: CurationFinding[] = (overCategorized?.items ?? []).map((model) => ({
    kind: "over_categorized",
    id: `over:${model.model_id}`,
    model,
  }));
  // `total` can exceed `items.length` (the endpoint caps items at `limit`), so
  // the honest finding count for this check is the server's total.
  const overTotal = overCategorized?.total ?? 0;

  // (e) + (f). Single count rows, absent at zero.
  const uncategorized: CurationFinding[] =
    uncategorizedTotal !== undefined && uncategorizedTotal > 0
      ? [{ kind: "uncategorized_models", id: "uncategorized", count: uncategorizedTotal }]
      : [];

  // No "user-facing" filter is applied: neither Tag nor TagGroup carries a
  // lifecycle or hidden flag, so every groupless tag IS user-facing.
  const ungroupedCount = tagGroups?.groupless.length ?? 0;
  const ungrouped: CurationFinding[] =
    ungroupedCount > 0
      ? [{ kind: "ungrouped_tags", id: "ungrouped", count: ungroupedCount }]
      : [];

  // D-7 — a total order that does not depend on which finding happens to exist:
  // category-level, then cross-entity, then model-level, then the two
  // aggregates. A recorded deviation from the mockup's narrative row sequence,
  // on determinism grounds; the per-row CONTENT contract is followed exactly.
  const groups = [
    group("empty_category", empty),
    group("tiny_category", tiny),
    group("label_collision", collisions),
    over.length > 0 ? { kind: "over_categorized" as const, rows: over.slice(0, ROW_CAP), total: overTotal } : null,
    group("uncategorized_models", uncategorized),
    group("ungrouped_tags", ungrouped),
  ].filter((g): g is CurationCheckGroup => g !== null);

  const totalFindings = groups.reduce((sum, g) => sum + g.total, 0);

  return { groups, totalFindings };
}
