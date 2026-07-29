import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// No <Toaster> is mounted here (same posture as TagGroupsPage.test.tsx): success
// and failure are asserted through the network calls that actually happened, and
// `sonner` is mocked so the toast calls stay observable.
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@sentry/react", () => ({ setTag: vi.fn() }));

import i18n from "@/locales/i18n";
import type {
  BrowseCategoryAdminRead,
  OverCategorizedResponse,
  TagGroupsResponse,
} from "@/lib/api-types";
import { CategoriesPage } from "@/modules/admin/CategoriesPage";
import { AuthProvider } from "@/shell/AuthContext";
import { toast } from "sonner";

// Matches the visual harness's default admin identity, so the "last changed by
// you" branch is exercised against the same id the Playwright fixture uses.
const ADMIN_ID = "11111111-1111-1111-1111-111111111111";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  // `vi.mock("sonner", ...)` builds its vi.fn()s once per file; restoreAllMocks
  // only reverts vi.spyOn spies, so without this the call history accumulates
  // across `it()` blocks and per-test call-count assertions see earlier totals.
  vi.clearAllMocks();
});

function category(overrides: Partial<BrowseCategoryAdminRead> = {}): BrowseCategoryAdminRead {
  return {
    id: "c1",
    slug: "storage-organization",
    name_en: "Storage & organization",
    name_pl: "Przechowywanie i organizacja",
    description_en: null,
    description_pl: null,
    position: 0,
    parent_id: null,
    model_count: 34,
    inclusion_criterion: "The model primarily stores, sorts or organises other objects.",
    ...overrides,
  };
}

const CATEGORIES: BrowseCategoryAdminRead[] = [
  category(),
  category({
    id: "c2",
    slug: "home-decor",
    name_en: "Home decor",
    name_pl: "Dekoracje",
    position: 1,
    model_count: 21,
    inclusion_criterion: "Chosen for how it looks in a living space, not what it does.",
  }),
  category({
    id: "c3",
    slug: "replacement-parts",
    name_en: "Replacement parts",
    name_pl: "Części zamienne",
    position: 2,
    model_count: 0,
    // A category with NO criterion — the row must render nothing on that line,
    // never a placeholder or a dash.
    inclusion_criterion: null,
  }),
];

