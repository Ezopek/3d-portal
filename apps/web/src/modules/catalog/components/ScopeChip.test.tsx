import "@/locales/i18n";

import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";

import { ScopeChip } from "./ScopeChip";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
  vi.stubGlobal("scrollTo", () => {});
});

// The chip's escape is a real anchor (D-5: a scope change is a route change), so
// the component needs a router in context even for presentational assertions.
// Deliberately a LOCAL two-route tree rather than the app's: this file is the
// unit surface for the chip, and coupling it to the whole route tree would make
// an unrelated route change able to break it. The cross-route behaviour is
// covered end-to-end in CatalogList.test.tsx (§7.2).
// A live search layer with BOTH something that must survive the escape (`q`)
// and something that must not (`page`), so the preservation assertions cannot
// pass vacuously.
const SEARCH = { q: "vase", page: 3 } as const;

async function renderChip(props: {
  label: string;
  otherConstraintsActive: boolean;
}) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: () => null,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const scoped = createRoute({
    getParentRoute: () => root,
    path: "/categories/$slug",
    component: () => <ScopeChip {...props} search={SEARCH} />,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const router = createRouter({
    routeTree: root.addChildren([catalog, scoped]),
    history: createMemoryHistory({
      initialEntries: ["/categories/uchwyty?q=vase&page=3"],
    }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
}

const SCOPE_ROW = { name: /Active category: Mounts/ };

describe("ScopeChip (Story 51.2)", () => {
  it("labels the row with the active-scope accessible name and renders the category label", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: false });

    // AC-28 — the row states WHERE you are, not merely what it contains.
    const row = screen.getByRole("group", SCOPE_ROW);
    expect(row).toBeTruthy();
    expect(row.textContent).toContain("Mounts");
  });

  it("labels the action 'Clear category' when the scope is the only constraint", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: false });

    // AC-9 — `filtersActive === false`: nothing else would survive the escape,
    // so promising "Search entire catalog" would over-state what happens.
    expect(screen.getByRole("link", { name: "Clear category" })).toBeTruthy();
    expect(
      screen.queryByRole("link", { name: "Search entire catalog" }),
    ).toBeNull();
  });

  it("labels the action 'Search entire catalog' when other constraints are active", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: true });

    // AC-9 / EXPERIENCE.md:203 — the ratified terminology. Never "Clear", which
    // would be a lie: the query and the tags survive.
    expect(
      screen.getByRole("link", { name: "Search entire catalog" }),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Clear category" })).toBeNull();
  });

  it("exposes exactly ONE action, as a text-labelled link — never a bare ×, never a checkbox", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: true });

    // AC-8 / DESIGN.md:274, :296.
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]?.textContent?.trim()).toBe("Search entire catalog");
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    // The chip is a place, not a toggle: no × glyph in any of its variants.
    expect(screen.getByRole("group", SCOPE_ROW).textContent).not.toMatch(
      /[×✕✖x]\s*$/,
    );
  });

  it("points the escape at /catalog, preserving every other URL layer and resetting page", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: true });

    // AC-10 — the escape clears ONLY the scope. The scope lives in the path, so
    // leaving the path is the whole of the clearing; `q` rides along untouched.
    const href = screen
      .getByRole("link", { name: "Search entire catalog" })
      .getAttribute("href");
    expect(href).toContain("/catalog");
    expect(href).toContain("q=vase");
    expect(href).not.toContain("category=");
    expect(href).not.toContain("page=");
  });

  it("renders the raw slug verbatim when the caller could not resolve a label", async () => {
    // AC-11 — an unknown slug is a rendered value, not an error surface (D-7).
    await renderChip({ label: "nie-ma-takiej", otherConstraintsActive: false });

    const row = screen.getByRole("group", {
      name: /Active category: nie-ma-takiej/,
    });
    expect(row.textContent).toContain("nie-ma-takiej");
    expect(screen.getByRole("link", { name: "Clear category" })).toBeTruthy();
  });

  it("carries the location token set and never the chosen-constraint accent vocabulary", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: false });

    // AC-12 / AC-33 — DESIGN.md:84-95, :203-204, :250, :258.
    const row = screen.getByRole("group", SCOPE_ROW);
    expect(row.className).toContain("bg-primary/10");
    expect(row.className).toContain("ring-1");
    expect(row.className).toContain("ring-inset");
    expect(row.className).toContain("ring-primary");
    // rounded-md, deliberately NOT rounded-full: the tag pill owns that shape,
    // and the contrast is a free reinforcement of place-vs-constraint.
    expect(row.className).toContain("rounded-md");
    expect(row.className).not.toContain("rounded-full");
    expect(row.className).toContain("min-h-6");
    // Flat, never floating.
    expect(row.className).not.toMatch(/\bshadow/);
    // `accent` is the selected-tag vocabulary; using it here would collide.
    expect(row.className).not.toMatch(/accent/);
  });

  it("gives the action a ≥24px keyboard-reachable target with a visible focus affordance", async () => {
    await renderChip({ label: "Mounts", otherConstraintsActive: false });

    // AC-29 — WCAG 2.2 SC 2.5.8; min-h-6/min-w-6 is 24px at the default scale.
    const action = screen.getByRole("link", { name: "Clear category" });
    expect(action.className).toContain("min-h-6");
    expect(action.className).toContain("min-w-6");
    expect(action.className).toMatch(/focus-visible:/);
    // No hover-only affordance: the label is always rendered text.
    expect(action.textContent?.trim()).toBe("Clear category");
  });
});
