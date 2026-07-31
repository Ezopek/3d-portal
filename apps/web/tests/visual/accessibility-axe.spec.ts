/*
 * Axe color-contrast scan, scoped to a curated page set, running once per
 * Playwright project (desktop-light/dark, mobile-light/dark — the existing
 * 4-project matrix from playwright.config.ts). Each project gets its own
 * scan automatically through Playwright's project sharding.
 *
 * Initiative 3 / Epic 5 / Story E5.6 (FR6). Level: warn — does NOT fail the
 * suite. Logs violations to console for operator review during Phase B
 * remediation. Story E5.17 promotes the assertion from console.warn to
 * `expect(violations).toHaveLength(0)` after Phase B leaves the baseline
 * at zero violations.
 *
 * Architecture references:
 *   - Decision H (dedicated axe spec, not per-page axe call)
 *   - Decision I (per-test escape hatches via `.exclude(...)` for known-noisy nodes)
 *
 * Scope is intentionally narrow: only `color-contrast` rule (NOT the full axe
 * a11y rule pack). Broader WCAG audit is out of Initiative 3 (NFR8 / scope-out).
 *
 * Exclude-list discipline (per Decision I): every `.exclude()` entry MUST
 * carry a one-line comment justifying the exclusion. Empty by default;
 * additions during Phase B require explicit operator approval.
 */

import type { Page } from "@playwright/test";

import { test, expect } from "./_test";
import AxeBuilder from "@axe-core/playwright";
import { stubSotDetail, stubSotList } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

interface Surface {
  label: string;
  needsAuth: boolean;
  /** Navigate and bring the surface into the state to be scanned. */
  reach: (page: Page) => Promise<void>;
  /**
   * Story 54.2 AC-7/AC-11 — MEASURED-AND-ROUTED contrast failures, not waivers.
   * Only the Initiative 26 entries carry one; the four Epic 5 pages keep the
   * E5.17 hard zero.
   *
   * This is deliberately NOT an `AxeBuilder.exclude(...)`: architecture
   * Decision I reserves the exclude-list for false positives and requires
   * explicit operator approval per entry. These are TRUE positives. The scan
   * still runs over them, still reports them, and the gate still fails on
   * anything NOT listed here — so it is a regression gate with a tracked known
   * set, the same shape `a11y-target-size.spec.ts` uses for its `routed:`
   * entries. Deleting an entry is how the owning story proves it closed one.
   */
  known?: KnownContrast[];
}

interface KnownContrast {
  /** Axe's measured pair, which is stable per theme. */
  fg: string;
  bg: string;
  /**
   * Which theme the pair belongs to. A light-theme colour pair CANNOT
   * reproduce on a `*-dark` project, so the stale-entry check below has to be
   * theme-scoped or it fires on every dark run for every light finding.
   */
  theme: "light" | "dark";
  /**
   * Projects on which the finding is REQUIRED to reproduce, for the stale-entry
   * check below. Defaults to all. Needed because a surface can be
   * viewport-gated: the browse rail is `lg:flex`, so its finding cannot appear
   * on a Pixel 5 viewport and demanding it there would fail the gate for the
   * wrong reason. Narrowing this field never weakens the UNROUTED check — that
   * one matches on the colour pair alone, on every project.
   */
  expectedOn?: RegExp;
  /** Owner + shipping story. Every entry is ledgered in `deferred-work.md`. */
  routed: string;
}

// The browse rail dims a zero-count category with `text-muted-foreground/60`
// (`BrowseCategoryList.tsx:140`) — a deliberate DESIGN.md:271 affordance whose
// opacity takes it under AA in BOTH themes. Shipped by the browse-rail story
// (Epic 51), so the finding is a defect in that story, not new 54.2 scope
// (`epics.md:4385`). The repair is a design call about how "empty" is signalled
// and is therefore routed, not made here.
const BROWSE_RAIL_DIMMED: KnownContrast[] = [
  {
    fg: "#939caa",
    bg: "#ffffff",
    theme: "light",
    // `lg:flex` — the rail does not render on the Pixel 5 projects at all.
    expectedOn: /^desktop-/,
    routed:
      "BrowseCategoryList.tsx:140 `text-muted-foreground/60` zero-count label," +
      " measured 2.77:1 (light). Owner: deferred-work.md (Story 54.2 audit)," +
      " shipping story: Epic 51 browse rail.",
  },
  {
    fg: "#5f6b7f",
    bg: "#0f1729",
    theme: "dark",
    expectedOn: /^desktop-/,
    routed:
      "BrowseCategoryList.tsx:140 `text-muted-foreground/60` zero-count label," +
      " measured 3.31:1 (dark). Owner: deferred-work.md (Story 54.2 audit)," +
      " shipping story: Epic 51 browse rail.",
  },
];