interface FetchOpts {
  categories?: BrowseCategoryAdminRead[];
  /** Zero-category models backing the curation queue. */
  queue?: { id: string; slug: string; name_en: string; name_pl: string | null }[];
  categoriesPending?: boolean;
  categoriesError?: boolean;
  queueError?: boolean;
  /** Story 52.3 — the two reads the curation-QA panel added to this route. */
  tagGroups?: TagGroupsResponse;
  tagGroupsError?: boolean;
  tagGroupsPending?: boolean;
  overCategorized?: OverCategorizedResponse;
  overCategorizedError?: boolean;
  /** Status returned for writes; 409 bodies carry `detail` so the conflict split is exercised. */
  writeStatus?: number;
  writeDetail?: string;
  /** `GET /api/models/{id}` detail body for the replace-set editor. */
  modelCategories?: { id: string; slug: string }[];
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetch(opts: FetchOpts = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method ?? "GET";

    if (url.includes("/api/auth/me")) {
      return json({ id: ADMIN_ID, email: "a@b.c", display_name: "Admin", role: "admin" });
    }

    if (method === "GET" && url.includes("/api/admin/categories")) {
      if (opts.categoriesPending) return new Promise<Response>(() => {});
      if (opts.categoriesError) return json({ detail: "boom" }, 500);
      return json(opts.categories ?? CATEGORIES);
    }

    if (method === "GET" && url.includes("/api/admin/audit-log")) {
      return json({ items: [] });
    }

    // Story 52.3 — the curation-QA panel's two extra sources. Checked before
    // the model routes below: neither path substring overlaps, but keeping the
    // admin read adjacent to its sibling keeps the ordering obvious.
    if (method === "GET" && url.includes("/api/admin/models/over-categorized")) {
      if (opts.overCategorizedError) return json({ detail: "boom" }, 500);
      return json(opts.overCategorized ?? { items: [], total: 0 });
    }

    if (method === "GET" && url.includes("/api/tag-groups")) {
      if (opts.tagGroupsPending) return new Promise<Response>(() => {});
      if (opts.tagGroupsError) return json({ detail: "boom" }, 500);
      return json(opts.tagGroups ?? { groups: [], groupless: [] });
    }

    // The model DETAIL read the editor re-fetches on open. Checked before the
    // list read below because both contain "/api/models".
    if (method === "GET" && /\/api\/models\/[^?]+/.test(url)) {
      return json({
        id: "m1",
        slug: "spiral-vase",
        name_en: "Spiral vase",
        name_pl: null,
        categories: opts.modelCategories ?? [],
        tags: [],
      });
    }

    if (method === "GET" && url.includes("/api/models")) {
      if (opts.queueError) return json({ detail: "boom" }, 500);
      const items = opts.queue ?? [
        { id: "m1", slug: "spiral-vase", name_en: "Spiral vase", name_pl: null },
      ];
      return json({ items, total: items.length, offset: 0, limit: 48 });
    }

    if (opts.writeStatus && opts.writeStatus >= 400) {
      return json({ detail: opts.writeDetail ?? "conflict" }, opts.writeStatus);
    }
    if (method === "DELETE") return new Response(null, { status: 204 });
    return json({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function calls(fetchMock: ReturnType<typeof vi.fn>, method: string, urlSubstr: string) {
  return fetchMock.mock.calls
    .map((call) => {
      const input = call[0] as RequestInfo | URL;
      const init = (call[1] ?? {}) as RequestInit;
      return { url: typeof input === "string" ? input : input.toString(), init };
    })
    .filter(({ url, init }) => (init.method ?? "GET") === method && url.includes(urlSubstr))
    .map(({ url, init }) => ({
      url,
      body: init.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {},
    }));
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/categories",
    component: () => <>{node}</>,
  });
  const others = ["/admin/users", "/admin/invites", "/admin/profile-library", "/admin/profile-offers", "/admin/queues", "/admin/tag-groups", "/"].map(
    (path) =>
      createRoute({
        getParentRoute: () => root,
        path,
        component: () => <div>{path}</div>,
      }),
  );
  const router = createRouter({
    routeTree: root.addChildren([route, ...others]),
    history: createMemoryHistory({ initialEntries: ["/admin/categories"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    ...render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    ),
    qc,
  };
}

describe("CategoriesPage — list (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("shows a skeleton while loading, not a bare spinner", async () => {
    installFetch({ categoriesPending: true });
    mount(<CategoriesPage />);
    expect(await screen.findByTestId("categories-skeleton")).toBeTruthy();
  });

  it("renders each row with position, name, slug, criterion and model count", async () => {
    installFetch();
    mount(<CategoriesPage />);

    const row = await screen.findByTestId("browse-category-storage-organization");
    expect(within(row).getByText("Storage & organization")).toBeTruthy();
    expect(within(row).getByText("storage-organization")).toBeTruthy();
    expect(within(row).getByText("0")).toBeTruthy(); // position
    expect(within(row).getByText("34 models")).toBeTruthy();
    // AC-4 / DESIGN.md: the criterion is visible IN THE LIST, because it is the
    // admission test — two categories must be comparable without opening two
    // dialogs.
    expect(
      within(row).getByText("The model primarily stores, sorts or organises other objects."),
    ).toBeTruthy();
  });

  it("renders no criterion line at all when a category has none", async () => {
    installFetch();
    mount(<CategoriesPage />);

    const row = await screen.findByTestId("browse-category-replacement-parts");
    // AC-5 — no placeholder, no em-dash: FR26-GOV-1 is a governance norm this
    // screen surfaces, not a field it enforces.
    expect(within(row).queryByText("—")).toBeNull();
    expect(within(row).getByText("0 models")).toBeTruthy();
  });

  it("renders rows in the server's order and does not re-sort them", async () => {
    // Served deliberately out of (position, slug) order: the backend owns the
    // sort and the client must not fork that contract.
    installFetch({ categories: [CATEGORIES[1]!, CATEGORIES[0]!, CATEGORIES[2]!] });
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-home-decor");
    const slugs = screen
      .getAllByTestId(/^browse-category-/)
      .map((el) => el.getAttribute("data-testid"));
    expect(slugs).toEqual([
      "browse-category-home-decor",
      "browse-category-storage-organization",
      "browse-category-replacement-parts",
    ]);
  });

  it("fails closed on a read error — error banner plus retry, never an empty list", async () => {
    installFetch({ categoriesError: true });
    mount(<CategoriesPage />);

    expect(await screen.findByText("Could not load browse categories")).toBeTruthy();
    expect(screen.queryByText("No browse categories yet.")).toBeNull();
    // Scoped to the LIST's error banner: Story 52.3's QA panel owns its own
    // "Retry" for the partial-failure branch, and both are legitimately present
    // when the category read is the source that failed.
    const banner = screen.getByText("Could not load browse categories").closest("div");
    expect(banner).toBeTruthy();
    expect(within(banner as HTMLElement).getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("renders the distinct empty-state copy for zero categories", async () => {
    installFetch({ categories: [] });
    mount(<CategoriesPage />);
    expect(await screen.findByText("No browse categories yet.")).toBeTruthy();
  });

  it("prefers the Polish name only when the locale is Polish and the name is non-empty", async () => {
    await i18n.changeLanguage("pl");
    installFetch({
      categories: [category({ name_pl: "Przechowywanie" }), category({ id: "c9", slug: "s9", name_en: "Only English", name_pl: "" })],
    });
    mount(<CategoriesPage />);

    expect(await screen.findByText("Przechowywanie")).toBeTruthy();
    // Empty string is a valid name_pl on the wire; it must fall back, not render blank.
    expect(screen.getByText("Only English")).toBeTruthy();
  });
});

describe("CategoriesPage — reorder (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("disables move-up on the first row and move-down on the last", async () => {
    const user = userEvent.setup();
    installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(
      screen.getByRole("button", { name: "Actions for category Storage & organization" }),
    );
    const moveUp = await screen.findByRole("menuitem", { name: /Move up/ });
    const moveDown = await screen.findByRole("menuitem", { name: /Move down/ });
    // First row: up is unavailable, down is available. Asserted through the
    // accessible disabled state, so a purely visual "greying out" cannot pass.
    expect(moveUp.getAttribute("aria-disabled")).toBe("true");
    expect(moveDown.getAttribute("aria-disabled")).not.toBe("true");

    // Last row: the mirror image. Both boundaries matter — the reorder swap
    // reads `data[index ± 1]`, so an enabled boundary control would index past
    // the array end.
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Actions for category Replacement parts" }));
    const lastUp = await screen.findByRole("menuitem", { name: /Move up/ });
    const lastDown = await screen.findByRole("menuitem", { name: /Move down/ });
    expect(lastUp.getAttribute("aria-disabled")).not.toBe("true");
    expect(lastDown.getAttribute("aria-disabled")).toBe("true");
  });

  it("swaps adjacent positions with two sequential PATCHes", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-home-decor");
    await user.click(screen.getByRole("button", { name: "Actions for category Home decor" }));
    await user.click(await screen.findByRole("menuitem", { name: /Move up/ }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/api/admin/categories")).toHaveLength(2));
    const patches = calls(fetchMock, "PATCH", "/api/admin/categories");
    // Home decor (position 1) takes Storage's 0; Storage takes 1.
    expect(patches[0]?.url).toContain("/c2");
    expect(patches[0]?.body).toEqual({ position: 0 });
    expect(patches[1]?.url).toContain("/c1");
    expect(patches[1]?.body).toEqual({ position: 1 });
  });

  it("restores the first write when the second PATCH fails, so no two rows share a position", async () => {
    const user = userEvent.setup();
    let patchCount = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      if (url.includes("/api/auth/me")) {
        return json({ id: ADMIN_ID, email: "a@b.c", display_name: "Admin", role: "admin" });
      }
      if (method === "GET" && url.includes("/api/admin/categories")) return json(CATEGORIES);
      if (method === "GET" && url.includes("/api/admin/models/over-categorized")) {
        return json({ items: [], total: 0 });
      }
      if (method === "GET" && url.includes("/api/tag-groups")) {
        return json({ groups: [], groupless: [] });
      }
      if (method === "GET" && url.includes("/api/models")) {
        return json({ items: [], total: 0, offset: 0, limit: 48 });
      }
      if (method === "PATCH") {
        patchCount += 1;
        // The SECOND write is the dangerous one: it lands after the first has
        // already committed, so a failure here leaves the server inconsistent
        // unless the compensating rollback fires.
        if (patchCount === 2) return json({ detail: "boom" }, 500);
        return json({});
      }
      return json({});
    });
    vi.stubGlobal("fetch", fetchMock);
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-home-decor");
    await user.click(screen.getByRole("button", { name: "Actions for category Home decor" }));
    await user.click(await screen.findByRole("menuitem", { name: /Move up/ }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/api/admin/categories")).toHaveLength(3));
    const patches = calls(fetchMock, "PATCH", "/api/admin/categories");
    // Third call is the compensating restore of the first write's original value.
    expect(patches[2]?.url).toContain("/c2");
    expect(patches[2]?.body).toEqual({ position: 1 });
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});

describe("CategoriesPage — create and edit (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("creates a category with the criterion and appends it at the end", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(screen.getByRole("button", { name: "New category" }));
    await user.type(screen.getByRole("textbox", { name: /Slug/ }), "vases");
    await user.type(screen.getByRole("textbox", { name: /English name/ }), "Vases");
    await user.type(screen.getByRole("textbox", { name: /Inclusion criterion/ }), "Vase models.");
    await user.click(screen.getByRole("button", { name: "Create category" }));

    await waitFor(() => expect(calls(fetchMock, "POST", "/api/admin/categories")).toHaveLength(1));
    expect(calls(fetchMock, "POST", "/api/admin/categories")[0]?.body).toEqual({
      slug: "vases",
      name_en: "Vases",
      name_pl: null,
      inclusion_criterion: "Vase models.",
      position: 3,
    });
  });

  it("surfaces a slug conflict inline and keeps the dialog open", async () => {
    const user = userEvent.setup();
    installFetch({ writeStatus: 409 });
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(screen.getByRole("button", { name: "New category" }));
    await user.type(screen.getByRole("textbox", { name: /Slug/ }), "storage-organization");
    await user.type(screen.getByRole("textbox", { name: /English name/ }), "Dupe");
    await user.click(screen.getByRole("button", { name: "Create category" }));

    expect(
      await screen.findByText("That slug is already taken by another category."),
    ).toBeTruthy();
    // Still open, input intact — the admin can correct it in place.
    expect(screen.getByRole("textbox", { name: /Slug/ })).toBeTruthy();
  });

  it("pre-fills the edit dialog from the admin read and sends only changed fields", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(
      screen.getByRole("button", { name: "Actions for category Storage & organization" }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "Edit" }));

    // AC-11 — the criterion is pre-filled, which is only possible because the
    // admin read exposes it (B-1). The slug field is create-only.
    const criterion = screen.getByRole("textbox", { name: /Inclusion criterion/ });
    expect((criterion as HTMLTextAreaElement).value).toBe(
      "The model primarily stores, sorts or organises other objects.",
    );
    expect(screen.queryByRole("textbox", { name: /Slug/ })).toBeNull();

    await user.clear(criterion);
    await user.type(criterion, "Now something else.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/api/admin/categories")).toHaveLength(1));
    // Only the criterion travels — name_en/name_pl were untouched.
    expect(calls(fetchMock, "PATCH", "/api/admin/categories")[0]?.body).toEqual({
      inclusion_criterion: "Now something else.",
    });
  });

  it("clears the criterion with an explicit null when the field is emptied", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(
      screen.getByRole("button", { name: "Actions for category Storage & organization" }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "Edit" }));
    await user.clear(screen.getByRole("textbox", { name: /Inclusion criterion/ }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(calls(fetchMock, "PATCH", "/api/admin/categories")).toHaveLength(1));
    expect(calls(fetchMock, "PATCH", "/api/admin/categories")[0]?.body).toEqual({
      inclusion_criterion: null,
    });
  });

  it("issues no request when an edit changes nothing", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("browse-category-storage-organization");
    await user.click(
      screen.getByRole("button", { name: "Actions for category Storage & organization" }),
    );
    await user.click(await screen.findByRole("menuitem", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls(fetchMock, "PATCH", "/api/admin/categories")).toHaveLength(0);
  });
});

