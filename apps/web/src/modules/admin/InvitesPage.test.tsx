import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import type {
  AdminInviteRow,
  AdminInvitesListResponse,
  GenerateInviteResponse,
} from "@/lib/api-types";
import i18n from "@/locales/i18n";

const generateMutate = vi.fn();
const revokeMutate = vi.fn();

vi.mock("@/modules/admin/hooks/useAdminInvites", () => ({
  useAdminInvites: vi.fn(),
  useGenerateInvite: vi.fn(),
  useRevokeInvite: vi.fn(),
}));

vi.mock("@/shell/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/shell/AuthContext";
import {
  useAdminInvites,
  useGenerateInvite,
  useRevokeInvite,
} from "@/modules/admin/hooks/useAdminInvites";
import { InvitesPage } from "@/modules/admin/InvitesPage";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

beforeEach(() => {
  generateMutate.mockReset();
  revokeMutate.mockReset();
  vi.mocked(useGenerateInvite).mockReturnValue({
    mutate: generateMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useGenerateInvite>);
  vi.mocked(useRevokeInvite).mockReturnValue({
    mutate: revokeMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useRevokeInvite>);
  vi.mocked(useAuth).mockReturnValue({
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "admin@localhost.localdomain",
      display_name: "Admin",
      role: "admin",
    },
    role: "admin",
    isAdmin: true,
    isMember: false,
    isAdminOrAgent: true,
    isAuthenticated: true,
    isLoading: false,
  });
});

function mockListHook(value: {
  data?: AdminInvitesListResponse;
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
}) {
  vi.mocked(useAdminInvites).mockReturnValue({
    data: value.data,
    isLoading: value.isLoading ?? false,
    isError: value.isError ?? false,
    error: value.error ?? null,
  } as unknown as ReturnType<typeof useAdminInvites>);
}

function mount(node: ReactNode, initialPath = "/admin/invites") {
  const root = createRootRoute();
  const invitesRoute = createRoute({
    getParentRoute: () => root,
    path: "/admin/invites",
    component: () => <>{node}</>,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const fallbackRoute = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([invitesRoute, fallbackRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...utils, router };
}

function seedRow(overrides: Partial<AdminInviteRow>): AdminInviteRow {
  return {
    id: "00000000-0000-0000-0000-aaaaaaaaaaaa",
    invite_id: "00000000-0000-0000-0000-aaaaaaaaaaaa",
    token_hash: "abc123",
    role: "member",
    ttl_seconds: 7 * 24 * 60 * 60,
    generated_by_user_id: "00000000-0000-0000-0000-000000000001",
    generated_at: "2026-05-19T10:00:00Z",
    expires_at: "2026-05-26T10:00:00Z",
    used_by_user_id: null,
    used_at: null,
    used_from_ip: null,
    revoked_at: null,
    status: "active",
    ...overrides,
  };
}

describe("InvitesPage", () => {
  it("I1 — renders empty state when total=0", async () => {
    mockListHook({
      data: { total: 0, items: [], page: 1, page_size: 50 },
    });
    mount(<InvitesPage />);
    await waitFor(() => {
      expect(
        screen.getByText(
          /brak zaproszeń pasujących do filtru|no invites match this filter/i,
        ),
      ).toBeTruthy();
    });
  });

  it("I2 — renders 4 rows with mixed statuses + Revoke visible only for active", async () => {
    mockListHook({
      data: {
        total: 4,
        page: 1,
        page_size: 50,
        items: [
          seedRow({
            invite_id: "00000000-0000-0000-0000-000000000a01",
            status: "active",
          }),
          seedRow({
            invite_id: "00000000-0000-0000-0000-000000000a02",
            status: "used",
            used_by_user_id: "00000000-0000-0000-0000-000000000b02",
            used_at: "2026-05-20T11:00:00Z",
            used_from_ip: "10.0.0.42",
          }),
          seedRow({
            invite_id: "00000000-0000-0000-0000-000000000a03",
            status: "expired",
            expires_at: "2026-05-10T00:00:00Z",
          }),
          seedRow({
            invite_id: "00000000-0000-0000-0000-000000000a04",
            status: "revoked",
            revoked_at: "2026-05-18T09:00:00Z",
          }),
        ],
      },
    });
    mount(<InvitesPage />);

    await waitFor(() => {
      expect(document.querySelectorAll("tbody tr")).toHaveLength(4);
    });

    // Only one Revoke button — for the active row
    const revokeButtons = screen.getAllByRole("button", { name: /^Odwołaj$|^Revoke$/i });
    expect(revokeButtons).toHaveLength(1);

    // Each of the 4 status badges rendered inside the table body (the
    // filter dropdown's <option> values also use the same labels — pick
    // only the in-table occurrences via the table-body root).
    const tbody = document.querySelector("tbody") as HTMLElement;
    expect(tbody).not.toBeNull();
    const badges = tbody.querySelectorAll("span.inline-flex");
    const badgeText = Array.from(badges).map((b) => b.textContent?.trim());
    expect(badgeText).toEqual(["Active", "Used", "Expired", "Revoked"]);
  });

  it("I3 — changing status filter navigates to /admin/invites with status search param", async () => {
    mockListHook({
      data: { total: 0, items: [], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    const { router } = mount(<InvitesPage />);

    const filterSelect = (await waitFor(() =>
      screen.getByLabelText(/^Status$/i),
    )) as HTMLSelectElement;
    await user.selectOptions(filterSelect, "used");

    await waitFor(() => {
      expect(router.state.location.searchStr).toContain("status=used");
    });
  });

  it("I4 — clicking Generate button opens GenerateInviteModal", async () => {
    mockListHook({
      data: { total: 0, items: [], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<InvitesPage />);

    const generateBtn = await waitFor(() =>
      screen.getByRole("button", { name: /wygeneruj zaproszenie|generate invite/i }),
    );
    await user.click(generateBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/wygeneruj nowe zaproszenie|generate new invite/i),
      ).toBeTruthy();
    });
  });

  it("I5 — submitting GenerateInviteModal calls useGenerateInvite and opens InviteTokenDisplayModal on success", async () => {
    mockListHook({
      data: { total: 0, items: [], page: 1, page_size: 50 },
    });

    const resp: GenerateInviteResponse = {
      invite_id: "00000000-0000-0000-0000-000000000a99",
      token: "TKN_ABC123",
      registration_url: "/register?token=TKN_ABC123",
      role: "member",
      ttl_seconds: 7 * 24 * 60 * 60,
      generated_at: "2026-05-20T12:00:00Z",
      expires_at: "2026-05-27T12:00:00Z",
    };
    generateMutate.mockImplementation((_payload, opts) => {
      opts?.onSuccess?.(resp);
    });

    const user = userEvent.setup();
    mount(<InvitesPage />);

    await user.click(
      await waitFor(() =>
        screen.getByRole("button", { name: /wygeneruj zaproszenie|generate invite/i }),
      ),
    );
    // Submit (defaults: role=member, ttl_preset=SEVEN_DAYS)
    await user.click(
      await waitFor(() =>
        screen.getByRole("button", { name: /^Wygeneruj$|^Generate$/i }),
      ),
    );

    expect(generateMutate).toHaveBeenCalledTimes(1);
    expect(generateMutate.mock.calls[0]?.[0]).toEqual({
      role: "member",
      ttl_preset: "SEVEN_DAYS",
    });

    // Token-display modal opens — registration URL rendered as absolute URL
    const expectedAbsolute = new URL(
      resp.registration_url,
      window.location.origin,
    ).toString();
    await waitFor(() => {
      expect(screen.getByDisplayValue(expectedAbsolute)).toBeTruthy();
    });
  });

  it("I6 — clicking Revoke on an active row opens ConfirmDialog", async () => {
    mockListHook({
      data: {
        total: 1,
        page: 1,
        page_size: 50,
        items: [seedRow({ status: "active" })],
      },
    });
    const user = userEvent.setup();
    mount(<InvitesPage />);

    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Odwołaj$|^Revoke$/i })),
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          /odwołać zaproszenie dla roli member|revoke invite for member role/i,
        ),
      ).toBeTruthy();
    });
  });

  it("I7 — confirming revoke dispatches useRevokeInvite with the row's invite_id", async () => {
    const inviteId = "00000000-0000-0000-0000-000000000aaa";
    mockListHook({
      data: {
        total: 1,
        page: 1,
        page_size: 50,
        items: [seedRow({ invite_id: inviteId, status: "active" })],
      },
    });
    revokeMutate.mockImplementation((_id, opts) => {
      opts?.onSuccess?.();
    });
    const user = userEvent.setup();
    mount(<InvitesPage />);

    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Odwołaj$|^Revoke$/i })),
    );
    // ConfirmDialog confirm button (Confirm / Potwierdź in EN locale = "Confirm")
    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Potwierdź$|^Confirm$/i })),
    );

    expect(revokeMutate).toHaveBeenCalledTimes(1);
    expect(revokeMutate.mock.calls[0]?.[0]).toBe(inviteId);
  });

  it("I8 — revoke 409 error renders invite_already_resolved inline error", async () => {
    mockListHook({
      data: {
        total: 1,
        page: 1,
        page_size: 50,
        items: [seedRow({ status: "active" })],
      },
    });
    const err = new ApiError(
      409,
      { detail: "invite_already_resolved" },
      "conflict",
    );
    revokeMutate.mockImplementation((_id, opts) => {
      opts?.onError?.(err);
    });
    const user = userEvent.setup();
    mount(<InvitesPage />);

    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Odwołaj$|^Revoke$/i })),
    );
    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Potwierdź$|^Confirm$/i })),
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          /zaproszenie zostało już wykorzystane|this invite is already used or revoked/i,
        ),
      ).toBeTruthy();
    });
  });

  it("I9 — revoke 404 error renders invite_not_found inline error", async () => {
    mockListHook({
      data: {
        total: 1,
        page: 1,
        page_size: 50,
        items: [seedRow({ status: "active" })],
      },
    });
    const err = new ApiError(
      404,
      { detail: "invite_not_found" },
      "not found",
    );
    revokeMutate.mockImplementation((_id, opts) => {
      opts?.onError?.(err);
    });
    const user = userEvent.setup();
    mount(<InvitesPage />);

    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Odwołaj$|^Revoke$/i })),
    );
    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /^Potwierdź$|^Confirm$/i })),
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          /zaproszenie nie zostało znalezione|invite not found/i,
        ),
      ).toBeTruthy();
    });
  });
});
