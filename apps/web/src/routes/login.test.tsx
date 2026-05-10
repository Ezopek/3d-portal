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

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

import { api } from "@/lib/api";
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