describe("CategoriesPage — delete (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  async function openDelete(
    user: ReturnType<typeof userEvent.setup>,
    name = "Storage & organization",
    testid = "browse-category-storage-organization",
  ) {
    await screen.findByTestId(testid);
    await user.click(screen.getByRole("button", { name: `Actions for category ${name}` }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }));
  }

  it("names the assignment count on the first screen instead of calling the category clean", async () => {
    const user = userEvent.setup();
    installFetch();
    mount(<CategoriesPage />);

    // The row the admin opened this from renders "34 models", and `model_count`
    // is already passed to the dialog — so claiming the category has none is a
    // falsehood the user can see contradicted on screen.
    await openDelete(user);

    expect(
      await screen.findByText(
        "This category has 34 assigned models. Deleting it will be refused until the assignments are detached.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/has no assigned models/)).toBeNull();
  });

  it("keeps the clean-confirm copy for a category that genuinely has none", async () => {
    const user = userEvent.setup();
    installFetch();
    mount(<CategoriesPage />);

    await openDelete(user, "Replacement parts", "browse-category-replacement-parts");

    expect(await screen.findByText(/has no assigned models/)).toBeTruthy();
  });

  it("drops the count on a 409 whose assignments the count cannot see", async () => {
    const user = userEvent.setup();
    installFetch({ writeStatus: 409, writeDetail: "category_in_use" });
    mount(<CategoriesPage />);

    // `model_count` excludes soft-deleted models (Decision AY) while the 409 is
    // raised over ALL assignment rows — `delete_browse_category` documents the
    // divergence. "Cannot delete — 0 models are assigned" next to a destructive
    // detach both contradicts itself and understates what the detach removes.
    await openDelete(user, "Replacement parts", "browse-category-replacement-parts");
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(
      await screen.findByText("Cannot delete — this category still has assignments"),
    ).toBeTruthy();
    expect(screen.queryByText(/0 models are assigned/)).toBeNull();
    // The detach is still offered — it is the branch detach actually resolves.
    expect(screen.getByRole("button", { name: "Detach and delete" })).toBeTruthy();
  });

  it("deletes a clean category without ever sending detach", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await openDelete(user);
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(calls(fetchMock, "DELETE", "/api/admin/categories")).toHaveLength(1));
    // AC-22 — detach is NEVER implicit in the first attempt.
    expect(calls(fetchMock, "DELETE", "/api/admin/categories")[0]?.url).not.toContain("detach");
  });

  it("turns a 409 in-use into a distinct message and an explicit detach action", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch({ writeStatus: 409, writeDetail: "category_in_use" });
    mount(<CategoriesPage />);

    await openDelete(user);
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByText("Cannot delete — 34 models are assigned")).toBeTruthy();
    const detachButton = screen.getByRole("button", { name: "Detach and delete" });
    await user.click(detachButton);

    await waitFor(() => expect(calls(fetchMock, "DELETE", "/api/admin/categories")).toHaveLength(2));
    expect(calls(fetchMock, "DELETE", "/api/admin/categories")[1]?.url).toContain("detach=true");
  });

  it("offers NO detach action for a has-children 409, because detach cannot resolve it", async () => {
    const user = userEvent.setup();
    installFetch({ writeStatus: 409, writeDetail: "category_has_children" });
    mount(<CategoriesPage />);

    await openDelete(user);
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(
      await screen.findByText("Cannot delete — this category has child categories"),
    ).toBeTruthy();
    // D-8 — offering detach here would offer a fix that provably does not work:
    // the API checks children FIRST and unconditionally.
    expect(screen.queryByRole("button", { name: "Detach and delete" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });
});

describe("CategoriesPage — curation queue (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("requests the queue with uncategorized=true", async () => {
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    await screen.findByTestId("curation-queue");
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes("uncategorized=true")),
      ).toBe(true),
    );
  });

  it("lists zero-category models as curation work, never as an error", async () => {
    installFetch();
    mount(<CategoriesPage />);

    expect(await screen.findByTestId("curation-model-spiral-vase")).toBeTruthy();
    // FR26-CAT-2 — the copy must call this a valid state, not a defect.
    expect(
      screen.getByText(/valid state — they stay public and visible everywhere/),
    ).toBeTruthy();
  });

  it("renders the nothing-needs-attention copy for an empty queue", async () => {
    installFetch({ queue: [] });
    mount(<CategoriesPage />);
    expect(await screen.findByText("Nothing needs attention.")).toBeTruthy();
  });

  it("fails closed when the queue read fails", async () => {
    installFetch({ queueError: true });
    mount(<CategoriesPage />);
    expect(await screen.findByText("Could not load the curation queue")).toBeTruthy();
  });
});

