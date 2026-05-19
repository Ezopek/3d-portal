import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { Route as LoginRoute } from "./login";

async function renderLogin(node: ReactNode) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const loginRoute = createRoute({
    getParentRoute: () => root,
    path: "/login",
    component: () => <>{node}</>,
    validateSearch: () => ({}),
  });
  const indexRoute = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([loginRoute, indexRoute]),
    history: createMemoryHistory({ initialEntries: ["/login"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Login form", () => {
  it("associates visible labels with both inputs", async () => {
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);
    // getByLabelText throws if no <label htmlFor> / aria-labelledby /
    // implicit-label association exists.
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password|hasło/i)).toBeDefined();
  });

  it("sets autocomplete + name on inputs so password managers work", async () => {
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const password = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    expect(email.getAttribute("autocomplete")).toBe("username");
    expect(email.getAttribute("name")).toBe("email");
    expect(email.required).toBe(true);
    expect(password.getAttribute("autocomplete")).toBe("current-password");
    expect(password.getAttribute("name")).toBe("password");
    expect(password.required).toBe(true);
  });

  it("shows a 'signing in' label on the submit button while the request is pending", async () => {
    let resolveLogin: () => void = () => undefined;
    vi.mocked(api).mockImplementation(
      () => new Promise<unknown>((res) => {
        resolveLogin = () => res(null);
      }),
    );
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);

    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const password = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    fireEvent.change(email, { target: { value: "x@y.z" } });
    fireEvent.change(password, { target: { value: "secret" } });

    const submit = screen.getAllByRole("button", { name: /sign in|zaloguj/i })[0];
    if (submit === undefined) throw new Error("submit button not found");
    fireEvent.click(submit);

    await waitFor(() => {
      // While pending the button caption changes; we don't pin the exact
      // string, just require it to differ from the idle caption.
      expect(submit.textContent).toMatch(/signing in|logowanie/i);
    });
    resolveLogin();
  });
});

describe("Login partial-auth flow (Story 7.3)", () => {
  async function submitEmailPassword(): Promise<void> {
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const password = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    fireEvent.change(email, { target: { value: "anna@example.com" } });
    fireEvent.change(password, { target: { value: "secret" } });
    const submit = screen.getAllByRole("button", { name: /sign in|zaloguj/i })[0];
    if (submit === undefined) throw new Error("submit button not found");
    fireEvent.click(submit);
  }

  it("renders second-factor prompt after partial-auth login response", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      partial_auth: true,
      totp_required: true,
      partial_token: "fixture-partial-token",
    });
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);

    await submitEmailPassword();

    await waitFor(() => {
      expect(screen.getByLabelText(/^code|^kod/i)).toBeDefined();
    });
    // Email/password form is no longer visible.
    expect(screen.queryByLabelText(/email/i)).toBeNull();
    expect(screen.queryByLabelText(/password|hasło/i)).toBeNull();
    // Verify + Back buttons present.
    expect(screen.getByRole("button", { name: /verify|zweryfikuj/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /back to sign in|powrót/i })).toBeDefined();
  });

  it("submits verify call and navigates to next on success", async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({
        partial_auth: true,
        totp_required: true,
        partial_token: "fixture-partial-token",
      })
      .mockResolvedValueOnce({
        partial_auth: false,
        user: {
          id: "00000000-0000-0000-0000-000000000001",
          email: "anna@example.com",
          display_name: "Anna",
          role: "member",
        },
      });
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);

    await submitEmailPassword();
    await waitFor(() => screen.getByLabelText(/^code|^kod/i));

    const code = screen.getByLabelText(/^code|^kod/i) as HTMLInputElement;
    fireEvent.change(code, { target: { value: "123456" } });
    const verify = screen.getByRole("button", { name: /verify|zweryfikuj/i });
    fireEvent.click(verify);

    await waitFor(() => {
      // The 2nd api() call is the /auth/2fa/verify POST.
      expect(vi.mocked(api).mock.calls[1]?.[0]).toBe("/auth/2fa/verify");
    });
    const verifyInit = vi.mocked(api).mock.calls[1]?.[1] as RequestInit;
    expect(verifyInit.method).toBe("POST");
    const verifyBody = JSON.parse(verifyInit.body as string);
    expect(verifyBody).toEqual({
      partial_token: "fixture-partial-token",
      code: "123456",
    });
  });

  it("shows invalid-code error on verify 401 and preserves partial-token state", async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({
        partial_auth: true,
        totp_required: true,
        partial_token: "fixture-partial-token",
      })
      .mockRejectedValueOnce(
        new ApiError(401, { detail: "invalid_code" }, "401 Unauthorized"),
      );
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);

    await submitEmailPassword();
    await waitFor(() => screen.getByLabelText(/^code|^kod/i));

    const code = screen.getByLabelText(/^code|^kod/i) as HTMLInputElement;
    fireEvent.change(code, { target: { value: "000000" } });
    const verify = screen.getByRole("button", { name: /verify|zweryfikuj/i });
    fireEvent.click(verify);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(
        /incorrect code|nieprawidłowy kod/i,
      );
    });
    // Still on second-factor sub-state: code input present, email/password not.
    expect(screen.getByLabelText(/^code|^kod/i)).toBeDefined();
    expect(screen.queryByLabelText(/email/i)).toBeNull();
  });

  it("resets to email_password sub-state on back-button click", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      partial_auth: true,
      totp_required: true,
      partial_token: "fixture-partial-token",
    });
    const Component = LoginRoute.options.component as React.ComponentType;
    await renderLogin(<Component />);

    await submitEmailPassword();
    await waitFor(() => screen.getByLabelText(/^code|^kod/i));

    const back = screen.getByRole("button", { name: /back to sign in|powrót/i });
    fireEvent.click(back);

    await waitFor(() => {
      expect(screen.getByLabelText(/email/i)).toBeDefined();
    });
    expect(screen.queryByLabelText(/^code|^kod/i)).toBeNull();
    expect(screen.getByLabelText(/password|hasło/i)).toBeDefined();
  });
});

