import "@/locales/i18n";

import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import i18n from "@/locales/i18n";
import { AdminTabs } from "@/modules/admin/AdminTabs";

const EN_KEYS = en as Record<string, string>;

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
});

// AdminTabs renders TanStack <Link>s, so it needs a router context with the six
// admin routes registered for `to` to resolve without a "could not resolve"
// warning. We register minimal placeholder routes matching the tab targets.
function mount(node: ReactNode) {
  const root = createRootRoute({ component: () => <>{node}</> });
  const paths = [
    "/admin/users",
    "/admin/invites",
    "/admin/profile-library",
    "/admin/profile-offers",
    "/admin/queues",
    "/admin/tag-groups",
  ];
  const children = paths.map((path) =>
    createRoute({
      getParentRoute: () => root,
      path,
      component: () => null,
    }),
  );
  const router = createRouter({
    routeTree: root.addChildren(children),
    history: createMemoryHistory({ initialEntries: ["/admin/tag-groups"] }),
  });
  return render(<RouterProvider router={router} />);
}

describe("AdminTabs — nav landmark labelling (Story 46.1 repair)", () => {
  it("labels the tablist with a generic admin-navigation label, not a per-tab label", async () => {
    mount(<AdminTabs activeTab="tag-groups" />);

    const nav = await waitFor(() => screen.getByRole("tablist"));
    const label = nav.getAttribute("aria-label");
    // The label must be the truthful generic key, NOT any individual tab's
    // label (the pre-repair bug hardcoded it to the "Users" tab label).
    expect(label).toBe(EN_KEYS["admin.tabs.nav_aria_label"]);
    expect(label).not.toBe(EN_KEYS["admin.tabs.users"]);
  });

  it("uses the same generic label regardless of which tab is active", async () => {
    mount(<AdminTabs activeTab="users" />);

    const nav = await waitFor(() => screen.getByRole("tablist"));
    // Even when Users is the active tab, the nav label stays generic — it does
    // not echo the active tab, so the landmark name is truthful on every screen.
    expect(nav.getAttribute("aria-label")).toBe(
      EN_KEYS["admin.tabs.nav_aria_label"],
    );
  });
});