// The `success` outline badge composites #21c45d on #e9f9ef = 2.11:1 in the
// light theme. This is the shared `ui/badge` success variant, pre-Initiative-26
// and app-wide: repairing it is a design-system token change with a blast
// radius far outside this story's envelope (§ 0.3 — "a sprawling diff is a
// signal that the audit turned into a redesign"). Routed.
const SUCCESS_BADGE: KnownContrast = {
  fg: "#21c45d",
  bg: "#e9f9ef",
  theme: "light",
  routed:
    "ui/badge `success` outline variant, measured 2.11:1 (light). App-wide" +
    " design-system token. Owner: deferred-work.md (Story 54.2 audit).",
};

// `ScopeChip.tsx:32` — the chip's text action, `text-primary` on the chip's own
// `bg-primary/10`. 4.49:1 against a 4.5:1 floor: a real fail, by 0.01, and one
// no threshold-based gate would ever have surfaced. Initiative 26's own
// (Epic 51 category scope). Routed rather than fixed here because the repair is
// a primary-token choice, not an opacity slip.
const SCOPE_CHIP_ACTION: KnownContrast = {
  fg: "#2463eb",
  bg: "#e9effd",
  theme: "light",
  routed:
    "ScopeChip.tsx:32 chip action `text-primary` on `bg-primary/10`, measured" +
    " 4.49:1 vs the 4.5:1 floor (light). Owner: deferred-work.md (Story 54.2" +
    " audit), shipping story: Epic 51 category scope.",
};

const PAGES: Surface[] = [
  // ---- The Epic 5 / Story E5.6 set, unchanged. Deliberately unstubbed: the
  // `_test.ts` catch-all 404s every `/api/*`, so these scan the empty/error
  // states, which is the coverage E5.17 promoted to a hard assertion.
  {
    label: "home (catalog)",
    needsAuth: false,
    reach: async (page) => {
      await page.goto("/");
    },
  },
  {
    label: "catalog list",
    needsAuth: false,
    reach: async (page) => {
      await page.goto("/catalog");
    },
  },
  {
    label: "admin models",
    needsAuth: true,
    reach: async (page) => {
      await page.goto("/admin/models");
    },
  },
  {
    label: "admin tags",
    needsAuth: true,
    reach: async (page) => {
      await page.goto("/admin/tags");
    },
  },

  // ---- Story 54.2 / AC-7 — the Initiative 26 surfaces and STATES. § 2 V-6
  // measured that none of them was scanned: the four entries above are all
  // pre-Initiative-26 and none of them is an OPEN OVERLAY, where the
  // `bg-gallery-control` / chip / sheet treatments actually live. These are
  // stubbed, because an empty catalog paints almost no colour and a scan of it
  // proves almost nothing.
  //
  // Axe's `color-contrast` rule reports `incomplete` (not `violation`) for text
  // over a translucent layer it cannot resolve, and an `incomplete` fails
  // nothing — so these entries do NOT discharge the V-6 finding on their own.
  // The composited overlay copy is measured directly in
  // `a11y-contrast-gate.spec.ts`. These entries close the PAGE-SET half of
  // AC-7: the opaque chrome on the journey is now scanned where it was not.
  {
    label: "catalog list (stubbed data)",
    needsAuth: false,
    known: [...BROWSE_RAIL_DIMMED, SUCCESS_BADGE],
    reach: async (page) => {
      await stubSotList(page);
      await page.goto("/catalog");
    },
  },
  {
    label: "catalog list — Filters panel open",
    needsAuth: false,
    known: [...BROWSE_RAIL_DIMMED, SUCCESS_BADGE],
    reach: async (page) => {
      await stubSotList(page);
      await page.goto("/catalog");
      await waitForReady(page);
      // catalog.filters.openFilters = "Filtry" (playwright.config.ts forces pl-PL).
      await page.getByRole("button", { name: "Filtry", exact: true }).click();
      await page.locator('[data-slot="sheet-content"]').waitFor({ state: "visible" });
    },
  },
  {
    label: "category browse (/categories/$slug)",
    needsAuth: false,
    known: [...BROWSE_RAIL_DIMMED, SUCCESS_BADGE, SCOPE_CHIP_ACTION],
    reach: async (page) => {
      await stubSotList(page);
      await page.goto("/categories/uchwyty");
    },
  },
  {
    label: "model detail (/catalog/$id)",
    needsAuth: false,
    known: [SUCCESS_BADGE],
    reach: async (page) => {
      await stubSotDetail(page, { imageCount: 2 });
      await page.goto(`/catalog/${MODEL_ID}`);
    },
  },
  {
    label: "model detail — photo lightbox open",
    needsAuth: false,
    known: [SUCCESS_BADGE],
    reach: async (page) => {
      await stubSotDetail(page, { imageCount: 2 });
      await page.goto(`/catalog/${MODEL_ID}`);
      await waitForReady(page);
      await page.getByTestId("gallery-fullscreen-trigger").click();
      await page.getByTestId("image-viewer-root").waitFor({ state: "visible" });
    },
  },
  {
    label: "admin categories",
    needsAuth: true,
    reach: async (page) => {
      await page.goto("/admin/categories");
    },
  },
];