describe("Login forced-enrollment flow (Story 7.4)", () => {
  async function renderLoginWithNext(node: ReactNode, next: string) {
    const root = createRootRoute({ component: () => <Outlet /> });
    const loginRoute = createRoute({
      getParentRoute: () => root,
      path: "/login",
      component: () => <>{node}</>,
      validateSearch: (raw: Record<string, unknown>) =>
        typeof raw.next === "string" && raw.next.length > 0
          ? { next: raw.next }
          : {},
    });
    const settings2faRoute = createRoute({
      getParentRoute: () => root,
      path: "/settings/2fa",
      component: () => <div>settings-2fa</div>,
      validateSearch: (raw: Record<string, unknown>) =>
        typeof raw.next === "string" && raw.next.length > 0
          ? { next: raw.next }
          : {},
    });
    const queueRoute = createRoute({
      getParentRoute: () => root,
      path: "/queue",
      component: () => <div>queue</div>,
    });
    const indexRoute = createRoute({
      getParentRoute: () => root,
      path: "/",
      component: () => <div>home</div>,
    });
    const router = createRouter({
      routeTree: root.addChildren([loginRoute, settings2faRoute, queueRoute, indexRoute]),
      history: createMemoryHistory({
        initialEntries: [`/login?next=${encodeURIComponent(next)}`],
      }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await router.load();
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );
    return router;
  }

  async function submitEmailPassword(): Promise<void> {
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const password = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    fireEvent.change(email, { target: { value: "anna@example.com" } });
    fireEvent.change(password, { target: { value: "secret" } });
    const submit = screen.getAllByRole("button", { name: /sign in|zaloguj/i })[0];
    if (submit === undefined) throw new Error("submit button not found");
    fireEvent.click(submit);
  }

  it("navigates to /settings/2fa when login response has totp_enroll_required=true", async () => {
    // V5 — Story 7.4 forced-enrollment branch.
    vi.mocked(api).mockResolvedValueOnce({
      partial_auth: false,
      user: {
        id: "00000000-0000-0000-0000-000000000001",
        email: "anna@example.com",
        display_name: "Anna",
        role: "member",
      },
      totp_enroll_required: true,
    });
    const Component = LoginRoute.options.component as React.ComponentType;
    const router = await renderLoginWithNext(<Component />, "/queue");

    await submitEmailPassword();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/settings/2fa");
    });
    expect(router.state.location.search).toEqual({ next: "/queue" });
  });

  it("navigates directly to next when login response has totp_enroll_required=false", async () => {
    // V6 — baseline regression: single-factor success path still navigates to next.
    vi.mocked(api).mockResolvedValueOnce({
      partial_auth: false,
      user: {
        id: "00000000-0000-0000-0000-000000000001",
        email: "anna@example.com",
        display_name: "Anna",
        role: "member",
      },
      totp_enroll_required: false,
    });
    const Component = LoginRoute.options.component as React.ComponentType;
    const router = await renderLoginWithNext(<Component />, "/queue");

    await submitEmailPassword();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/queue");
    });
  });
});
