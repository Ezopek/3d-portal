import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    body?: unknown;
    constructor(status: number, body?: unknown, message?: string) {
      super(message);
      this.status = status;
      this.body = body;
    }
  },
  api: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { ApiError, api } from "@/lib/api";
import i18n from "@/locales/i18n";
import { AuthProvider } from "@/shell/AuthContext";
import { toast } from "sonner";
import { Route as ProfileRoute } from "./profile";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const ME_RESPONSE = {
  id: "u-1",
  email: "member@example.com",
  display_name: "legacy_local_part",
  role: "member",
};

function mount() {
  const root = createRootRoute();
  const profileRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/profile",
    component: ProfileRoute.options.component,
  });
  const router = createRouter({
    routeTree: root.addChildren([profileRoute]),
    history: createMemoryHistory({ initialEntries: ["/settings/profile"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Settings — Profile page", () => {
  it("prepopulates the display_name input from the authenticated /me response", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    const input = (await screen.findByLabelText(
      /display name/i,
    )) as HTMLInputElement;
    expect(input.value).toBe("legacy_local_part");

    // Email field is shown read-only
    const emailField = screen.getByLabelText(/email/i) as HTMLInputElement;
    expect(emailField.value).toBe("member@example.com");
    expect(emailField.disabled).toBe(true);
  });

  it("submits PATCH /auth/me/display-name with the trimmed new value and toasts on success", async () => {
    vi.mocked(api).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/auth/me") return ME_RESPONSE;
      if (path === "/auth/me/display-name") {
        expect(init?.method).toBe("PATCH");
        expect(init?.body).toBe(
          JSON.stringify({ display_name: "Foo Bar" }),
        );
        return { ...ME_RESPONSE, display_name: "Foo Bar" };
      }
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    const input = (await screen.findByLabelText(
      /display name/i,
    )) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "  Foo Bar  " } });

    const btn = screen.getByRole("button", { name: /save/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringMatching(/display name saved/i),
      );
    });
    expect(vi.mocked(api)).toHaveBeenCalledWith(
      "/auth/me/display-name",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("renders 422 backend rejection as an inline error and does NOT toast success", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      if (path === "/auth/me/display-name") {
        throw new ApiError(
          422,
          { detail: "display_name must not be blank" },
          "422 Unprocessable",
        );
      }
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    const input = (await screen.findByLabelText(
      /display name/i,
    )) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "something-the-backend-rejects" } });

    const btn = screen.getByRole("button", { name: /save/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("disables the submit button while the value is unchanged or blank", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    await screen.findByLabelText(/display name/i);
    const btn = screen.getByRole("button", { name: /save/i }) as HTMLButtonElement;
    // Initial: value === current display_name → disabled
    expect(btn.disabled).toBe(true);

    const input = screen.getByLabelText(/display name/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "" } });
    // Blank → still disabled
    expect(btn.disabled).toBe(true);

    fireEvent.change(input, { target: { value: "Foo" } });
    // Changed + non-blank → enabled
    expect(btn.disabled).toBe(false);
  });
});
