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

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@sentry/react", () => ({ setTag: vi.fn() }));

import i18n from "@/locales/i18n";
import type {
  BrowseCategoryAdminRead,
  OverCategorizedResponse,
  TagGroupsResponse,
} from "@/lib/api-types";
import { CategoriesPage } from "@/modules/admin/CategoriesPage";
import { CurationQaPanel } from "@/modules/admin/CurationQaPanel";
import { ADVISORY_MAX } from "@/modules/admin/curationThresholds";
import { AuthProvider } from "@/shell/AuthContext";

// Story 52.3 — the curation-QA panel. Mounted through CategoriesPage (real
// hooks, real `api()`, fetch stubbed at the network edge) so the query keys, the
// threshold that travels to the server and the advisory-only contract are all
// exercised end-to-end rather than asserted against a mock.

const ADMIN_ID = "11111111-1111-1111-1111-111111111111";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function cat(overrides: Partial<BrowseCategoryAdminRead> = {}): BrowseCategoryAdminRead {
  return {
    id: "c1",
    slug: "storage",
    name_en: "Storage",
    name_pl: "Przechowywanie",
    description_en: null,
    description_pl: null,
    position: 0,
    parent_id: null,
    model_count: 10,
    inclusion_criterion: null,
    ...overrides,
  };
}

// One category of each interesting shape: healthy, empty, tiny + label-colliding.
const CATEGORIES: BrowseCategoryAdminRead[] = [
  cat(),
  cat({ id: "c2", slug: "replacement-parts", name_en: "Replacement parts", name_pl: "Części", position: 1, model_count: 0 }),
  cat({ id: "c3", slug: "vases", name_en: "Vases", name_pl: "Wazony", position: 2, model_count: 1 }),
];

const TAG_GROUPS: TagGroupsResponse = {
  groups: [
    {
      id: "g1",
      slug: "type",
      name_en: "Type",
      name_pl: "Typ",
      position: 0,
      tags: [
        {
          id: "t1",
          slug: "vases",
          name_en: "Vases",
          name_pl: "Wazony",
          group_id: "g1",
          group_position: 0,
          model_count: 4,
        },
      ],
    },
  ],
  groupless: [
    {
      id: "t2",
      slug: "loose",
      name_en: "Loose",
      name_pl: "Luźny",
      group_id: null,
      group_position: 0,
      model_count: 1,
    },
  ],
};

const OVER_CATEGORIZED: OverCategorizedResponse = {
  items: [
    {
      model_id: "m1",
      slug: "spiral-vase",
      name_en: "Spiral vase",
      name_pl: "Wazon spiralny",
      category_count: ADVISORY_MAX + 1,
    },
  ],
  total: 1,
};

