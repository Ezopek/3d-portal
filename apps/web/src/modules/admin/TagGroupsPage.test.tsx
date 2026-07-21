import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { TagGroupsResponse } from "@/lib/api-types";
import { TagGroupsPage } from "@/modules/admin/TagGroupsPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function response(overrides: Partial<TagGroupsResponse> = {}): TagGroupsResponse {
  return {
    groups: [
      {
        id: "g1",
        slug: "material",
        name_en: "Material",
        name_pl: "Materiał",
        position: 0,
        tags: [
          {
            id: "t1",
            slug: "pla",
            name_en: "PLA",
            name_pl: null,
            group_id: "g1",
            group_position: 0,
            model_count: 12,
          },
          {
            id: "t2",
            slug: "petg",
            name_en: "PETG",
            name_pl: null,
            group_id: "g1",
            group_position: 1,
            model_count: 3,
          },
        ],
      },
      {
        id: "g2",
        slug: "style",
        name_en: "Style",
        name_pl: "Styl",
        position: 1,
        tags: [],
      },
    ],
    groupless: [
      {
        id: "t3",
        slug: "misc",
        name_en: "Misc",
        name_pl: null,
        group_id: null,
        group_position: 0,
        model_count: 1,
      },
    ],
    ...overrides,
  };
}

function installFetch(
  opts: { data?: TagGroupsResponse; error?: boolean; pending?: boolean } = {},
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/api/tag-groups")) {
      if (opts.pending) return new Promise<Response>(() => {}); // never resolves → loading
      if (opts.error) {
        return new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(opts.data ?? response()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** First call fails, every call after succeeds with `data` — for retry-recovery assertions. */
function installFailThenSucceed(data: TagGroupsResponse = response()) {
  let calls = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/api/tag-groups")) {
      calls += 1;
      if (calls === 1) {
        return new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(data), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/tag-groups",
    component: () => <>{node}</>,
  });
  const fallback = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([route, fallback]),
    history: createMemoryHistory({ initialEntries: ["/admin/tag-groups"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("TagGroupsPage (Story 46.1)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("shows a skeleton while loading, not a bare spinner", async () => {
    installFetch({ pending: true });
    mount(<TagGroupsPage />);
    expect(await screen.findByTestId("tag-groups-skeleton")).toBeTruthy();
  });

  it("renders groups in position order with tags + model_count (happy path)", async () => {
    installFetch();
    mount(<TagGroupsPage />);
    expect(await screen.findByText("Material")).toBeTruthy();
    expect(screen.getByText("PLA")).toBeTruthy();
    expect(screen.getByText("12 models")).toBeTruthy();
    expect(screen.getByText("PETG")).toBeTruthy();
    expect(screen.getByText("3 models")).toBeTruthy();

    // position order: Material (position 0) before Style (position 1)
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings.indexOf("Material")).toBeLessThan(headings.indexOf("Style"));
  });

  it("renders an inline empty-state message for a group with zero tags", async () => {
    installFetch();
    mount(<TagGroupsPage />);
    expect(await screen.findByText("Style")).toBeTruthy();
    expect(screen.getByText("No tags in this group.")).toBeTruthy();
  });

  it("renders the Ungrouped section when groupless tags are present", async () => {
    installFetch();
    mount(<TagGroupsPage />);
    expect(await screen.findByText("Ungrouped")).toBeTruthy();
    expect(screen.getByText("Misc")).toBeTruthy();
    expect(screen.getByText("1 model")).toBeTruthy();
  });

  it("omits the Ungrouped section entirely when there are no groupless tags", async () => {
    installFetch({ data: response({ groupless: [] }) });
    mount(<TagGroupsPage />);
    await screen.findByText("Material");
    expect(screen.queryByText("Ungrouped")).toBeNull();
  });

  it("shows an explicit empty state when there are no groups and no groupless tags", async () => {
    installFetch({ data: { groups: [], groupless: [] } });
    mount(<TagGroupsPage />);
    expect(await screen.findByText("No tag groups yet.")).toBeTruthy();
  });

  it("fails closed on a read error: error panel + Retry, never a blank/crashed page", async () => {
    const fetchMock = installFetch({ error: true });
    mount(<TagGroupsPage />);
    expect(await screen.findByText("Couldn't load the tag groups")).toBeTruthy();
    const retry = screen.getByRole("button", { name: "Retry" });
    expect(retry).toBeTruthy();
    expect(screen.queryByText("Material")).toBeNull();
    const before = fetchMock.mock.calls.length;
    fireEvent.click(retry);
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(before));
  });

  it("recovers on retry: a successful refetch replaces the error panel with real data", async () => {
    installFailThenSucceed();
    mount(<TagGroupsPage />);
    const retry = await screen.findByRole("button", { name: "Retry" });
    fireEvent.click(retry);
    expect(await screen.findByText("Material")).toBeTruthy();
    expect(screen.queryByText("Couldn't load the tag groups")).toBeNull();
  });
});
