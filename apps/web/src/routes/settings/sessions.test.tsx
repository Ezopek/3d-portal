import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

vi.mock("@/lib/api", () => ({
  api: vi.fn().mockResolvedValue({
    items: [
      {
        family_id: "f-1",
        last_used_at: "2026-05-07T10:00:00Z",
        family_issued_at: "2026-05-01T10:00:00Z",
        ip: "1.2.3.4",
        user_agent: "Chrome 130 / macOS",
        is_current: true,
      },
      {
        family_id: "f-2",
        last_used_at: "2026-05-06T08:00:00Z",
        family_issued_at: "2026-05-02T08:00:00Z",
        ip: "5.6.7.8",
        user_agent: "Firefox 132 / Windows",
        is_current: false,
      },
    ],
  }),
}));

// Mock AuthContext so AuthGate doesn't redirect to /login
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "u1", email: "test@example.com", display_name: "Test", role: "admin" },
    role: "admin",
    isAdmin: true,
    isMember: false,
    isAdminOrAgent: true,
  }),
}));

import { Route as SessionsRoute } from "./sessions";

afterEach(() => {
  vi.clearAllMocks();
});

async function renderWithRouter(node: ReactNode) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const sessionsRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/sessions",
    component: () => <>{node}</>,
  });
  const loginRoute = createRoute({
    getParentRoute: () => root,
    path: "/login",
    component: () => null,
  });
  const tree = root.addChildren([sessionsRoute, loginRoute]);
  const router = createRouter({
    routeTree: tree,
    history: createMemoryHistory({ initialEntries: ["/settings/sessions"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("Sessions route", () => {
  it("renders both sessions with current badge", async () => {
    // Extract the component from the TanStack Router file route
    const Component = SessionsRoute.options.component as React.ComponentType;
    await renderWithRouter(<Component />);
    // Both desktop table and mobile cards render the same sessions (CSS hides one)
    expect((await screen.findAllByText(/Chrome 130/)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Firefox 132/)).length).toBeGreaterThan(0);
    // The "Current" badge appears in both table and mobile card for the current session
    expect(screen.getAllByText("Current").length).toBeGreaterThan(0);
  });
});
