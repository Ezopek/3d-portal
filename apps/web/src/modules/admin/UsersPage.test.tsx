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
import type { ReactNode } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import type {
  AdminUser,
  AdminUsersListResponse,
} from "@/lib/api-types";
import i18n from "@/locales/i18n";

vi.mock("@/modules/admin/hooks/useAdminUsers", () => ({
  useAdminUsers: vi.fn(),
}));

import { useAdminUsers } from "@/modules/admin/hooks/useAdminUsers";
import { UsersPage } from "@/modules/admin/UsersPage";

beforeAll(async () => {
  await i18n.changeLanguage("en");
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
});
