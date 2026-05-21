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
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

// Default mock response: 1 browser session (current) + 1 API session. Tests
// that need different data override `api` per-test before rendering.
const DEFAULT_SESSIONS = {
  items: [
    {
      family_id: "f-1",
      last_used_at: "2026-05-07T10:00:00Z",
      family_issued_at: "2026-05-01T10:00:00Z",
      ip: "1.2.3.4",
      user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130",
      is_current: true,
    },
    {
      family_id: "f-2",
      last_used_at: "2026-05-06T08:00:00Z",
      family_issued_at: "2026-05-02T08:00:00Z",
      ip: "5.6.7.8",
      user_agent: "curl/8.4.0",
      is_current: false,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

const apiMock = vi.fn();
vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
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

async function renderWithRouter(
  node: ReactNode,
  initialEntries: string[] = ["/settings/sessions"],
) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const sessionsRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/sessions",
    component: () => <>{node}</>,
    validateSearch: SessionsRoute.options.validateSearch,
  });
  const loginRoute = createRoute({
    getParentRoute: () => root,
    path: "/login",
    component: () => null,
  });
  const tree = root.addChildren([sessionsRoute, loginRoute]);
  const router = createRouter({
    routeTree: tree,
    history: createMemoryHistory({ initialEntries }),
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
  it("renders the browser session by default and hides the curl session", async () => {
    apiMock.mockResolvedValue(DEFAULT_SESSIONS);
    const Component = SessionsRoute.options.component as React.ComponentType;
    await renderWithRouter(<Component />);
    // Browser session visible (matched on the unique Mozilla/Chrome UA substring).
    expect((await screen.findAllByText(/Chrome\/130/)).length).toBeGreaterThan(0);
    // curl/ session must NOT be visible in default state.
    expect(screen.queryAllByText(/curl\/8\.4\.0/).length).toBe(0);
    // "Current" badge still appears for the browser session (both layouts).
    expect(screen.getAllByText("Current").length).toBeGreaterThan(0);
  });

  it("toggling 'Show API/non-browser sessions' reveals the curl session with a badge", async () => {
    apiMock.mockResolvedValue(DEFAULT_SESSIONS);
    const Component = SessionsRoute.options.component as React.ComponentType;
    await renderWithRouter(<Component />);
    await screen.findAllByText(/Chrome\/130/);
    // Click the filter checkbox (matched by accessible label).
    const checkboxes = screen.getAllByRole("checkbox", {
      name: /Show API \/ non-browser sessions/i,
    });
    expect(checkboxes.length).toBeGreaterThan(0);
    const checkbox = checkboxes[0]!;
    act(() => {
      fireEvent.click(checkbox);
    });
    // After the toggle, the curl session must render with the "API client" badge.
    await waitFor(() => {
      expect(screen.getAllByText(/curl\/8\.4\.0/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("API client").length).toBeGreaterThan(0);
  });

  it("pagination next button passes page=2 to the API and is disabled at the end", async () => {
    // 25 sessions total, page_size=20 → next button should be enabled on page 1
    // and disabled after navigating to page 2.
    const page1 = {
      items: Array.from({ length: 20 }, (_, i) => ({
        family_id: `f-${i + 1}`,
        last_used_at: `2026-05-${String(20 - (i % 20)).padStart(2, "0")}T10:00:00Z`,
        family_issued_at: "2026-05-01T10:00:00Z",
        ip: `10.0.0.${i + 1}`,
        user_agent: `Mozilla/5.0 device-${i + 1}`,
        is_current: i === 0,
      })),
      total: 25,
      page: 1,
      page_size: 20,
    };
    const page2 = {
      items: Array.from({ length: 5 }, (_, i) => ({
        family_id: `f-${21 + i}`,
        last_used_at: `2026-04-${String(25 - i).padStart(2, "0")}T10:00:00Z`,
        family_issued_at: "2026-04-01T10:00:00Z",
        ip: `10.0.1.${i + 1}`,
        user_agent: `Mozilla/5.0 device-${21 + i}`,
        is_current: false,
      })),
      total: 25,
      page: 2,
      page_size: 20,
    };
    apiMock.mockImplementation((url: string) => {
      if (url.includes("page=2")) return Promise.resolve(page2);
      return Promise.resolve(page1);
    });
    const Component = SessionsRoute.options.component as React.ComponentType;
    await renderWithRouter(<Component />);
    await screen.findByText(/Showing 1–20 of 25/);
    const nextButtons = screen.getAllByRole("button", { name: /Next/ });
    const nextBtn = nextButtons[0] as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(false);
    act(() => {
      fireEvent.click(nextBtn);
    });
    // After click, the API must be called with page=2 and the page indicator
    // updates to reflect the second window.
    await waitFor(() => {
      const urls = apiMock.mock.calls.map((c) => String(c[0]));
      expect(urls.some((u) => u.includes("page=2"))).toBe(true);
    });
    await waitFor(() => {
      expect(screen.queryByText(/Showing 21–25 of 25/)).not.toBeNull();
    });
    // Next button must now be disabled (page 2 already at the end).
    const nextAfter = screen.getAllByRole("button", { name: /Next/ });
    expect((nextAfter[0] as HTMLButtonElement).disabled).toBe(true);
  });

  it("page_size selector forwards the value to the API and resets to page 1", async () => {
    apiMock.mockResolvedValue(DEFAULT_SESSIONS);
    const Component = SessionsRoute.options.component as React.ComponentType;
    // Start on page 3 with page_size=20 to verify the reset.
    await renderWithRouter(<Component />, [
      "/settings/sessions?page=3&page_size=20",
    ]);
    await screen.findAllByText(/Chrome\/130/);
    const selects = screen.getAllByRole("combobox");
    const select = selects[0] as HTMLSelectElement;
    act(() => {
      fireEvent.change(select, { target: { value: "10" } });
    });
    await waitFor(() => {
      const urls = apiMock.mock.calls.map((c) => String(c[0]));
      expect(urls.some((u) => u.includes("page_size=10"))).toBe(true);
    });
    // After the size change, requests must use page=1 (or no page param,
    // which the backend treats as page=1). Concretely the last call must
    // NOT carry page=3.
    const lastUrl = String(apiMock.mock.calls.at(-1)?.[0] ?? "");
    expect(lastUrl).not.toContain("page=3");
  });
});
