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

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { loginAsAdmin, waitForReady } from "./helpers";

const PAGES = [
  { path: "/", label: "home (catalog)", needsAuth: false },
  { path: "/catalog", label: "catalog list", needsAuth: false },
  { path: "/admin/models", label: "admin models", needsAuth: true },
  { path: "/admin/tags", label: "admin tags", needsAuth: true },
  { path: "/admin/categories", label: "admin categories", needsAuth: true },
];

for (const { path, label, needsAuth } of PAGES) {
  test(`axe color-contrast — ${label}`, async ({ page }) => {
    if (needsAuth) await loginAsAdmin(page);
    await page.goto(path);
    await waitForReady(page);

    const result = await new AxeBuilder({ page })
      .withRules(["color-contrast"])
      // Exclude-list — add entries here when a real false-positive justifies it.
      // Per Decision I: one-line WHY comment per entry. Currently empty.
      .analyze();

    // Story E5.17 PROMOTION (closing gate for Epic 5): hard assertion.
    // Phase B remediation is complete; the baseline at this point is zero
    // violations across all 4 projects × 5 pages. Any regression breaks
    // the visual-regression suite contract. Use AxeBuilder.exclude(...)
    // above per architecture Decision I if a real false-positive emerges.
    expect(
      result.violations,
      `[axe color-contrast ${label}] violation(s):\n` +
        result.violations
          .map(
            (v) =>
              `  - ${v.id}: ${v.description}\n    nodes: ${v.nodes
                .map((n) => n.target.join(" > "))
                .join(", ")}`,
          )
          .join("\n"),
    ).toHaveLength(0);
  });
}
