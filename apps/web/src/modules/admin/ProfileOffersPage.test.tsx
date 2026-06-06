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
import type { ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { PrintProfileOffer, ProfileLibraryBlock } from "@/lib/api-types";
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

function libBlock(overrides: Partial<ProfileLibraryBlock> = {}): ProfileLibraryBlock {
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
    ...overrides,
  };
}

const LIBRARY: ProfileLibraryBlock[] = [
  libBlock({ block_id: MACHINE_ID, profile_type: "machine", name: "K1 Max" }),
  libBlock({ block_id: PROCESS_ID, profile_type: "process", name: "0.20 MicroSwiss" }),
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
      libBlock({ block_id: MACHINE_ID, profile_type: "machine", name: "K1 Max" }),
      libBlock({ block_id: PROCESS_ID, profile_type: "process", name: "0.20 MicroSwiss" }),
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
}

/** Install a stateful `fetch` stub — we intercept the network, never mock `api()` (T6). */
function installFetch(state: FetchState) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = (init?.method ?? "GET").toUpperCase();
    if (url.includes("/api/admin/profiles/offers")) {
      if (method === "GET") {
        return new Response(JSON.stringify({ offers: state.offers }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
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
      return new Response(JSON.stringify({ blocks: state.library ?? LIBRARY }), {
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

  it("renders offers with validation badges across all three states", async () => {
    installFetch({
      offers: [
        offer({ offer_id: "a".repeat(32), label: "Good", validation_state: "usable" }),
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
      within(row.closest("li") as HTMLElement).getByRole("button", { name: /show details/i }),
    );
    expect(await screen.findByText(/Generic PLA @System/)).toBeTruthy();
    expect(
      screen.getByText(/this filament isn't declared compatible with this machine/i),
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
    fireEvent.change(screen.getByLabelText("Process block"), { target: { value: PROCESS_ID } });
    fireEvent.change(screen.getByLabelText("Filament block"), { target: { value: FILAMENT_ID } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "My offer" } });

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
    fireEvent.change(screen.getByLabelText("Process block"), { target: { value: PROCESS_ID } });
    fireEvent.change(screen.getByLabelText("Filament block"), { target: { value: FILAMENT_ID } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Bad" } });
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
      within(row.closest("li") as HTMLElement).getByRole("button", { name: /edit editable/i }),
    );
    // Chain pickers are NOT selects in edit mode (immutable) — no <select> rendered.
    await screen.findByText(/edit offer/i);
    expect(screen.queryByLabelText("Machine block")?.tagName).not.toBe("SELECT");
    expect(screen.getByText(/to change the selected blocks, delete this offer/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Renamed" } });
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
      within(row.closest("li") as HTMLElement).getByRole("button", { name: /delete doomed/i }),
    );
    const confirm = await screen.findByRole("button", { name: /^confirm$/i });
    fireEvent.click(confirm);
    await waitFor(() => expect(screen.queryByText("Doomed")).toBeNull());
    expect(screen.getByText(/no offers composed yet/i)).toBeTruthy();
  });
});
