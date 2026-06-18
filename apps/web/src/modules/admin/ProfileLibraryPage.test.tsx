import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import type { ProfileLibraryBlock } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { ProfileLibraryPage } from "@/modules/admin/ProfileLibraryPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

function block(
  overrides: Partial<ProfileLibraryBlock> = {},
): ProfileLibraryBlock {
  return {
    block_id: "0".repeat(32),
    profile_type: "process",
    name: "AI 0.20mm TPU - FlowTech",
    source: "user",
    is_system: false,
    inherit: "0.20mm Standard @Creality K1Max (0.4 nozzle)",
    inherit_chain: ["0.20mm Standard @Creality K1Max (0.4 nozzle)"],
    settings_id: "AI 0.20mm TPU - FlowTech",
    material_type: null,
    compatible_printers: [],
    validation_state: "usable",
    reasons: [],
    portal_label: null,
    imported_at: "2026-06-06T00:00:00+00:00",
    imported_by: "00000000-0000-0000-0000-000000000001",
    stale_offers: [],
    ...overrides,
  };
}

interface FetchState {
  blocks: ProfileLibraryBlock[];
  postStatus?: number;
  postBody?: unknown;
  offers?: Array<{ offer_id: string; published_stl_hash?: string | null }>;
}

/** Install a stateful `fetch` stub — we intercept the network, never mock `api()` (T5). */
function installFetch(state: FetchState) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.includes("/api/admin/profiles/offers")) {
        if (method === "GET") {
          return new Response(JSON.stringify({ offers: state.offers ?? [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "POST" && url.includes("/publish")) {
          return new Response(
            JSON.stringify({
              offer_id: url.split("/").at(-2) ?? "offer",
              published_bundle_hash: "b".repeat(64),
              publish_state: "published",
              published_at: "2026-06-06T00:00:00+00:00",
              estimate_job_id: "job-1",
              estimate: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
      }
      if (url.includes("/api/admin/profiles/library")) {
        if (method === "GET") {
          return new Response(JSON.stringify({ blocks: state.blocks }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "POST") {
          const status = state.postStatus ?? 201;
          return new Response(JSON.stringify(state.postBody ?? block()), {
            status,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "DELETE") {
          state.blocks = [];
          return new Response(null, { status: 204 });
        }
      }
      return new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/profile-library",
    component: () => <>{node}</>,
  });
  const fallback = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([route, fallback]),
    history: createMemoryHistory({
      initialEntries: ["/admin/profile-library"],
    }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ProfileLibraryPage (PROFILE-LIB-1)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("renders imported blocks with curated metadata + validation badges", async () => {
    installFetch({
      blocks: [
        block({ name: "Usable Proc", validation_state: "usable" }),
        block({
          block_id: "1".repeat(32),
          name: "Flagged Proc",
          validation_state: "requires_attention",
          reasons: ["user_process_invalid_inheritance"],
        }),
      ],
    });
    mount(<ProfileLibraryPage />);
    expect(await screen.findByText("Usable Proc")).toBeTruthy();
    expect(screen.getByText("Flagged Proc")).toBeTruthy();
    expect(screen.getByText("Usable")).toBeTruthy();
    expect(screen.getByText("Needs attention")).toBeTruthy();
  });

  it("empty inventory shows the empty state", async () => {
    installFetch({ blocks: [] });
    mount(<ProfileLibraryPage />);
    expect(
      await screen.findByText(/no profile blocks imported yet/i),
    ).toBeTruthy();
  });

  it("fails closed/visible on a load error with a retry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 500 })),
    );
    mount(<ProfileLibraryPage />);
    expect(
      await screen.findByText(/couldn't load the profile library/i),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
  });

  it("detail expander shows the inherit chain + flagged reasons (no raw JSON)", async () => {
    installFetch({
      blocks: [
        block({
          name: "Flagged Proc",
          validation_state: "requires_attention",
          reasons: ["user_process_invalid_inheritance"],
          inherit_chain: ["Parent A", "Parent B"],
        }),
      ],
    });
    const { container } = mount(<ProfileLibraryPage />);
    const row = await screen.findByText("Flagged Proc");
    fireEvent.click(
      within(row.closest("li") as HTMLElement).getByRole("button", {
        name: /show details/i,
      }),
    );
    expect(await screen.findByText(/Parent A → Parent B/)).toBeTruthy();
    expect(
      screen.getByText(/a user process must inherit a system process/i),
    ).toBeTruthy();
    // No raw Orca JSON node anywhere on the page.
    expect(container.textContent).not.toContain("outer_wall_speed");
    expect(container.textContent).not.toContain("layer_height");
  });

  it("localizes an import rejection reason category (fails closed/visible)", async () => {
    installFetch({
      blocks: [],
      postStatus: 422,
      postBody: {
        detail: { reason_category: "unsupported_profile", message: "x" },
      },
    });
    const { container } = mount(<ProfileLibraryPage />);
    await screen.findByText(/no profile blocks imported yet/i);
    const fileInput = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(['{"a":1}'], "weird.json", {
      type: "application/json",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });
    expect(
      await screen.findByText(/couldn't classify this orca profile block/i),
    ).toBeTruthy();
  });

  it("shows stale-offer notification after import and republish now publishes each offer", async () => {
    const staleOffers = [
      {
        offer_id: "a".repeat(32),
        label: "PLA standard",
        publish_state: "published" as const,
      },
      {
        offer_id: "b".repeat(32),
        label: "TPU strong",
        publish_state: "published" as const,
      },
    ];
    const fetchMock = installFetch({
      blocks: [],
      postBody: block({ name: "Imported", stale_offers: staleOffers }),
      offers: [
        { offer_id: "a".repeat(32), published_stl_hash: "c".repeat(64) },
        { offer_id: "b".repeat(32), published_stl_hash: "d".repeat(64) },
      ],
    });
    const { container } = mount(<ProfileLibraryPage />);
    await screen.findByText(/no profile blocks imported yet/i);
    const fileInput = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: {
        files: [
          new File(['{"a":1}'], "profile.json", { type: "application/json" }),
        ],
      },
    });

    expect(
      await screen.findByText(
        /2 published offer\(s\) now require republish: PLA standard, TPU strong/i,
      ),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /republish now/i }));

    await waitFor(() =>
      expect(screen.getByText(/PLA standard: republished/i)).toBeTruthy(),
    );
    await waitFor(() =>
      expect(screen.getByText(/TPU strong: republished/i)).toBeTruthy(),
    );
    const publishCalls = fetchMock.mock.calls.filter(
      ([input, init]) =>
        (typeof input === "string" ? input : String(input)).includes(
          "/publish",
        ) && (init?.method ?? "GET").toUpperCase() === "POST",
    );
    expect(publishCalls).toHaveLength(2);
    const firstPublishInit = publishCalls[0]![1]!;
    const secondPublishInit = publishCalls[1]![1]!;
    expect(JSON.parse(String(firstPublishInit.body))).toEqual({
      stl_hash: "c".repeat(64),
    });
    expect(JSON.parse(String(secondPublishInit.body))).toEqual({
      stl_hash: "d".repeat(64),
    });
  });

  it("dismisses stale-offer notification with Later without publish calls", async () => {
    const fetchMock = installFetch({
      blocks: [],
      postBody: block({
        name: "Imported",
        stale_offers: [
          {
            offer_id: "a".repeat(32),
            label: "PLA standard",
            publish_state: "published",
          },
        ],
      }),
    });
    const { container } = mount(<ProfileLibraryPage />);
    await screen.findByText(/no profile blocks imported yet/i);
    const fileInput = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: {
        files: [
          new File(['{"a":1}'], "profile.json", { type: "application/json" }),
        ],
      },
    });

    expect(await screen.findByText(/PLA standard/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /later/i }));
    await waitFor(() => expect(screen.queryByText(/PLA standard/i)).toBeNull());
    const publishCalls = fetchMock.mock.calls.filter(([input]) =>
      (typeof input === "string" ? input : String(input)).includes("/publish"),
    );
    expect(publishCalls).toHaveLength(0);
  });

  it("does not show stale-offer notification when import response has none", async () => {
    installFetch({
      blocks: [],
      postBody: block({ name: "Imported", stale_offers: [] }),
    });
    const { container } = mount(<ProfileLibraryPage />);
    await screen.findByText(/no profile blocks imported yet/i);
    const fileInput = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: {
        files: [
          new File(['{"a":1}'], "profile.json", { type: "application/json" }),
        ],
      },
    });
    await waitFor(() =>
      expect(screen.queryByText(/require republish/i)).toBeNull(),
    );
  });

  it("delete confirm fires DELETE and the list reconciles from the server", async () => {
    const state: FetchState = { blocks: [block({ name: "Doomed" })] };
    installFetch(state);
    mount(<ProfileLibraryPage />);
    const row = await screen.findByText("Doomed");
    fireEvent.click(
      within(row.closest("li") as HTMLElement).getByRole("button", {
        name: /delete doomed/i,
      }),
    );
    // Confirm dialog → confirm.
    const confirm = await screen.findByRole("button", { name: /^confirm$/i });
    fireEvent.click(confirm);
    await waitFor(() => expect(screen.queryByText("Doomed")).toBeNull());
    expect(screen.getByText(/no profile blocks imported yet/i)).toBeTruthy();
  });
});
