import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { AdminProfileSlot, AdminProfileStatus } from "@/lib/api-types";
import i18n from "@/locales/i18n";

vi.mock("@/modules/admin/hooks/useAdminProfiles", () => ({
  useAdminProfiles: vi.fn(),
}));

import { useAdminProfiles } from "@/modules/admin/hooks/useAdminProfiles";
import { ProfilesPage } from "@/modules/admin/ProfilesPage";

afterEach(cleanup);

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

beforeEach(() => {
  vi.mocked(useAdminProfiles).mockReset();
});

function mockHook(value: {
  data?: { printer_ref: string; slots: AdminProfileSlot[] };
  isLoading?: boolean;
  isError?: boolean;
}) {
  vi.mocked(useAdminProfiles).mockReturnValue({
    data: value.data,
    isLoading: value.isLoading ?? false,
    isError: value.isError ?? false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAdminProfiles>);
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/profiles",
    component: () => <>{node}</>,
  });
  const fallback = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([route, fallback]),
    history: createMemoryHistory({ initialEntries: ["/admin/profiles"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function slot(
  material: AdminProfileSlot["material_class"],
  tier: AdminProfileSlot["quality_tier"],
  status: AdminProfileStatus,
): AdminProfileSlot {
  return {
    material_class: material,
    quality_tier: tier,
    imported: status !== "not_imported",
    resolvable: status === "offerable",
    compatible: status !== "incompatible",
    offerable: status === "offerable",
    status,
    reason: status === "offerable" ? null : "profile_not_imported",
    portal_label: null,
    provenance:
      status === "offerable"
        ? { source_system_tree_hash: "abcdef012345", orca_version: "2.3.2" }
        : { source_system_tree_hash: null, orca_version: null },
  };
}

const ALL_NOT_IMPORTED: AdminProfileSlot[] = (["PLA", "PETG", "PCTG", "TPU"] as const).flatMap(
  (m) =>
    (["aesthetic", "standard", "strong"] as const).map((t) =>
      slot(m, t, m === "TPU" && t !== "strong" ? "incompatible" : "not_imported"),
    ),
);

describe("ProfilesPage (Story 33.1 — AC-15 states)", () => {
  it("renders a skeleton matrix while loading, not a bare spinner", async () => {
    mockHook({ isLoading: true });
    mount(<ProfilesPage />);
    expect(await screen.findByTestId("profiles-skeleton")).toBeTruthy();
  });

  it("fails CLOSED/visible on error: shows an error panel with Retry", async () => {
    mockHook({ isError: true });
    mount(<ProfilesPage />);
    expect(await screen.findByText(/couldn't load profiles/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
    // Must NOT fabricate slot statuses / fall open to "all offerable".
    expect(screen.queryByText("Offerable")).toBeNull();
  });

  it("empty state renders the all-not-imported grid plus a one-line hint", async () => {
    mockHook({ data: { printer_ref: "creality-k1-max-microswiss-hf", slots: ALL_NOT_IMPORTED } });
    mount(<ProfilesPage />);
    expect(await screen.findByText(/no profiles imported yet/i)).toBeTruthy();
    // The grid still renders all slots (not a blank grid).
    expect(screen.getAllByText("Not imported").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Incompatible").length).toBeGreaterThan(0);
  });

  it("with offerable slots renders the grid and shows no empty hint", async () => {
    const slots = ALL_NOT_IMPORTED.map((s) =>
      s.material_class === "PLA" && s.quality_tier === "standard"
        ? slot("PLA", "standard", "offerable")
        : s,
    );
    mockHook({ data: { printer_ref: "creality-k1-max-microswiss-hf", slots } });
    mount(<ProfilesPage />);
    // The discriminating signal: an offerable slot exists, so the empty hint is absent.
    expect(await screen.findByText(/process profiles/i)).toBeTruthy();
    expect(screen.queryByText(/no profiles imported yet/i)).toBeNull();
  });
});