interface FetchOpts {
  categories?: BrowseCategoryAdminRead[];
  tagGroups?: TagGroupsResponse;
  tagGroupsPending?: boolean;
  overCategorized?: OverCategorizedResponse;
  overCategorizedError?: boolean;
  queueTotal?: number;
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
    if (method === "GET" && url.includes("/api/admin/models/over-categorized")) {
      if (opts.overCategorizedError) return json({ detail: "boom" }, 500);
      return json(opts.overCategorized ?? OVER_CATEGORIZED);
    }
    if (method === "GET" && url.includes("/api/admin/categories")) {
      return json(opts.categories ?? CATEGORIES);
    }
    if (method === "GET" && url.includes("/api/admin/audit-log")) return json({ items: [] });
    if (method === "GET" && url.includes("/api/tag-groups")) {
      if (opts.tagGroupsPending) return new Promise<Response>(() => {});
      return json(opts.tagGroups ?? TAG_GROUPS);
    }
    if (method === "GET" && /\/api\/models\/[^?]+/.test(url)) {
      return json({
        id: "m1",
        slug: "spiral-vase",
        name_en: "Spiral vase",
        name_pl: "Wazon spiralny",
        categories: [],
        tags: [],
      });
    }
    if (method === "GET" && url.includes("/api/models")) {
      const total = opts.queueTotal ?? 17;
      return json({ items: [], total, offset: 0, limit: 48 });
    }
    return json({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/categories",
    component: () => <>{node}</>,
  });
  const others = ["/admin/tag-groups", "/"].map((path) =>
    createRoute({ getParentRoute: () => root, path, component: () => <div>{path}</div> }),
  );
  const router = createRouter({
    routeTree: root.addChildren([route, ...others]),
    history: createMemoryHistory({ initialEntries: ["/admin/categories"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

function panel() {
  return screen.getByTestId("curation-qa-panel");
}

describe("CurationQaPanel — the six checks (Story 52.3)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("mounts between the page header and the category list, with an accessible name", async () => {
    installFetch();
    mount(<CategoriesPage />);

    const section = await screen.findByTestId("curation-qa-panel");
    // AC-8 — accessible name via aria-labelledby on its own heading.
    expect(section.getAttribute("aria-labelledby")).toBe("curation-qa-heading");
    const heading = within(section).getByRole("heading", { level: 2 });
    expect(heading.id).toBe("curation-qa-heading");
    // Mount position: after the <header>, before the category list.
    const list = await screen.findByTestId("browse-category-storage");
    expect(section.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders every check in the D-7 order (AC-16)", async () => {
    installFetch();
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-finding-empty:c2");

    const ids = within(panel())
      .getAllByTestId(/^curation-finding-/)
      .map((el) => el.getAttribute("data-testid"));
    expect(ids).toEqual([
      "curation-finding-empty:c2",
      "curation-finding-tiny:c3",
      "curation-finding-collision:c3:t1",
      "curation-finding-over:m1",
      "curation-finding-uncategorized",
      "curation-finding-ungrouped",
    ]);
  });

  it("states the finding count in the heading, not the rendered-row count (AC-9)", async () => {
    installFetch();
    mount(<CategoriesPage />);
    const section = await screen.findByTestId("curation-qa-panel");
    expect(await within(section).findByRole("heading", { name: "Curation QA (6)" })).toBeTruthy();
  });

  it("names the tag's group, and renders no suffix for a groupless tag (AC-12)", async () => {
    installFetch();
    mount(<CategoriesPage />);
    const row = await screen.findByTestId("curation-finding-collision:c3:t1");
    expect(within(row).getByText('Label collision: category “Vases” / tag “Vases” (Type)')).toBeTruthy();

    cleanup();
    installFetch({
      tagGroups: { groups: [], groupless: [{ ...TAG_GROUPS.groups[0]!.tags[0]!, group_id: null }] },
    });
    mount(<CategoriesPage />);
    const groupless = await screen.findByTestId("curation-finding-collision:c3:t1");
    expect(within(groupless).getByText('Label collision: category “Vases” / tag “Vases”')).toBeTruthy();
  });

  it("carries the affected entity's name in every row action's accessible name (AC-26)", async () => {
    installFetch();
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-finding-empty:c2");

    const labels = within(panel())
      .getAllByTestId(/^curation-finding-/)
      .map((row) => row.querySelector("a[aria-label], button[aria-label]")?.getAttribute("aria-label") ?? "");
    expect(labels).toEqual([
      "Go to category Replacement parts in the list",
      "Go to category Vases in the list",
      "Resolve the label collision between category Vases and tag Vases in tag groups",
      "Edit categories for model Spiral vase",
      "Go to the list of models with no category",
      "Go to tag groups to place the tags with no group",
    ]);
    // A shared generic label is exactly the low-severity finding recorded
    // against 52.2's queue; these must all differ.
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("sends the SHARED advisory threshold to the server, so the panel and the editor cannot diverge (AC-7)", async () => {
    const fetchMock = installFetch();
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-finding-over:m1");

    const urls = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) => url.includes("over-categorized"));
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) {
      expect(url).toContain(`min_categories=${ADVISORY_MAX + 1}`);
    }
  });
});

describe("CurationQaPanel — states (AC-18..AC-21)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("renders an aria-hidden skeleton while a source is unresolved — no count, no empty state", async () => {
    installFetch({ tagGroupsPending: true });
    mount(<CategoriesPage />);

    const skeleton = await screen.findByTestId("curation-qa-skeleton");
    expect(skeleton.getAttribute("aria-hidden")).toBe("true");
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Curation QA");
    expect(screen.queryByTestId("curation-qa-empty")).toBeNull();
    expect(within(panel()).queryAllByTestId(/^curation-finding-/)).toHaveLength(0);
  });

  it("renders the empty state ONLY when all four sources resolved with zero findings (AC-21)", async () => {
    installFetch({
      categories: [cat()],
      tagGroups: { groups: [], groupless: [] },
      overCategorized: { items: [], total: 0 },
      queueTotal: 0,
    });
    mount(<CategoriesPage />);

    const empty = await screen.findByTestId("curation-qa-empty");
    expect(empty.textContent).toBe("Nothing needs attention.");
    // Unlike DuplicateTagsPanel, the section itself does not disappear.
    expect(panel()).toBeTruthy();
  });

  it("on a failed source with no data: renders the other checks, names the gap, offers a retry, and NEVER the empty state (AC-20)", async () => {
    installFetch({
      overCategorizedError: true,
      categories: [cat()],
      tagGroups: { groups: [], groupless: [] },
      queueTotal: 0,
    });
    mount(<CategoriesPage />);

    const partial = await screen.findByTestId("curation-qa-partial");
    expect(within(partial).getByText("Some checks could not run — one of the reads did not complete.")).toBeTruthy();
    expect(within(partial).getByRole("button", { name: "Retry" })).toBeTruthy();
    // The heading must not assert a total it cannot know: "(0)" printed beside
    // "some checks could not run" is the same fabricated-green claim as the
    // empty state itself.
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Curation QA");
    // The other sources produced zero findings, and the panel STILL must not
    // claim "Nothing needs attention." — that is D-6's whole point.
    expect(screen.queryByTestId("curation-qa-empty")).toBeNull();
  });

  it("computes from cached data when a source errors while holding a cache (AC-19)", async () => {
    // Direct props: a background-refetch error on a query that already has data
    // must not blank the panel.
    const source = <T,>(data: T | undefined, isError = false) => ({
      data,
      isError,
      isFetching: false,
      refetch: () => {},
    });
    mount(
      <CurationQaPanel
        categories={source(CATEGORIES, true)}
        uncategorized={source({ total: 0 })}
        tagGroups={source({ groups: [], groupless: [] })}
        overCategorized={source({ items: [], total: 0 })}
        localize={(en) => en}
        onEditModelCategories={() => {}}
      />,
    );
    expect(await screen.findByTestId("curation-finding-empty:c2")).toBeTruthy();
    expect(screen.queryByTestId("curation-qa-partial")).toBeNull();
    expect(screen.queryByTestId("curation-qa-empty")).toBeNull();
  });
});

