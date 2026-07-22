import "@/locales/i18n";

import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The auth-gate is the entire behaviour under test, so useAuth is the single
// mocked seam. TagGroupsPage is stubbed with a render spy: the route only mounts
// it for authenticated admins, so the spy doubles as the "did the tag-groups
// data surface render / would it have fetched" probe for the non-admin cases.
const tagGroupsRenderSpy = vi.fn();

vi.mock("@/shell/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/modules/admin/TagGroupsPage", () => ({
  TagGroupsPage: () => {
    tagGroupsRenderSpy();
    return <div data-testid="tag-groups-page">tag groups page</div>;
  },
}));

import { useAuth } from "@/shell/AuthContext";
import { Route as TagGroupsRoute } from "./tag-groups";

// AuthState is not exported from AuthContext; derive it from useAuth's return.
type AuthState = ReturnType<typeof useAuth>;

const ADMIN_ID = "00000000-0000-0000-0000-000000000001";

function authState(overrides: Partial<AuthState>): AuthState {
  return {
    user: null,
    role: null,
    isAdmin: false,
    isMember: false,
    isAdminOrAgent: false,
    isAuthenticated: false,
    isLoading: false,
    ...overrides,
  };
}

// Mounts the real route component with a "/" fallback so the non-admin
// <Navigate to="/" replace /> redirect resolves to a concrete landing route.
function mount(initialPath = "/admin/tag-groups") {
  const root = createRootRoute();
  const tagGroupsRoute = createRoute({
    getParentRoute: () => root,
    path: "/admin/tag-groups",
    component: TagGroupsRoute.options.component,
  });
  const homeRoute = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div data-testid="home">home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([tagGroupsRoute, homeRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
  return render(<RouterProvider router={router} />);
}

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  tagGroupsRenderSpy.mockReset();
});

describe("/admin/tag-groups route — auth gate (Story 46.1 repair)", () => {
  it("renders nothing while auth is loading (unknown auth → null, no fetch)", async () => {
    vi.mocked(useAuth).mockReturnValue(authState({ isLoading: true }));
    const { container } = mount();

    // Loading resolves to null: no page, no redirect, no tag-groups data.
    await waitFor(() => {
      expect(screen.queryByTestId("tag-groups-page")).toBeNull();
    });
    expect(screen.queryByTestId("home")).toBeNull();
    expect(container.querySelector("[data-testid]")).toBeNull();
    expect(tagGroupsRenderSpy).not.toHaveBeenCalled();
  });

  it("renders null for unauthenticated users, deferring to the shell AuthGate", async () => {
    // The route returns null (not a redirect) for anonymous users so AppShell's
    // AuthGate handles the /login?next= redirect and preserves the pathname.
    vi.mocked(useAuth).mockReturnValue(
      authState({ isAuthenticated: false, isAdmin: false }),
    );
    const { container } = mount();

    await waitFor(() => {
      expect(screen.queryByTestId("tag-groups-page")).toBeNull();
    });
    // No client-side redirect to "/" — that path is reserved for the non-admin
    // (member-authenticated) tier, not anonymous users.
    expect(screen.queryByTestId("home")).toBeNull();
    expect(container.querySelector("[data-testid]")).toBeNull();
    expect(tagGroupsRenderSpy).not.toHaveBeenCalled();
  });

  it("redirects an authenticated non-admin to / without fetching tag-groups", async () => {
    vi.mocked(useAuth).mockReturnValue(
      authState({
        user: {
          id: "u-member",
          email: "member@example.com",
          display_name: "Member",
          role: "member",
        },
        role: "member",
        isMember: true,
        isAuthenticated: true,
        isAdmin: false,
      }),
    );
    mount();

    // Member-authenticated non-admin is bounced to the home landing route.
    await waitFor(() => {
      expect(screen.getByTestId("home")).toBeTruthy();
    });
    // The tag-groups page (and thus its data fetch) never mounts.
    expect(screen.queryByTestId("tag-groups-page")).toBeNull();
    expect(tagGroupsRenderSpy).not.toHaveBeenCalled();
  });

  it("renders TagGroupsPage for an authenticated admin", async () => {
    vi.mocked(useAuth).mockReturnValue(
      authState({
        user: {
          id: ADMIN_ID,
          email: "admin@example.com",
          display_name: "Admin",
          role: "admin",
        },
        role: "admin",
        isAdmin: true,
        isAdminOrAgent: true,
        isAuthenticated: true,
      }),
    );
    mount();

    await waitFor(() => {
      expect(screen.getByTestId("tag-groups-page")).toBeTruthy();
    });
    expect(screen.queryByTestId("home")).toBeNull();
    expect(tagGroupsRenderSpy).toHaveBeenCalled();
  });
});
