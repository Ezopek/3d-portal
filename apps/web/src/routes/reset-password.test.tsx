import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: vi.fn(),
  };
});

import { ApiError, api } from "@/lib/api";
import { Route as ResetPasswordRoute } from "./reset-password";

const TEST_TOKEN = "test-token-43-chars-AAAAAAAAAAAAAAAAAAAA";

async function renderResetPassword(node: ReactNode, initialPath: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const resetRoute = createRoute({
    getParentRoute: () => root,
    path: "/reset-password",
    component: () => <>{node}</>,
    validateSearch: (raw: Record<string, unknown>) =>
      typeof raw.token === "string" && raw.token.length > 0
        ? { token: raw.token }
        : {},
  });
  const loginRoute = createRoute({
    getParentRoute: () => root,
    path: "/login",
    component: () => <div>login</div>,
    validateSearch: (raw: Record<string, unknown>) =>
      raw.reset === "success" ? { reset: "success" as const } : {},
  });
  const router = createRouter({
    routeTree: root.addChildren([resetRoute, loginRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  return {
    rendered: render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
    router,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const Component = ResetPasswordRoute.options.component as React.ComponentType;

describe("ResetPassword form", () => {
  it("R1 — golden path: submits new password and navigates to /login?reset=success", async () => {
    vi.mocked(api).mockResolvedValueOnce(undefined);
    const { router } = await renderResetPassword(
      <Component />,
      `/reset-password?token=${TEST_TOKEN}`,
    );

    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(vi.mocked(api)).toHaveBeenCalledWith(
        "/auth/password-reset",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: TEST_TOKEN,
            new_password: "correct horse battery staple",
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
      expect(router.state.location.search).toEqual({ reset: "success" });
    });
  });

  it("R2 — 404 token_invalid renders full-page error panel", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(404, { detail: "token_invalid" }, "404 Not Found"),
    );
    await renderResetPassword(<Component />, `/reset-password?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(screen.queryByLabelText(/password|hasło/i)).toBeNull();
    });
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("R3 — 422 weak-password renders inline error below the password input", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(
        422,
        { detail: "password must be at least 12 characters" },
        "422 Unprocessable",
      ),
    );
    await renderResetPassword(<Component />, `/reset-password?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "abc12" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(
        screen.getByText("password must be at least 12 characters"),
      ).toBeDefined();
    });
    // Form remains visible.
    expect(screen.getByLabelText(/password|hasło/i)).toBeDefined();
  });
});