describe("CurationQaPanel — bounded rows and the advisory-only contract", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("caps a check at five rows and states the true remaining count, non-interactively (AC-17)", async () => {
    installFetch({
      categories: Array.from({ length: 8 }, (_, i) =>
        cat({ id: `e${i}`, slug: `e${i}`, position: i, model_count: 0 }),
      ),
      tagGroups: { groups: [], groupless: [] },
      overCategorized: { items: [], total: 0 },
      queueTotal: 0,
    });
    mount(<CategoriesPage />);

    const overflow = await screen.findByTestId("curation-overflow-empty_category");
    expect(within(panel()).getAllByTestId(/^curation-finding-/)).toHaveLength(5);
    expect(overflow.textContent).toBe("3 more findings in this check.");
    // Not a focus stop.
    expect(overflow.getAttribute("tabindex")).toBeNull();
    expect(within(overflow).queryByRole("button")).toBeNull();
    expect(within(overflow).queryByRole("link")).toBeNull();
    // The heading still counts findings, not rows.
    expect(within(panel()).getByRole("heading", { level: 2 }).textContent).toBe("Curation QA (8)");
  });

  it("issues no write: the over-categorized action opens the SHIPPED replace-set editor (AC-22)", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetch();
    mount(<CategoriesPage />);

    const row = await screen.findByTestId("curation-finding-over:m1");
    await user.click(within(row).getByRole("button", { name: "Edit categories for model Spiral vase" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Model categories" })).toBeTruthy());
    const nonGet = fetchMock.mock.calls.filter((call) => {
      const init = (call[1] ?? {}) as RequestInit;
      return (init.method ?? "GET") !== "GET";
    });
    expect(nonGet).toHaveLength(0);
  });

  it("uses only the warning token family — destructive appears nowhere (AC-24)", async () => {
    installFetch();
    mount(<CategoriesPage />);
    await screen.findByTestId("curation-finding-empty:c2");

    for (const el of panel().querySelectorAll<HTMLElement>("*")) {
      // `className` is an SVGAnimatedString on SVG nodes, so read the attribute.
      for (const token of (el.getAttribute("class") ?? "").split(/\s+/)) {
        // Unconditional destructive styling only — the shipped Button primitive
        // legitimately carries `aria-invalid:`-prefixed destructive variants.
        expect(token, `${token} is a destructive token on an advisory surface`).not.toMatch(
          /^(text|bg|border|ring)-destructive/,
        );
      }
    }
  });
});
