import "@/locales/i18n";

import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { BrowseCategoryRead } from "@/lib/api-types";

import { BrowseSheet } from "./BrowseSheet";

function category(
  id: string,
  slug: string,
  name_en: string,
  model_count: number,
): BrowseCategoryRead {
  return {
    id,
    slug,
    name_en,
    name_pl: null,
    position: 0,
    parent_id: null,
    description_en: null,
    description_pl: null,
    model_count,
  };
}

const CATEGORIES: BrowseCategoryRead[] = [
  category("c1", "organizery", "Organisers", 12),
  category("c2", "uchwyty", "Mounts", 7),
];

const SEARCH = { q: "vase", page: 3 } as const;

beforeAll(async () => {
  await i18n.changeLanguage("en");
  vi.stubGlobal("scrollTo", () => {});
});

afterEach(() => {
  cleanup();
});

// Real router registers both link targets, mirroring BrowseRail.test.tsx's
// harness — `BrowseSheet` renders row `Link`s through the shared
// `BrowseCategoryList`, so a router context is required.
function mountSheet(overrides: Partial<Parameters<typeof BrowseSheet>[0]> = {}) {
  const onOpenChange = vi.fn();
  const props = {
    categories: CATEGORIES,
    activeSlug: undefined as string | undefined,
    search: SEARCH,
    isLoading: false,
    isError: false,
    onRetry: vi.fn(),
    open: false,
    onOpenChange,
    ...overrides,
  };
  const root = createRootRoute({ component: () => <Outlet /> });
  const sheet = () => <BrowseSheet {...props} />;
  const passthrough = (raw: Record<string, unknown>) => raw;
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: sheet,
    validateSearch: passthrough,
  });
  const scoped = createRoute({
    getParentRoute: () => root,
    path: "/categories/$slug",
    component: sheet,
    validateSearch: passthrough,
  });
  // Mirrors BrowseRail.test.tsx: the mounted URL is DERIVED from `activeSlug`,
  // since `Link` stamps `aria-current="page"` on whichever row's href matches
  // the current location — pinning both independently would let the two
  // sources disagree in a way production never can.
  const at =
    props.activeSlug === undefined
      ? "/catalog/?q=vase&page=3"
      : `/categories/${props.activeSlug}?q=vase&page=3`;
  const router = createRouter({
    routeTree: root.addChildren([catalog, scoped]),
    history: createMemoryHistory({ initialEntries: [at] }),
  });
  return { router, props };
}

async function renderSheet(overrides: Partial<Parameters<typeof BrowseSheet>[0]> = {}) {
  const { router, props } = mountSheet(overrides);
  await router.load();
  render(<RouterProvider router={router} />);
  return props;
}

// A real controlled Harness (not a stub) so opening the trigger, closing via
// a row's `onNavigate`, and D-6's focus-return can all be exercised against
// actual state transitions instead of asserting on a spy alone.
function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <BrowseSheet
      categories={CATEGORIES}
      activeSlug={undefined}
      search={SEARCH}
      isLoading={false}
      isError={false}
      onRetry={vi.fn()}
      open={open}
      onOpenChange={setOpen}
    />
  );
}

async function renderHarness() {
  const root = createRootRoute({ component: () => <Outlet /> });
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: Harness,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const scoped = createRoute({
    getParentRoute: () => root,
    path: "/categories/$slug",
    component: Harness,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const router = createRouter({
    routeTree: root.addChildren([catalog, scoped]),
    history: createMemoryHistory({ initialEntries: ["/catalog/?q=vase&page=3"] }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
}

describe("BrowseSheet", () => {
  it("renders a trigger button with an accessible name distinct from Tags/Filters", async () => {
    await renderSheet({ open: false });

    const trigger = screen.getByRole("button", { name: "Browse" });
    expect(trigger).toBeTruthy();
    expect(trigger.className).toContain("lg:hidden");
  });

  it("does not render the sheet dialog while closed", async () => {
    await renderSheet({ open: false });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens a left sheet with an accessible dialog name and the rail's row vocabulary", async () => {
    await renderSheet({ open: true });

    const dialog = screen.getByRole("dialog", { name: "Browse categories" });
    expect(dialog).toBeTruthy();
    expect(screen.getByRole("link", { name: "All catalog" })).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /Organisers, 12 models/ }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /Mounts, 7 models/ })).toBeTruthy();
  });

  it("marks the active category with the same active treatment the rail uses", async () => {
    await renderSheet({ open: true, activeSlug: "uchwyty" });

    const active = screen.getByRole("link", { name: /Mounts, 7 models/ });
    expect(active.getAttribute("aria-current")).toBe("page");
    expect(active.className).toContain("ring-primary");
    expect(
      screen.getByRole("link", { name: "All catalog" }).getAttribute("aria-current"),
    ).toBeNull();
  });

  it("carries the forwarded search layer and resets page on a row link, same as the rail", async () => {
    await renderSheet({ open: true });

    const href = screen
      .getByRole("link", { name: /Organisers, 12 models/ })
      .getAttribute("href");
    expect(href).toContain("/categories/organizery");
    expect(href).toContain("q=vase");
    expect(href).not.toContain("page=");
  });

  it("closes via onOpenChange(false) when a row is clicked (D-2 onNavigate)", async () => {
    const onOpenChange = vi.fn();
    await renderSheet({ open: true, onOpenChange });

    fireEvent.click(screen.getByRole("link", { name: "All catalog" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("does not close on a modified click (Cmd/Ctrl/Shift/Alt or middle-click opens in a new tab)", async () => {
    const onOpenChange = vi.fn();
    await renderSheet({ open: true, onOpenChange });

    const link = screen.getByRole("link", { name: "All catalog" });
    fireEvent.click(link, { metaKey: true });
    fireEvent.click(link, { ctrlKey: true });
    fireEvent.click(link, { shiftKey: true });
    fireEvent.click(link, { altKey: true });
    fireEvent.click(link, { button: 1 });
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it("shares loading/error footer state with the rail via BrowseCategoryList", async () => {
    await renderSheet({ open: true, isError: true, categories: [] });

    expect(screen.getByText("Network error. Try again.")).toBeTruthy();
    const retry = screen.getByRole("button", { name: "Retry" });
    expect(retry).toBeTruthy();
  });

  it("returns focus to the trigger when the sheet closes after a row selection (D-6)", async () => {
    await renderHarness();

    const trigger = screen.getByRole("button", { name: "Browse" });
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: "Browse categories" })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("link", { name: "All catalog" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByRole("button", { name: "Browse" }));
    });
  });
});