for (const { label, needsAuth, reach, known: allKnown = [] } of PAGES) {
  test(`axe color-contrast — ${label}`, async ({ page }, testInfo) => {
    // `desktop-light` / `desktop-dark` / `mobile-light` / `mobile-dark`.
    const theme = testInfo.project.name.endsWith("-dark") ? "dark" : "light";
    const known = allKnown.filter((k) => k.theme === theme);
    if (needsAuth) await loginAsAdmin(page);
    await reach(page);
    await waitForReady(page);

    const result = await new AxeBuilder({ page })
      .withRules(["color-contrast"])
      // Exclude-list — add entries here when a real false-positive justifies it.
      // Per Decision I: one-line WHY comment per entry. Currently empty, and
      // Story 54.2 deliberately kept it empty: its findings are TRUE positives
      // and are tracked through the surface's `known` list instead.
      .analyze();

    // Flatten to individual failing NODES. A violation groups every node that
    // trips the same rule, so asserting on `violations.length` would let a new
    // failure hide inside an already-known one.
    const failing = result.violations.flatMap((v) =>
      v.nodes.map((n) => {
        const data = n.any.find((c) => c.id === "color-contrast")?.data as
          | { fgColor?: string; bgColor?: string; contrastRatio?: number }
          | undefined;
        return {
          rule: v.id,
          target: n.target.join(" > "),
          fg: (data?.fgColor ?? "?").toLowerCase(),
          bg: (data?.bgColor ?? "?").toLowerCase(),
          ratio: data?.contrastRatio ?? NaN,
        };
      }),
    );

    const unknown = failing.filter(
      (f) => !known.some((k) => k.fg.toLowerCase() === f.fg && k.bg.toLowerCase() === f.bg),
    );

    // Story E5.17 PROMOTION (closing gate for Epic 5): hard assertion, kept.
    // Story 54.2 AC-7 grew this set from 4 surfaces to 10 — adding the
    // Initiative 26 routes AND two OPEN-OVERLAY states, which § 2 V-6 measured
    // as entirely unscanned — and fixed the stale "5 pages" count this comment
    // used to carry. Anything not in the surface's routed `known` list fails.
    expect(
      unknown.map((f) => `${f.target} — ${f.fg} on ${f.bg} = ${f.ratio}:1`).sort(),
      `[axe color-contrast ${label}] unrouted violation(s). Either fix the` +
        ` contrast or add a KnownContrast entry with an owner and a` +
        ` deferred-work.md routing — never an AxeBuilder.exclude(), which` +
        ` architecture Decision I reserves for false positives.`,
    ).toEqual([]);

    // Non-vacuity in the other direction: a `known` entry that no longer fires
    // means the finding was FIXED and the routing is now stale. Report it, so
    // the ledger closes instead of quietly accumulating dead waivers.
    const stale = known
      .filter((k) => (k.expectedOn ?? /./).test(testInfo.project.name))
      .filter(
        (k) => !failing.some((f) => f.fg === k.fg.toLowerCase() && f.bg === k.bg.toLowerCase()),
      );
    expect(
      stale.map((k) => `${k.fg} on ${k.bg} — ${k.routed}`),
      `[axe color-contrast ${label}] routed finding(s) no longer reproduce.` +
        ` Remove the KnownContrast entry and close the deferred-work.md entry.`,
    ).toEqual([]);
  });
}
