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
import { Route as RegisterRoute } from "./register";

const TEST_TOKEN = "test-token-43-chars-AAAAAAAAAAAAAAAAAAAA";

async function renderRegister(node: ReactNode, initialPath: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const registerRoute = createRoute({
    getParentRoute: () => root,
    path: "/register",
    component: () => <>{node}</>,
    validateSearch: (raw: Record<string, unknown>) =>
      typeof raw.token === "string" && raw.token.length > 0 ? { token: raw.token } : {},
  });
  const catalogRoute = createRoute({
    getParentRoute: () => root,
    path: "/catalog",
    component: () => <div>catalog</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([registerRoute, catalogRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  return { rendered: render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  ), router };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const Component = RegisterRoute.options.component as React.ComponentType;

describe("Register form", () => {
  it("renders email + password inputs with proper autoComplete + required attributes", async () => {
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const password = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    expect(email.getAttribute("autocomplete")).toBe("email");
    expect(email.getAttribute("name")).toBe("email");
    expect(email.required).toBe(true);
    expect(password.getAttribute("autocomplete")).toBe("new-password");
    expect(password.getAttribute("name")).toBe("password");
    expect(password.required).toBe(true);
  });

  it("submits the form with token from query string + email + password", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      user: {
        id: "uid",
        email: "newbie@example.com",
        display_name: "newbie",
        role: "member",
      },
    });
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "newbie@example.com" },
    });
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
        "/auth/register",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: TEST_TOKEN,
            email: "newbie@example.com",
            password: "correct horse battery staple",
          }),
        }),
      );
    });
  });

  it("redirects to /catalog on 201 response", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      user: {
        id: "uid",
        email: "newbie@example.com",
        display_name: "newbie",
        role: "member",
      },
    });
    const { router } = await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "newbie@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
  });

  it("surfaces 422 detail string as inline error below password input", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(
        422,
        { detail: "password must be at least 12 characters" },
        "422 Unprocessable",
      ),
    );
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "x@y.z" },
    });
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
    // Form is still visible
    expect(screen.getByLabelText(/password|hasło/i)).toBeDefined();
  });

  it("does not crash and renders fallback message when 422 detail is a FastAPI validation array", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(
        422,
        {
          detail: [
            {
              loc: ["body", "email"],
              msg: "value is not a valid email address",
              type: "value_error.email",
            },
          ],
        },
        "422 Unprocessable",
      ),
    );
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    // Use an HTML5-valid email so jsdom doesn't short-circuit the submit
    // before our mocked API call fires — the regression we care about is
    // server-side validation rejection (array-shaped detail), not client.
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    // Form is still rendered (no crash, no fullPageError)
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password|hasło/i)).toBeDefined();
  });

  it("surfaces 409 email_taken as inline error below email input", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(409, { detail: "email_taken" }, "409 Conflict"),
    );
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "taken@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    // Form still visible
    expect(screen.getByLabelText(/email/i)).toBeDefined();
  });

  it("surfaces 404 token_invalid as full-page error replacing the form", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(404, { detail: "token_invalid" }, "404 Not Found"),
    );
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "x@y.z" },
    });
    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(screen.queryByLabelText(/email/i)).toBeNull();
    });
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("surfaces 410 token_consumed as full-page error replacing the form", async () => {
    vi.mocked(api).mockRejectedValueOnce(
      new ApiError(410, { detail: "token_consumed" }, "410 Gone"),
    );
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "x@y.z" },
    });
    fireEvent.change(screen.getByLabelText(/password|hasło/i), {
      target: { value: "correct horse battery staple" },
    });
    {
      const btn = screen.getAllByRole("button")[0];
      if (btn === undefined) throw new Error("submit button not found");
      fireEvent.click(btn);
    }

    await waitFor(() => {
      expect(screen.queryByLabelText(/email/i)).toBeNull();
    });
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("renders token_missing error state when ?token= query param is absent", async () => {
    await renderRegister(<Component />, "/register");
    // Form is NOT rendered
    expect(screen.queryByLabelText(/email/i)).toBeNull();
    expect(screen.queryByLabelText(/password|hasło/i)).toBeNull();
    // Error message is rendered
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // Story 12.3 — display_name field + email-prefix autopopulate on blur
  // -------------------------------------------------------------------------

  it("renders display_name input with proper a11y attributes", async () => {
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);
    const dn = screen.getByLabelText(
      /display name|nazwa wyświetlana/i,
    ) as HTMLInputElement;
    expect(dn.getAttribute("autocomplete")).toBe("nickname");
    expect(dn.getAttribute("name")).toBe("display_name");
    expect(dn.getAttribute("aria-label")).not.toBeNull();
    expect(dn.getAttribute("aria-describedby")).not.toBeNull();
    expect(dn.getAttribute("maxlength")).toBe("120");
    // NOT required — display_name is optional (server falls back to email prefix)
    expect(dn.required).toBe(false);
  });

  it("autopopulates display_name with email prefix on email blur when empty", async () => {
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const dn = screen.getByLabelText(
      /display name|nazwa wyświetlana/i,
    ) as HTMLInputElement;
    expect(dn.value).toBe("");

    fireEvent.change(email, { target: { value: "foo@example.com" } });
    fireEvent.blur(email);

    await waitFor(() => {
      expect(dn.value).toBe("foo");
    });
  });

  it("does NOT clobber a user-typed display_name on email blur", async () => {
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    const dn = screen.getByLabelText(
      /display name|nazwa wyświetlana/i,
    ) as HTMLInputElement;

    fireEvent.change(dn, { target: { value: "Alice Smith" } });
    fireEvent.change(email, { target: { value: "foo@example.com" } });
    fireEvent.blur(email);

    // The blur autopopulate must respect the touched-state and leave the
    // user-typed value intact.
    expect(dn.value).toBe("Alice Smith");
  });

  it("submits display_name in the request body when populated", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      user: {
        id: "uid",
        email: "newbie@example.com",
        display_name: "Custom Name",
        role: "member",
      },
    });
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "newbie@example.com" },
    });
    fireEvent.change(
      screen.getByLabelText(/display name|nazwa wyświetlana/i),
      { target: { value: "Custom Name" } },
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
        "/auth/register",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: TEST_TOKEN,
            email: "newbie@example.com",
            password: "correct horse battery staple",
            display_name: "Custom Name",
          }),
        }),
      );
    });
  });

  it("omits display_name from the request body when blank", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      user: {
        id: "uid",
        email: "newbie@example.com",
        display_name: "newbie",
        role: "member",
      },
    });
    await renderRegister(<Component />, `/register?token=${TEST_TOKEN}`);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "newbie@example.com" },
    });
    // Do NOT type into display_name and do NOT blur email — body must
    // omit display_name entirely so the backend falls back to email prefix.
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
        "/auth/register",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: TEST_TOKEN,
            email: "newbie@example.com",
            password: "correct horse battery staple",
          }),
        }),
      );
    });
  });
});
