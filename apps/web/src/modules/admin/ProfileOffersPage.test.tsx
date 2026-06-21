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

import type {
  DefaultMatrixBackfillResponse,
  PolicyAdminView,
  PrintProfileOffer,
  ProfileLibraryBlock,
} from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { ProfileOffersPage } from "@/modules/admin/ProfileOffersPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const MACHINE_ID = "3".repeat(32);
const PROCESS_ID = "1".repeat(32);
const FILAMENT_ID = "2".repeat(32);

function libBlock(
  overrides: Partial<ProfileLibraryBlock> = {},
): ProfileLibraryBlock {
  return {
    block_id: "0".repeat(32),
    profile_type: "process",
    name: "Block",
    source: "user",
    is_system: false,
    inherit: null,
    inherit_chain: [],
    settings_id: null,
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

const LIBRARY: ProfileLibraryBlock[] = [
  libBlock({ block_id: MACHINE_ID, profile_type: "machine", name: "K1 Max" }),
  libBlock({
    block_id: PROCESS_ID,
    profile_type: "process",
    name: "0.20 MicroSwiss",
  }),
  libBlock({
    block_id: FILAMENT_ID,
    profile_type: "filament",
    name: "Rosa PLA",
    material_type: "PLA",
  }),
];

function offer(overrides: Partial<PrintProfileOffer> = {}): PrintProfileOffer {
  return {
    offer_id: "a".repeat(32),
    label: "Rosa PLA — standard",
    description: null,
    chain: {
      machine_block_id: MACHINE_ID,
      process_block_id: PROCESS_ID,
      filament_block_id: FILAMENT_ID,
    },
    visibility: "visible",
    is_default: false,
    compatible_material_categories: ["PLA"],
    validation_state: "usable",
    reasons: [],
    chain_blocks: [
      libBlock({
        block_id: MACHINE_ID,
        profile_type: "machine",
        name: "K1 Max",
      }),
      libBlock({
        block_id: PROCESS_ID,
        profile_type: "process",
        name: "0.20 MicroSwiss",
      }),
      libBlock({
        block_id: FILAMENT_ID,
        profile_type: "filament",
        name: "Rosa PLA",
        material_type: "PLA",
        inherit_chain: ["Generic PLA @System"],
      }),
    ],
    created_at: "2026-06-06T00:00:00+00:00",
    created_by: "00000000-0000-0000-0000-000000000001",
    updated_at: "2026-06-06T00:00:00+00:00",
    publish_state: "unpublished",
    published_bundle_hash: null,
    published_at: null,
    published_by: null,
    source_snapshot_ref: null,
    published_stl_hash: null,
    sync_state: "unknown",
    ...overrides,
  };
}

function policyView(overrides: Partial<PolicyAdminView> = {}): PolicyAdminView {
  return {
    policy: { material_defaults: {}, filament_overrides: {} },
    spoolman_materials: [],
    spoolman_filaments: [],
    orca_filament_profile_names: [
      "Generic PLA @System",
      "Generic PETG @System",
    ],
    ...overrides,
  };
}

function backfillResponse(
  overrides: Partial<DefaultMatrixBackfillResponse> = {},
): DefaultMatrixBackfillResponse {
  return {
    dry_run: true,
    inspected: 4,
    cells_total: 6,
    cells_resolved: 6,
    cells_resolve_failed: 0,
    enqueued: 0,
    already_fresh: 1,
    missing_stl: 0,
    errors: 0,
    would_enqueue: 5,
    ...overrides,
  };
}

interface FetchState {
  offers: PrintProfileOffer[];
  library?: ProfileLibraryBlock[];
  postStatus?: number;
  postBody?: unknown;
  patchStatus?: number;
  patchBody?: unknown;
  /** Default mocked `GET /api/admin/policy` payload (and the body PUT upserts echo back). */
  policy?: PolicyAdminView;
  /** Mocked `POST /api/admin/policy/default-matrix-backfill` summary. */
  backfill?: DefaultMatrixBackfillResponse;
  /** Mocked `POST /api/admin/profiles/offers/recompute-estimates` summary. */
  recompute?: DefaultMatrixBackfillResponse;
  recomputeStatus?: number;
}

/** Install a stateful `fetch` stub — we intercept the network, never mock `api()` (T6). */
function installFetch(state: FetchState) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.includes("/api/admin/profiles/offers/recompute-estimates")) {
        return new Response(JSON.stringify(state.recompute ?? backfillResponse()), {
          status: state.recomputeStatus ?? 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/api/admin/profiles/offers")) {
        if (method === "GET") {
          return new Response(JSON.stringify({ offers: state.offers }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "POST" && url.includes("/publish")) {
          return new Response(
            JSON.stringify({
              offer_id: "a".repeat(32),
              published_bundle_hash: "b".repeat(64),
              publish_state: "published",
              published_at: "2026-06-06T00:00:00+00:00",
              estimate_job_id: "job-1",
              estimate: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (method === "POST") {
          return new Response(JSON.stringify(state.postBody ?? offer()), {
            status: state.postStatus ?? 201,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "PATCH") {
          return new Response(JSON.stringify(state.patchBody ?? offer()), {
            status: state.patchStatus ?? 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (method === "DELETE") {
          state.offers = [];
          return new Response(null, { status: 204 });
        }
      }
      if (url.includes("/api/admin/profiles/library")) {
        return new Response(
          JSON.stringify({ blocks: state.library ?? LIBRARY }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
      // Profile-policy surface (ProfilePolicyPanel) — backfill POST + material-default
      // upsert/delete + the base view. All keyed off the same `/api/admin/policy` prefix.
      if (url.includes("/api/admin/policy/default-matrix-backfill")) {
        return new Response(
          JSON.stringify(state.backfill ?? backfillResponse()),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
      if (url.includes("/api/admin/policy/material-defaults/")) {
        if (method === "DELETE") {
          return new Response(null, { status: 204 });
        }
        // PUT echoes back the (unchanged here) policy view, matching the real upsert.
        return new Response(JSON.stringify(state.policy ?? policyView()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/api/admin/policy")) {
        return new Response(JSON.stringify(state.policy ?? policyView()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
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
    path: "/admin/profile-offers",
    component: () => <>{node}</>,
  });
  const fallback = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([route, fallback]),
    history: createMemoryHistory({ initialEntries: ["/admin/profile-offers"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ProfileOffersPage (PROFILE-OFFER-1)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("primary offer recompute dry-run posts visible current offers and renders counters", async () => {
    const fetchMock = installFetch({
      offers: [offer()],
      recompute: backfillResponse({ would_enqueue: 3, inspected: 2 }),
    });
    mount(<ProfileOffersPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /inspect current offers/i }),
    );

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([url, init]) =>
          (typeof url === "string" ? url : String(url)).includes(
            "/api/admin/profiles/offers/recompute-estimates",
          ) && (init?.method ?? "GET").toUpperCase() === "POST",
      );
      expect(post).toBeTruthy();
      expect(JSON.parse((post?.[1]?.body as string) ?? "{}")).toEqual({
        dry_run: true,
        visible_only: true,
      });
    });
    expect(await screen.findAllByText(/would enqueue/i)).toHaveLength(2);
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("primary offer recompute confirmed run posts dry_run:false visible_only:true", async () => {
    const fetchMock = installFetch({
      offers: [offer()],
      recompute: backfillResponse({ dry_run: false, would_enqueue: 0, enqueued: 4 }),
    });
    mount(<ProfileOffersPage />);
    fireEvent.click(await screen.findByRole("button", { name: /run recompute/i }));
    fireEvent.click(await screen.findByRole("button", { name: /^confirm$/i }));

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([url, init]) =>
          (typeof url === "string" ? url : String(url)).includes(
            "/api/admin/profiles/offers/recompute-estimates",
          ) && (init?.method ?? "GET").toUpperCase() === "POST",
      );
      expect(post).toBeTruthy();
      expect(JSON.parse((post?.[1]?.body as string) ?? "{}")).toEqual({
        dry_run: false,
        visible_only: true,
      });
    });
    expect(await screen.findAllByText(/enqueued/i)).toHaveLength(2);
    expect(screen.getAllByText("4").length).toBeGreaterThan(0);
  });

  it("primary offer recompute errors surface visibly", async () => {
    installFetch({ offers: [offer()], recomputeStatus: 500 });
    mount(<ProfileOffersPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /inspect current offers/i }),
    );
    expect(await screen.findByText(/recompute request failed/i)).toBeTruthy();
  });

  it("advanced policy fetch is gated until the legacy panel is opened", async () => {
    const fetchMock = installFetch({ offers: [] });
    mount(<ProfileOffersPage />);
    await screen.findByText(/no offers composed yet/i);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        (typeof url === "string" ? url : String(url)).includes("/api/admin/policy"),
      ),
    ).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /show advanced/i }));
    await screen.findByText(/advanced \/ legacy material defaults/i);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          (typeof url === "string" ? url : String(url)).includes("/api/admin/policy"),
        ),
      ).toBe(true),
    );
  });

  it("renders offers with validation badges across all three states", async () => {
    installFetch({
      offers: [
        offer({
          offer_id: "a".repeat(32),
          label: "Good",
          validation_state: "usable",
        }),
        offer({
          offer_id: "b".repeat(32),
          label: "Flagged",
          validation_state: "requires_attention",
          reasons: ["filament_machine_incompatible"],
        }),
        offer({
          offer_id: "c".repeat(32),
          label: "Broken",
          validation_state: "invalid",
          reasons: ["unknown_block"],
        }),
      ],
    });
    mount(<ProfileOffersPage />);
    expect(await screen.findByText("Good")).toBeTruthy();
    expect(screen.getByText("Flagged")).toBeTruthy();
    expect(screen.getByText("Broken")).toBeTruthy();
    expect(screen.getByText("Usable")).toBeTruthy();
    expect(screen.getByText("Needs attention")).toBeTruthy();
    expect(screen.getByText("Invalid")).toBeTruthy();
    // invalid row surfaces its first reason inline.
    expect(
      screen.getByText(/a selected block no longer exists in the library/i),
    ).toBeTruthy();
  });

  it("renders stale sync badge only for stale offers", async () => {
    installFetch({
      offers: [
        offer({
          offer_id: "a".repeat(32),
          label: "Stale offer",
          sync_state: "stale",
        }),
        offer({
          offer_id: "b".repeat(32),
          label: "Current offer",
          sync_state: "current",
        }),
      ],
    });
    mount(<ProfileOffersPage />);
    expect(await screen.findByText("Stale offer")).toBeTruthy();
    expect(screen.getByText("Current offer")).toBeTruthy();
    expect(screen.getByText("Stale")).toBeTruthy();
    expect(screen.queryByText("Current")).toBeNull();
  });

  it("shows republish only for stale published valid offers and posts the published STL hash", async () => {
    const fetchMock = installFetch({
      offers: [
        offer({
          label: "Needs republish",
          publish_state: "published",
          published_stl_hash: "c".repeat(64),
          sync_state: "stale",
          validation_state: "usable",
        }),
        offer({
          offer_id: "b".repeat(32),
          label: "Invalid stale",
          publish_state: "published",
          published_stl_hash: "d".repeat(64),
          sync_state: "stale",
          validation_state: "invalid",
          reasons: ["unknown_block"],
        }),
        offer({
          offer_id: "e".repeat(32),
          label: "Unpublished stale",
          publish_state: "unpublished",
          sync_state: "stale",
        }),
      ],
    });
    mount(<ProfileOffersPage />);
    const row = (await screen.findByText("Needs republish")).closest(
      "li",
    ) as HTMLElement;
    expect(
      within(row).getByRole("button", { name: /^republish$/i }),
    ).toBeTruthy();
    expect(
      within(
        screen.getByText("Invalid stale").closest("li") as HTMLElement,
      ).queryByRole("button", {
        name: /republish/i,
      }),
    ).toBeNull();
    expect(
      within(
        screen.getByText("Unpublished stale").closest("li") as HTMLElement,
      ).queryByRole("button", {
        name: /republish/i,
      }),
    ).toBeNull();

    fireEvent.click(within(row).getByRole("button", { name: /^republish$/i }));

    await waitFor(() => {
      const publishCall = fetchMock.mock.calls.find(
        ([input, init]) =>
          (typeof input === "string" ? input : String(input)).includes(
            "/publish",
          ) && (init?.method ?? "GET").toUpperCase() === "POST",
      );
      expect(publishCall).toBeTruthy();
      expect(JSON.parse((publishCall?.[1]?.body as string) ?? "{}")).toEqual({
        stl_hash: "c".repeat(64),
      });
    });
    await waitFor(() => {
      const offerGets = fetchMock.mock.calls.filter(
        ([input, init]) =>
          (typeof input === "string" ? input : String(input)).includes(
            "/api/admin/profiles/offers",
          ) &&
          !(typeof input === "string" ? input : String(input)).includes(
            "/publish",
          ) &&
          (init?.method ?? "GET").toUpperCase() === "GET",
      );
      expect(offerGets.length).toBeGreaterThan(1);
    });
  });

  it("disables republish when a stale published offer has no published STL hash", async () => {
    installFetch({
      offers: [
        offer({
          label: "No hash",
          publish_state: "published",
          published_stl_hash: null,
          sync_state: "stale",
        }),
      ],
    });
    mount(<ProfileOffersPage />);
    const row = (await screen.findByText("No hash")).closest(
      "li",
    ) as HTMLElement;
    expect(
      within(row)
        .getByRole("button", { name: /republish/i })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(within(row).getByText(/no published stl hash/i)).toBeTruthy();
  });

  it("empty inventory shows the empty state", async () => {
    installFetch({ offers: [] });
    mount(<ProfileOffersPage />);
    expect(await screen.findByText(/no offers composed yet/i)).toBeTruthy();
  });

  it("fails closed/visible on a load error with a retry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url.includes("/api/admin/profiles/offers")) {
          return new Response("{}", { status: 500 });
        }
        if (url.includes("/api/admin/policy")) {
          return new Response(JSON.stringify(policyView()), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify({ blocks: LIBRARY }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
    mount(<ProfileOffersPage />);
    expect(await screen.findByText(/couldn't load the offers/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
  });

  it("detail expander shows curated chain blocks + reasons (no raw JSON)", async () => {
    installFetch({
      offers: [
        offer({
          label: "Flagged",
          validation_state: "requires_attention",
          reasons: ["filament_machine_incompatible"],
        }),
      ],
    });
    const { container } = mount(<ProfileOffersPage />);
    const row = await screen.findByText("Flagged");
    fireEvent.click(
      within(row.closest("li") as HTMLElement).getByRole("button", {
        name: /show details/i,
      }),
    );
    expect(await screen.findByText(/Generic PLA @System/)).toBeTruthy();
    expect(
      screen.getByText(
        /this filament isn't declared compatible with this machine/i,
      ),
    ).toBeTruthy();
    // No raw Orca JSON node anywhere on the page.
    expect(container.textContent).not.toContain("outer_wall_speed");
    expect(container.textContent).not.toContain("layer_height");
  });

  it("composes an offer: pick three blocks + label → POST, then list reconciles", async () => {
    const state: FetchState = { offers: [] };
    const fetchMock = installFetch(state);
    mount(<ProfileOffersPage />);
    await screen.findByText(/no offers composed yet/i);

    fireEvent.click(screen.getByRole("button", { name: /compose offer/i }));
    fireEvent.change(await screen.findByLabelText("Machine block"), {
      target: { value: MACHINE_ID },
    });
    fireEvent.change(screen.getByLabelText("Process block"), {
      target: { value: PROCESS_ID },
    });
    fireEvent.change(screen.getByLabelText("Filament block"), {
      target: { value: FILAMENT_ID },
    });
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "My offer" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save offer/i }));

    await waitFor(() => {
      const posted = fetchMock.mock.calls.find(
        ([input, init]) =>
          (typeof input === "string" ? input : String(input)).includes(
            "/api/admin/profiles/offers",
          ) && (init?.method ?? "GET").toUpperCase() === "POST",
      );
      expect(posted).toBeTruthy();
      const body = JSON.parse((posted?.[1]?.body as string) ?? "{}");
      expect(body.label).toBe("My offer");
      expect(body.chain.machine_block_id).toBe(MACHINE_ID);
      expect(body.chain.process_block_id).toBe(PROCESS_ID);
      expect(body.chain.filament_block_id).toBe(FILAMENT_ID);
    });
  });

  it("localizes a create rejection reason category (fails closed/visible)", async () => {
    installFetch({
      offers: [],
      postStatus: 422,
      postBody: { detail: { reason_category: "invalid_chain", message: "x" } },
    });
    mount(<ProfileOffersPage />);
    await screen.findByText(/no offers composed yet/i);
    fireEvent.click(screen.getByRole("button", { name: /compose offer/i }));
    fireEvent.change(await screen.findByLabelText("Machine block"), {
      target: { value: MACHINE_ID },
    });
    fireEvent.change(screen.getByLabelText("Process block"), {
      target: { value: PROCESS_ID },
    });
    fireEvent.change(screen.getByLabelText("Filament block"), {
      target: { value: FILAMENT_ID },
    });
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Bad" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save offer/i }));
    expect(
      await screen.findByText(/the selected blocks don't form a valid chain/i),
    ).toBeTruthy();
  });

  it("edit keeps the chain read-only and PATCHes label/visibility/default/categories", async () => {
    const fetchMock = installFetch({ offers: [offer({ label: "Editable" })] });
    mount(<ProfileOffersPage />);
    const row = await screen.findByText("Editable");
    fireEvent.click(
      within(row.closest("li") as HTMLElement).getByRole("button", {
        name: /edit editable/i,
      }),
    );
    // Chain pickers are NOT selects in edit mode (immutable) — no <select> rendered.
    await screen.findByText(/edit offer/i);
    expect(screen.queryByLabelText("Machine block")?.tagName).not.toBe(
      "SELECT",
    );
    expect(
      screen.getByText(/to change the selected blocks, delete this offer/i),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Renamed" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save offer/i }));

    await waitFor(() => {
      const patched = fetchMock.mock.calls.find(
        ([, init]) => (init?.method ?? "GET").toUpperCase() === "PATCH",
      );
      expect(patched).toBeTruthy();
      const body = JSON.parse((patched?.[1]?.body as string) ?? "{}");
      expect(body.label).toBe("Renamed");
      expect("chain" in body).toBe(false);
    });
  });

  it("delete confirm fires DELETE and the list reconciles from the server", async () => {
    const state: FetchState = { offers: [offer({ label: "Doomed" })] };
    installFetch(state);
    mount(<ProfileOffersPage />);
    const row = await screen.findByText("Doomed");
    fireEvent.click(
      within(row.closest("li") as HTMLElement).getByRole("button", {
        name: /delete doomed/i,
      }),
    );
    const confirm = await screen.findByRole("button", { name: /^confirm$/i });
    fireEvent.click(confirm);
    await waitFor(() => expect(screen.queryByText("Doomed")).toBeNull());
    expect(screen.getByText(/no offers composed yet/i)).toBeTruthy();
  });

  it("policy panel renders and warns when no material default is enabled", async () => {
    installFetch({ offers: [] });
    mount(<ProfileOffersPage />);
    // The panel is collapsed by default — expand it to reveal the table + backfill controls.
    fireEvent.click(await screen.findByRole("button", { name: /show advanced/i }));
    // Panel header proves the policy view resolved (no undefined material_defaults).
    expect(await screen.findByText(/advanced \/ legacy material defaults/i)).toBeTruthy();
    // Empty material_defaults → the backfill matrix would be empty, so warn.
    expect(
      await screen.findByText(/no enabled material defaults/i),
    ).toBeTruthy();
  });

  it("saving a material default PUTs to /material-defaults/PLA with the expected body", async () => {
    const fetchMock = installFetch({ offers: [] });
    mount(<ProfileOffersPage />);
    fireEvent.click(await screen.findByRole("button", { name: /show advanced/i }));
    const input = await screen.findByLabelText("Orca filament profile for PLA");
    fireEvent.change(input, { target: { value: "Generic PLA @System" } });
    const row = input.closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([url, init]) =>
          (typeof url === "string" ? url : String(url)).includes(
            "/api/admin/policy/material-defaults/PLA",
          ) && (init?.method ?? "GET").toUpperCase() === "PUT",
      );
      expect(put).toBeTruthy();
      expect(JSON.parse((put?.[1]?.body as string) ?? "{}")).toEqual({
        orca_filament_profile_ref: "Generic PLA @System",
        enabled: true,
      });
    });
  });

  it("inspect backfill POSTs dry_run:true and renders the returned counters", async () => {
    const fetchMock = installFetch({
      offers: [],
      policy: policyView({
        policy: {
          material_defaults: {
            PLA: {
              orca_filament_profile_ref: "Generic PLA @System",
              enabled: true,
            },
          },
          filament_overrides: {},
        },
      }),
      backfill: backfillResponse({ would_enqueue: 5, inspected: 4 }),
    });
    mount(<ProfileOffersPage />);
    fireEvent.click(await screen.findByRole("button", { name: /show advanced/i }));
    const inspect = await screen.findByRole("button", {
      name: /inspect backfill/i,
    });
    // The button is gated on an enabled default — wait for the policy fetch to land.
    await waitFor(() => expect(inspect.hasAttribute("disabled")).toBe(false));
    fireEvent.click(inspect);

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([url, init]) =>
          (typeof url === "string" ? url : String(url)).includes(
            "/api/admin/policy/default-matrix-backfill",
          ) && (init?.method ?? "GET").toUpperCase() === "POST",
      );
      expect(post).toBeTruthy();
      expect(JSON.parse((post?.[1]?.body as string) ?? "{}")).toMatchObject({
        dry_run: true,
        include_overrides: false,
        material: null,
      });
    });
    // Counter grid surfaces the returned summary (label + value).
    expect(await screen.findAllByText(/would enqueue/i)).toHaveLength(2);
    expect(screen.getByText("5")).toBeTruthy();
  });
});
