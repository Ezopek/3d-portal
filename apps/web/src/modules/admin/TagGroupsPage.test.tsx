import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  opts: {
    data?: TagGroupsResponse;
    error?: boolean;
    pending?: boolean;
    /** Status returned for any non-read (write) request — used to exercise inline errors. */
    writeStatus?: number;
  } = {},
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    // GET /api/tag-groups is the read; the admin write endpoints all live under
    // /api/admin/* so they never collide with this substring.
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
    // Any write endpoint: succeed with a trivial 200 body unless a failure is requested.
    if (opts.writeStatus && opts.writeStatus >= 400) {
      return new Response(JSON.stringify({ detail: "conflict" }), {
        status: opts.writeStatus,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// Return every write (PATCH/POST) call to a URL containing `urlSubstr`, as
// { method, url, body } with the JSON body parsed. Reads (GET) are ignored.
function writeCalls(
  fetchMock: ReturnType<typeof vi.fn>,
  method: string,
  urlSubstr: string,
): { method: string; url: string; body: Record<string, unknown> }[] {
  return fetchMock.mock.calls
    .map((call) => {
      const input = call[0] as RequestInfo | URL;
      const init = (call[1] ?? {}) as RequestInit;
      const url = typeof input === "string" ? input : input.toString();
      return { url, init };
    })
    .filter(({ url, init }) => init.method === method && url.includes(urlSubstr))
    .map(({ url, init }) => ({
      method: init.method as string,
      url,
      body: init.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {},
    }));
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

function readCount(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((call) => {
    const input = call[0] as RequestInfo | URL;
    const url = typeof input === "string" ? input : input.toString();
    return url.includes("/api/tag-groups");
  }).length;
}

describe("TagGroupsPage write actions (Story 46.2)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("rename tag → PATCH /admin/tags/{id} with only the changed name field, then refreshes", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("PLA");

    await user.click(screen.getByRole("button", { name: "Actions for tag PLA" }));
    await user.click(await screen.findByRole("menuitem", { name: "Rename" }));

    const nameEn = await screen.findByLabelText("English name");
    await user.clear(nameEn);
    await user.type(nameEn, "PLA Plus");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")).toHaveLength(1),
    );
    expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")[0]?.body).toEqual({
      name_en: "PLA Plus",
    });
    // Successful write invalidates the read → list refreshes (>1 GET /tag-groups).
    await waitFor(() => expect(readCount(fetchMock)).toBeGreaterThanOrEqual(2));
  });

  it("clear Polish name → PATCH sends name_pl: null", async () => {
    const data = response({
      groupless: [
        {
          id: "t3",
          slug: "misc",
          name_en: "Misc",
          name_pl: "Różne",
          group_id: null,
          group_position: 0,
          model_count: 1,
        },
      ],
    });
    const fetchMock = installFetch({ data });
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Misc");

    await user.click(screen.getByRole("button", { name: "Actions for tag Misc" }));
    await user.click(await screen.findByRole("menuitem", { name: "Rename" }));

    await user.clear(await screen.findByLabelText("Polish name"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t3")).toHaveLength(1),
    );
    expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t3")[0]?.body).toEqual({
      name_pl: null,
    });
  });

  it("rename group → PATCH /admin/tag-groups/{id} with changed fields", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Material");

    await user.click(screen.getByRole("button", { name: "Actions for group Material" }));
    await user.click(await screen.findByRole("menuitem", { name: "Rename" }));

    const nameEn = await screen.findByLabelText("English name");
    await user.clear(nameEn);
    await user.type(nameEn, "Materials");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g1")).toHaveLength(1),
    );
    expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g1")[0]?.body).toEqual({
      name_en: "Materials",
    });
  });

  it("move tag into a group → group_position is the target's current tag count", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("PLA");

    await user.click(screen.getByRole("button", { name: "Actions for tag PLA" }));
    await user.click(await screen.findByRole("menuitem", { name: "Move to group" }));

    const select = await screen.findByLabelText("Target group");
    await user.selectOptions(select, within(select).getByRole("option", { name: "Style" }));
    await user.click(screen.getByRole("button", { name: "Move" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")).toHaveLength(1),
    );
    // Style (g2) currently holds 0 tags → append at position 0.
    expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")[0]?.body).toEqual({
      group_id: "g2",
      group_position: 0,
    });
  });

  it("move tag to Ungrouped → group_id: null with group_position = groupless count", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("PLA");

    await user.click(screen.getByRole("button", { name: "Actions for tag PLA" }));
    await user.click(await screen.findByRole("menuitem", { name: "Move to group" }));

    const select = await screen.findByLabelText("Target group");
    await user.selectOptions(select, within(select).getByRole("option", { name: "Ungrouped" }));
    await user.click(screen.getByRole("button", { name: "Move" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")).toHaveLength(1),
    );
    // One groupless tag (Misc) already exists → append at position 1.
    expect(writeCalls(fetchMock, "PATCH", "/admin/tags/t1")[0]?.body).toEqual({
      group_id: null,
      group_position: 1,
    });
  });

  it("merge tag → POST /admin/tags/merge { from_id, to_id }", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("PLA");

    await user.click(screen.getByRole("button", { name: "Actions for tag PLA" }));
    await user.click(await screen.findByRole("menuitem", { name: "Merge into…" }));

    const select = await screen.findByLabelText("Survivor tag");
    await user.selectOptions(select, within(select).getByRole("option", { name: "PETG" }));
    await user.click(screen.getByRole("button", { name: "Merge" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "POST", "/admin/tags/merge")).toHaveLength(1),
    );
    expect(writeCalls(fetchMock, "POST", "/admin/tags/merge")[0]?.body).toEqual({
      from_id: "t1",
      to_id: "t2",
    });
  });

  it("create group → POST /admin/tag-groups with position = current group count", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Material");

    await user.click(screen.getByRole("button", { name: "Create group" }));
    await user.type(await screen.findByLabelText("Slug"), "finish");
    await user.type(screen.getByLabelText("English name"), "Finish");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "POST", "/admin/tag-groups")).toHaveLength(1),
    );
    expect(writeCalls(fetchMock, "POST", "/admin/tag-groups")[0]?.body).toEqual({
      slug: "finish",
      name_en: "Finish",
      name_pl: null,
      position: 2,
    });
  });

  it("reorder group up → two PATCHes swap adjacent positions", async () => {
    const fetchMock = installFetch();
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Style");

    await user.click(screen.getByRole("button", { name: "Actions for group Style" }));
    await user.click(await screen.findByRole("menuitem", { name: "Move up" }));

    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/")).toHaveLength(2),
    );
    // Style (g2, position 1) takes Material's slot (0); Material (g1) takes 1.
    expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g2")[0]?.body).toEqual({
      position: 0,
    });
    expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g1")[0]?.body).toEqual({
      position: 1,
    });
  });

  it("reorder partial failure rolls back the first PATCH so no two groups share a position", async () => {
    // First swap PATCH (g2 → 0) succeeds; the second (g1 → 1) fails. The page must
    // then restore g2 to its original position (1) so the server never keeps two
    // groups at the same `position` (an inconsistent, slug-tie-broken order).
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/tag-groups")) {
        return new Response(JSON.stringify(response()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/admin/tag-groups/g1")) {
        return new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Style");

    await user.click(screen.getByRole("button", { name: "Actions for group Style" }));
    await user.click(await screen.findByRole("menuitem", { name: "Move up" }));

    // g2 is written twice: the forward swap to 0, then the compensating rollback to 1.
    await waitFor(() =>
      expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g2")).toHaveLength(2),
    );
    const g2Writes = writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g2");
    expect(g2Writes[0]?.body).toEqual({ position: 0 });
    expect(g2Writes[1]?.body).toEqual({ position: 1 }); // rollback to original
    // g1 was attempted exactly once (the failed second PATCH), never left applied.
    expect(writeCalls(fetchMock, "PATCH", "/admin/tag-groups/g1")).toHaveLength(1);
  });

  it("boundary reorder: first group can't move up, last can't move down", async () => {
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Material");

    await user.click(screen.getByRole("button", { name: "Actions for group Material" }));
    const moveUp = await screen.findByRole("menuitem", { name: "Move up" });
    expect(moveUp.getAttribute("aria-disabled") === "true" || moveUp.hasAttribute("data-disabled")).toBe(
      true,
    );

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Actions for group Style" }));
    const moveDown = await screen.findByRole("menuitem", { name: "Move down" });
    expect(
      moveDown.getAttribute("aria-disabled") === "true" || moveDown.hasAttribute("data-disabled"),
    ).toBe(true);
  });

  it("write conflict (409) keeps the dialog open with an inline error", async () => {
    const fetchMock = installFetch({ writeStatus: 409 });
    const user = userEvent.setup();
    mount(<TagGroupsPage />);
    await screen.findByText("Material");

    await user.click(screen.getByRole("button", { name: "Create group" }));
    await user.type(await screen.findByLabelText("Slug"), "material");
    await user.type(screen.getByLabelText("English name"), "Material 2");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("That name or slug is already in use.")).toBeTruthy();
    // Dialog stays open (submit button still rendered), request was attempted.
    expect(screen.getByRole("button", { name: "Create" })).toBeTruthy();
    expect(writeCalls(fetchMock, "POST", "/admin/tag-groups")).toHaveLength(1);
  });
});
