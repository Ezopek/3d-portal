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

import { ModuleRail } from "./ModuleRail";

afterEach(cleanup);

beforeAll(async () => {
  await i18n.changeLanguage("en");
  vi.stubGlobal("scrollTo", () => {});
});

const MODULE_PATHS = [
  "/catalog",
  "/queue",
  "/spools",
  "/printer",
  "/requests",
] as const;

async function mountAt(url: string) {
  const root = createRootRoute({ component: () => <ModuleRail /> });
  const children = [
    ...MODULE_PATHS.map((path) =>
      createRoute({
        getParentRoute: () => root,
        path,
        component: () => <Outlet />,
      }),
    ),
    createRoute({
      getParentRoute: () => root,
      path: "/categories/$slug",
      component: () => <Outlet />,
    }),
  ];
  const router = createRouter({
    routeTree: root.addChildren(children),
    history: createMemoryHistory({ initialEntries: [url] }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
}

/** Both viewports render a row per module, so each label resolves to 2 anchors. */
function catalogRows() {
  return screen.getAllByRole("link", { name: "Catalog" });
}

const ACTIVE_DESKTOP = "ring-primary";
const ACTIVE_MOBILE = "text-primary";

describe("ModuleRail module-active predicate", () => {
  it("marks Catalog active on /catalog, on both viewports", async () => {
    await mountAt("/catalog");

    const rows = catalogRows();
    expect(rows).toHaveLength(2);
    expect(rows[0]?.className).toContain(ACTIVE_DESKTOP);
    expect(rows[1]?.className).toContain(ACTIVE_MOBILE);
  });

  // Story 51.2 D-8 / AC-17 — `/categories/{slug}` is the catalogue's canonical
  // browse URL now. Without the widened predicate `pathname.startsWith(to)`
  // matches NO module there, so the desktop rail and the mobile bottom bar both
  // go dark on the very route this story introduces.
  it("marks Catalog active on /categories/<slug>, on both viewports", async () => {
    await mountAt("/categories/uchwyty");

    const rows = catalogRows();
    expect(rows).toHaveLength(2);
    expect(rows[0]?.className).toContain(ACTIVE_DESKTOP);
    expect(rows[1]?.className).toContain(ACTIVE_MOBILE);
  });

  it("leaves every other module inactive on /categories/<slug>", async () => {
    await mountAt("/categories/uchwyty");

    for (const label of ["Queue", "Spools", "Printer", "Requests"]) {
      for (const row of screen.getAllByRole("link", { name: label })) {
        expect(row.className).not.toContain(ACTIVE_DESKTOP);
        expect(row.className).not.toContain(ACTIVE_MOBILE);
      }
    }
  });

  it("does not leak the widened prefix onto a different module's route", async () => {
    await mountAt("/queue");

    for (const row of catalogRows()) {
      expect(row.className).not.toContain(ACTIVE_DESKTOP);
      expect(row.className).not.toContain(ACTIVE_MOBILE);
    }
  });

  it("keeps the tab SET untouched — five modules, no addition, removal or rename", async () => {
    // The Story 51.3 `Ask First` boundary is about the mobile tab set, which
    // this story must not touch (D-8 boundary check).
    await mountAt("/categories/uchwyty");

    for (const label of ["Catalog", "Queue", "Spools", "Printer", "Requests"]) {
      expect(screen.getAllByRole("link", { name: label })).toHaveLength(2);
    }
    // 5 modules × 2 viewports, and nothing else.
    expect(screen.getAllByRole("link")).toHaveLength(10);
  });
});
