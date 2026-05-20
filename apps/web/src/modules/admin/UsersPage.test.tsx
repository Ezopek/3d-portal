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

import type {
  AdminUser,
  AdminUsersListResponse,
} from "@/lib/api-types";
import i18n from "@/locales/i18n";

const updateMutate = vi.fn();
const forceLogoutMutate = vi.fn();
const force2faEnrollmentMutate = vi.fn();
const forceDisable2faMutate = vi.fn();

vi.mock("@/modules/admin/hooks/useAdminUsers", () => ({
  useAdminUsers: vi.fn(),
  useUpdateAdminUser: vi.fn(),
  useForceLogoutAdminUser: vi.fn(),
  useForce2faEnrollmentAdminUser: vi.fn(),
  useForceDisable2faAdminUser: vi.fn(),
}));

vi.mock("@/shell/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/shell/AuthContext";
import {
  useAdminUsers,
  useForce2faEnrollmentAdminUser,
  useForceDisable2faAdminUser,
  useForceLogoutAdminUser,
  useUpdateAdminUser,
} from "@/modules/admin/hooks/useAdminUsers";
import { UsersPage } from "@/modules/admin/UsersPage";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const ADMIN_ID = "00000000-0000-0000-0000-000000000001";

beforeEach(() => {
  updateMutate.mockReset();
  forceLogoutMutate.mockReset();
  force2faEnrollmentMutate.mockReset();
  forceDisable2faMutate.mockReset();
  vi.mocked(useUpdateAdminUser).mockReturnValue({
    mutate: updateMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useUpdateAdminUser>);
  vi.mocked(useForceLogoutAdminUser).mockReturnValue({
    mutate: forceLogoutMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useForceLogoutAdminUser>);
  vi.mocked(useForce2faEnrollmentAdminUser).mockReturnValue({
    mutate: force2faEnrollmentMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useForce2faEnrollmentAdminUser>);
  vi.mocked(useForceDisable2faAdminUser).mockReturnValue({
    mutate: forceDisable2faMutate,
    isPending: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useForceDisable2faAdminUser>);
  vi.mocked(useAuth).mockReturnValue({
    user: {
      id: ADMIN_ID,
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

function mockHook(value: {
  data?: AdminUsersListResponse;
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
}) {
  vi.mocked(useAdminUsers).mockReturnValue({
    data: value.data,
    isLoading: value.isLoading ?? false,
    isError: value.isError ?? false,
    error: value.error ?? null,
  } as unknown as ReturnType<typeof useAdminUsers>);
}

function mount(node: ReactNode, initialPath = "/admin/users") {
  const root = createRootRoute();
  const adminUsersRoute = createRoute({
    getParentRoute: () => root,
    path: "/admin/users",
    component: () => <>{node}</>,
    validateSearch: (raw: Record<string, unknown>) => raw,
  });
  const fallbackRoute = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([adminUsersRoute, fallbackRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

const seedAdminItem: AdminUser = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "admin@localhost.localdomain",
  display_name: "Admin",
  role: "admin",
  created_at: "2026-05-19T00:00:00Z",
  last_active_at: "2026-05-20T00:00:00Z",
  totp_enabled: false,
  is_active: true,
  force_2fa_enrollment: false,
};

function seedMembers(n: number): AdminUser[] {
  const out: AdminUser[] = [];
  for (let i = 0; i < n; i += 1) {
    out.push({
      id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`,
      email: `member${i}@test.example`,
      display_name: `Member ${i}`,
      role: "member",
      created_at: "2026-05-19T00:00:00Z",
      last_active_at: null,
      totp_enabled: false,
      is_active: true,
      force_2fa_enrollment: false,
    });
  }
  return out;
}

describe("UsersPage", () => {
  it("V1 — renders table with all 7 columns for a non-empty response", async () => {
    mockHook({
      data: {
        total: 1,
        items: [seedAdminItem],
        page: 1,
        page_size: 50,
      },
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("columnheader", { name: /Email/i }),
      ).toBeTruthy();
    });
    expect(
      screen.getByRole("columnheader", { name: /Display name/i }),
    ).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /Role/i })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /^2FA/i })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /^Active$/ })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /Created/i })).toBeTruthy();
    expect(
      screen.getByRole("columnheader", { name: /Last active/i }),
    ).toBeTruthy();
    expect(screen.getByText("admin@localhost.localdomain")).toBeTruthy();
  });

  it("V2 — renders empty-state message when total=0", async () => {
    mockHook({
      data: { total: 0, items: [], page: 1, page_size: 50 },
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText(/No users match this filter/i)).toBeTruthy();
    });
    const tbodyRows = document.querySelectorAll("tbody tr");
    // The empty-state placeholder is a single tr with one td colspan; the
    // assertion is that NO data row was rendered (placeholder is fine).
    expect(tbodyRows.length).toBe(1);
    expect(document.querySelector("tbody tr td[colspan]")).toBeTruthy();
  });

  it("V3 — renders error message when query.error is non-null", async () => {
    mockHook({
      data: undefined,
      isError: true,
      error: new Error("boom"),
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText(/Could not load users/i)).toBeTruthy();
    });
  });

  it("V4 — renders zero checkboxes and zero bulk-action buttons (FR5-ADMIN-4)", async () => {
    mockHook({
      data: { total: 5, items: seedMembers(5), page: 1, page_size: 50 },
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member0@test.example")).toBeTruthy();
    });
    expect(screen.queryAllByRole("checkbox").length).toBe(0);
    expect(
      screen.queryAllByRole("button", { name: /bulk|select all/i }).length,
    ).toBe(0);
    expect(document.querySelectorAll('input[type="checkbox"]').length).toBe(0);
  });

  const memberRow: AdminUser = {
    id: "00000000-0000-0000-0000-000000000010",
    email: "member@test.example",
    display_name: "Member",
    role: "member",
    created_at: "2026-05-19T00:00:00Z",
    last_active_at: null,
    totp_enabled: false,
    is_active: true,
    force_2fa_enrollment: false,
  };

  const agentRow: AdminUser = {
    id: "00000000-0000-0000-0000-000000000020",
    email: "agent@portal.local",
    display_name: "Agent",
    role: "agent",
    created_at: "2026-05-19T00:00:00Z",
    last_active_at: null,
    totp_enabled: false,
    is_active: true,
    force_2fa_enrollment: false,
  };

  const inactiveMemberRow: AdminUser = {
    ...memberRow,
    id: "00000000-0000-0000-0000-000000000030",
    email: "inactive@test.example",
    is_active: false,
  };

  it("V5 — renders an actions kebab button for every non-self non-agent row", async () => {
    mockHook({
      data: {
        total: 3,
        items: [seedAdminItem, memberRow, agentRow],
        page: 1,
        page_size: 50,
      },
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    const memberKebab = screen.getByRole("button", {
      name: /Actions for member@test\.example/i,
    });
    expect(memberKebab.hasAttribute("disabled")).toBe(false);

    const agentKebab = screen.getByRole("button", {
      name: /Actions for agent@portal\.local/i,
    });
    expect(agentKebab.getAttribute("aria-disabled")).toBe("true");

    const ownKebab = screen.getByRole("button", {
      name: /Actions for admin@localhost\.localdomain/i,
    });
    expect(ownKebab.getAttribute("aria-disabled")).toBe("true");
  });

  it("V6 — opens action menu on kebab click and lists items for active user", async () => {
    mockHook({
      data: { total: 1, items: [memberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );

    await waitFor(() => {
      expect(screen.getByText("Change role")).toBeTruthy();
    });
    expect(screen.getByText("Deactivate")).toBeTruthy();
    expect(screen.getByText("Force logout all sessions")).toBeTruthy();
    expect(screen.queryByText("Reactivate")).toBeNull();
  });

  it("V7 — opens action menu and shows Reactivate instead of Deactivate for inactive user", async () => {
    mockHook({
      data: { total: 1, items: [inactiveMemberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("inactive@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for inactive@test\.example/i }),
    );

    await waitFor(() => {
      expect(screen.getByText("Reactivate")).toBeTruthy();
    });
    expect(screen.queryByText("Deactivate")).toBeNull();
  });

  it("V8 — clicking Deactivate opens confirm modal then PATCH on confirm", async () => {
    mockHook({
      data: { total: 1, items: [memberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Deactivate")).toBeTruthy();
    });
    await user.click(screen.getByText("Deactivate"));

    await waitFor(() => {
      expect(
        screen.getByText(/Deactivate member@test\.example\?/i),
      ).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: /^Confirm$/i }));

    expect(updateMutate).toHaveBeenCalledTimes(1);
    const call = updateMutate.mock.calls[0];
    if (!call) throw new Error("expected mutate call");
    expect(call[0]).toEqual({
      user_id: memberRow.id,
      body: { is_active: false },
    });
  });

  it("V9 — clicking Force logout opens confirm modal then POST on confirm", async () => {
    mockHook({
      data: { total: 1, items: [memberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Force logout all sessions")).toBeTruthy();
    });
    await user.click(screen.getByText("Force logout all sessions"));

    await waitFor(() => {
      expect(
        screen.getByText(/Force logout member@test\.example\?/i),
      ).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: /^Confirm$/i }));

    expect(forceLogoutMutate).toHaveBeenCalledTimes(1);
    const call = forceLogoutMutate.mock.calls[0];
    if (!call) throw new Error("expected mutate call");
    expect(call[0]).toBe(memberRow.id);
  });

  it("V10 — renders NO checkbox column even with the new Actions column (FR5-ADMIN-4 regression guard)", async () => {
    mockHook({
      data: {
        total: 5,
        items: [seedAdminItem, memberRow, agentRow, inactiveMemberRow, ...seedMembers(1)],
        page: 1,
        page_size: 50,
      },
    });
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    expect(screen.queryAllByRole("checkbox").length).toBe(0);
    expect(
      screen.queryAllByRole("button", { name: /bulk|select all/i }).length,
    ).toBe(0);
    expect(document.querySelectorAll('input[type="checkbox"]').length).toBe(0);
  });

  // ---------------------------------------------------------------------------
  // Story 8.4 — V11..V14 admin 2FA override menu items + ConfirmDialog wiring
  // ---------------------------------------------------------------------------

  const enrolledMemberRow: AdminUser = {
    ...memberRow,
    id: "00000000-0000-0000-0000-000000000040",
    email: "enrolled@test.example",
    totp_enabled: true,
  };

  const flaggedMemberRow: AdminUser = {
    ...memberRow,
    id: "00000000-0000-0000-0000-000000000050",
    email: "flagged@test.example",
    force_2fa_enrollment: true,
  };

  it("V11 — shows Force 2FA enrollment item only for non-enrolled non-flagged users", async () => {
    mockHook({
      data: {
        total: 3,
        items: [memberRow, enrolledMemberRow, flaggedMemberRow],
        page: 1,
        page_size: 50,
      },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    // (a) Plain member (totp=false, force=false) — item visible.
    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Force 2FA enrollment")).toBeTruthy();
    });
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByText("Force 2FA enrollment")).toBeNull();
    });

    // (b) Enrolled member (totp=true) — item hidden.
    await user.click(
      screen.getByRole("button", { name: /Actions for enrolled@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Change role")).toBeTruthy();
    });
    expect(screen.queryByText("Force 2FA enrollment")).toBeNull();
    await user.keyboard("{Escape}");

    // (c) Already-flagged member (totp=false, force=true) — item hidden.
    await user.click(
      screen.getByRole("button", { name: /Actions for flagged@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Change role")).toBeTruthy();
    });
    expect(screen.queryByText("Force 2FA enrollment")).toBeNull();
  });

  it("V12 — shows Force-disable 2FA item only for enrolled users", async () => {
    mockHook({
      data: {
        total: 2,
        items: [memberRow, enrolledMemberRow],
        page: 1,
        page_size: 50,
      },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("enrolled@test.example")).toBeTruthy();
    });

    // (a) Enrolled member — item visible.
    await user.click(
      screen.getByRole("button", { name: /Actions for enrolled@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText(/Force-disable 2FA/i)).toBeTruthy();
    });
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByText(/Force-disable 2FA/i)).toBeNull();
    });

    // (b) Non-enrolled member — item hidden.
    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Change role")).toBeTruthy();
    });
    expect(screen.queryByText(/Force-disable 2FA/i)).toBeNull();
  });

  it("V13 — clicking Force 2FA enrollment opens confirm modal then POST on confirm", async () => {
    mockHook({
      data: { total: 1, items: [memberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("member@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for member@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText("Force 2FA enrollment")).toBeTruthy();
    });
    await user.click(screen.getByText("Force 2FA enrollment"));

    await waitFor(() => {
      expect(
        screen.getByText(/Force 2FA enrollment for member@test\.example\?/i),
      ).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: /^Confirm$/i }));

    expect(force2faEnrollmentMutate).toHaveBeenCalledTimes(1);
    const call = force2faEnrollmentMutate.mock.calls[0];
    if (!call) throw new Error("expected mutate call");
    expect(call[0]).toBe(memberRow.id);
  });

  it("V14 — clicking Force-disable 2FA opens confirm modal then POST on confirm", async () => {
    mockHook({
      data: { total: 1, items: [enrolledMemberRow], page: 1, page_size: 50 },
    });
    const user = userEvent.setup();
    mount(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText("enrolled@test.example")).toBeTruthy();
    });

    await user.click(
      screen.getByRole("button", { name: /Actions for enrolled@test\.example/i }),
    );
    await waitFor(() => {
      expect(screen.getByText(/Force-disable 2FA/i)).toBeTruthy();
    });
    await user.click(screen.getByText(/Force-disable 2FA/i));

    await waitFor(() => {
      expect(
        screen.getByText(/Force-disable 2FA for enrolled@test\.example\?/i),
      ).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: /^Confirm$/i }));

    expect(forceDisable2faMutate).toHaveBeenCalledTimes(1);
    const call = forceDisable2faMutate.mock.calls[0];
    if (!call) throw new Error("expected mutate call");
    expect(call[0]).toBe(enrolledMemberRow.id);
  });
});