describe("ModelCategoriesDialog — replace-set editor (Story 52.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  async function openEditor(
    user: ReturnType<typeof userEvent.setup>,
    opts: FetchOpts = {},
  ) {
    const fetchMock = installFetch(opts);
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-model-spiral-vase");
    await user.click(screen.getByRole("button", { name: "Assign categories" }));
    return fetchMock;
  }

  it("re-fetches the model's categories when it opens", async () => {
    const user = userEvent.setup();
    const fetchMock = await openEditor(user);

    // AC-16 — the checkbox state must derive from a fresh read, not a value
    // captured at mount. This shrinks the last-writer-wins stale window; it does
    // not close it, and nothing in the UI claims otherwise.
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter((c) => /\/api\/models\/m1/.test(String(c[0]))).length,
      ).toBeGreaterThan(0),
    );
  });

  it("labels the save control 'Replace categories', never 'Save changes'", async () => {
    const user = userEvent.setup();
    await openEditor(user);

    expect(await screen.findByRole("button", { name: "Replace categories" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /save changes/i })).toBeNull();
  });

  it("shows the advisory above three categories AND keeps the save button enabled", async () => {
    const user = userEvent.setup();
    await openEditor(user, {
      categories: CATEGORIES,
      modelCategories: [
        { id: "c1", slug: "storage-organization" },
        { id: "c2", slug: "home-decor" },
        { id: "c3", slug: "replacement-parts" },
      ],
    });

    // Three selected: no advisory yet.
    await waitFor(() => expect(screen.queryByTestId("category-advisory")).toBeNull());

    // Tick a fourth by adding one more category to the list.
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.every((c) => (c as HTMLInputElement).checked)).toBe(true);

    // Untick then re-tick is a no-op; instead assert the four-selected case via a
    // model that already carries four.
    cleanup();
    await openEditor(user, {
      categories: [...CATEGORIES, category({ id: "c4", slug: "vases", name_en: "Vases", position: 3 })],
      modelCategories: [
        { id: "c1", slug: "storage-organization" },
        { id: "c2", slug: "home-decor" },
        { id: "c3", slug: "replacement-parts" },
        { id: "c4", slug: "vases" },
      ],
    });

    expect(await screen.findByTestId("category-advisory")).toBeTruthy();
    expect(screen.getByText(/the suggested norm is 1–3\. Saving is not blocked\./)).toBeTruthy();
    // FR26-CAT-3 — this is the assertion that actually catches a regression:
    // the norm is advisory, so the write must stay possible.
    const save = screen.getByRole("button", { name: "Replace categories" });
    expect((save as HTMLButtonElement).disabled).toBe(false);
  });

  it("saves a four-category set successfully — a warning, not a 4xx and not a block", async () => {
    const user = userEvent.setup();
    const fetchMock = await openEditor(user, {
      categories: [...CATEGORIES, category({ id: "c4", slug: "vases", name_en: "Vases", position: 3 })],
      modelCategories: [
        { id: "c1", slug: "storage-organization" },
        { id: "c2", slug: "home-decor" },
        { id: "c3", slug: "replacement-parts" },
        { id: "c4", slug: "vases" },
      ],
    });

    await screen.findByTestId("category-advisory");
    await user.click(screen.getByRole("button", { name: "Replace categories" }));

    await waitFor(() =>
      expect(calls(fetchMock, "PUT", "/api/admin/models/m1/categories")).toHaveLength(1),
    );
    expect(calls(fetchMock, "PUT", "/api/admin/models/m1/categories")[0]?.body).toEqual({
      category_ids: ["c1", "c2", "c3", "c4"],
    });
  });

  it("submits an empty set, clearing every assignment", async () => {
    const user = userEvent.setup();
    const fetchMock = await openEditor(user, {
      modelCategories: [{ id: "c1", slug: "storage-organization" }],
    });

    await screen.findByRole("button", { name: "Replace categories" });
    await user.click(screen.getAllByRole("checkbox")[0]!);
    await user.click(screen.getByRole("button", { name: "Replace categories" }));

    await waitFor(() =>
      expect(calls(fetchMock, "PUT", "/api/admin/models/m1/categories")).toHaveLength(1),
    );
    // AC-19 — an empty set is valid; the model stays public with zero categories.
    expect(calls(fetchMock, "PUT", "/api/admin/models/m1/categories")[0]?.body).toEqual({
      category_ids: [],
    });
  });

  it("sends no optimistic-concurrency precondition — the contract has none", async () => {
    const user = userEvent.setup();
    const fetchMock = await openEditor(user, {
      modelCategories: [{ id: "c1", slug: "storage-organization" }],
    });

    await screen.findByRole("button", { name: "Replace categories" });
    await user.click(screen.getByRole("button", { name: "Replace categories" }));

    await waitFor(() =>
      expect(calls(fetchMock, "PUT", "/api/admin/models/m1/categories")).toHaveLength(1),
    );
    const put = fetchMock.mock.calls.find(
      (c) => (((c[1] ?? {}) as RequestInit).method ?? "GET") === "PUT",
    );
    const headers = new Headers(((put?.[1] ?? {}) as RequestInit).headers);
    // D-3 — inventing an If-Match here would imply conflict detection the API
    // does not perform. The payload carries no `revision` either.
    expect(headers.get("If-Match")).toBeNull();
    const body = JSON.parse(String(((put?.[1] ?? {}) as RequestInit).body)) as Record<string, unknown>;
    expect(Object.keys(body)).toEqual(["category_ids"]);
  });

  it("renders no last-writer note when the audit log has no category write", async () => {
    const user = userEvent.setup();
    await openEditor(user);

    await screen.findByRole("button", { name: "Replace categories" });
    // The note is an advisory garnish: absent audit data renders nothing and
    // blocks nothing.
    expect(screen.queryByTestId("category-last-write")).toBeNull();
  });

  it("names the last audited writer as 'you' when the actor is the current admin", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      if (url.includes("/api/auth/me")) {
        return json({ id: ADMIN_ID, email: "a@b.c", display_name: "Admin", role: "admin" });
      }
      if (method === "GET" && url.includes("/api/admin/audit-log")) {
        return json({
          items: [
            // A NON-category model.update lands first and must be skipped: the
            // replace-set write deliberately reuses this action/entity_type, so
            // only the `category_ids` key distinguishes it.
            {
              id: "a2",
              actor_user_id: ADMIN_ID,
              action: "model.update",
              entity_type: "model",
              entity_id: "m1",
              before_json: { name_en: "x" },
              after_json: { name_en: "y" },
              at: "2026-07-29T22:00:00",
            },
            {
              id: "a1",
              actor_user_id: ADMIN_ID,
              action: "model.update",
              entity_type: "model",
              entity_id: "m1",
              before_json: { category_ids: [] },
              after_json: { category_ids: ["c1"] },
              at: "2026-07-29T21:04:00",
            },
          ],
        });
      }
      if (method === "GET" && url.includes("/api/admin/categories")) return json(CATEGORIES);
      if (method === "GET" && url.includes("/api/admin/models/over-categorized")) {
        return json({ items: [], total: 0 });
      }
      if (method === "GET" && url.includes("/api/tag-groups")) {
        return json({ groups: [], groupless: [] });
      }
      if (method === "GET" && /\/api\/models\/[^?]+/.test(url)) {
        return json({ id: "m1", slug: "spiral-vase", name_en: "Spiral vase", name_pl: null, categories: [], tags: [] });
      }
      if (method === "GET" && url.includes("/api/models")) {
        return json({
          items: [{ id: "m1", slug: "spiral-vase", name_en: "Spiral vase", name_pl: null }],
          total: 1,
          offset: 0,
          limit: 48,
        });
      }
      return json({});
    });
    vi.stubGlobal("fetch", fetchMock);
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-model-spiral-vase");
    await user.click(screen.getByRole("button", { name: "Assign categories" }));

    const note = await screen.findByTestId("category-last-write");
    expect(note.textContent).toBe("Last changed by you, 2026-07-29 21:04");
  });

  it("does not imply merge or conflict detection anywhere in the editor", async () => {
    const user = userEvent.setup();
    await openEditor(user);

    const dialog = await screen.findByRole("dialog");
    const text = dialog.textContent ?? "";
    // D-3 — under the accepted last-writer-wins posture a concurrent edit is
    // silently discarded. Copy that implied detection would be a lie.
    for (const forbidden of [/conflict/i, /merge/i, /someone else/i, /reload/i, /out of date/i]) {
      expect(text).not.toMatch(forbidden);
    }
  });
});
