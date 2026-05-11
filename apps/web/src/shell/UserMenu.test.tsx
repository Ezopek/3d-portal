import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { AuthProvider } from "@/shell/AuthContext";
import { UserMenu } from "@/shell/UserMenu";

// Per project-context.md, intercept at fetch level (not at the `api()`
// wrapper). This keeps CSRF + 401-retry plumbing in the path under test;
// mocking `api()` would silently mask regressions in either layer.
vi.mock("@sentry/react", () => ({ setTag: vi.fn() }));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

beforeAll(async () => {
  // Pin EN for deterministic regex matches against menu item text.
  await i18n.changeLanguage("en");
});

function makeJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mount() {
  const rootRoute = createRootRoute({ component: () => <UserMenu /> });
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Tree({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    );
  }
  return render(
    <Tree>
      <RouterProvider router={router} />
    </Tree>,
  );
}

function stubAuthMe(user: { id: string; email: string; display_name: string; role: string }) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url.endsWith("/api/auth/me")) {
      return makeJsonResponse(user);
    }
    // Any other call falls through to a stub 204 — keeps the test deterministic
    // without modeling every backend route.
    return new Response(null, { status: 204 });
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("UserMenu — TB-006 admin agents entry", () => {
  it("does NOT show the agents entry for non-admin (member) users", async () => {
    stubAuthMe({ id: "u-1", email: "m@example.com", display_name: "Member", role: "member" });
    mount();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /member/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /member/i }));
    expect(screen.queryByText(/for agents|dla agentów/i)).toBeNull();
  });

  it("shows the agents entry for admin users and opens the dialog on click", async () => {
    stubAuthMe({ id: "u-2", email: "a@example.com", display_name: "Admin", role: "admin" });
    mount();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /admin/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /admin/i }));

    const menuItem = await screen.findByText(/for agents|dla agentów/i);
    expect(menuItem).toBeTruthy();
    fireEvent.click(menuItem);

    await waitFor(() => {
      expect(screen.getByText(/agent onboarding|onboarding agenta/i)).toBeTruthy();
    });
    expect(screen.getByText(/curl -fsS https:\/\/3d\.ezop\.ddns\.net\/agent-runbook/)).toBeTruthy();
    expect(
      screen.getByText(/curl -fsS https:\/\/3d\.ezop\.ddns\.net\/api\/openapi\.json/),
    ).toBeTruthy();
    expect(screen.getByText("~/.config/3d-portal/agent.token")).toBeTruthy();
  });

  it("copies the runbook command to clipboard and emits a success toast", async () => {
    stubAuthMe({ id: "u-3", email: "a@example.com", display_name: "Admin", role: "admin" });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    mount();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /admin/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /admin/i }));
    fireEvent.click(await screen.findByText(/for agents|dla agentów/i));
    await waitFor(() => {
      expect(screen.getByText(/agent onboarding|onboarding agenta/i)).toBeTruthy();
    });

    // The first copy button is now aria-labeled per-block; match the
    // runbook-specific aria-label rather than generic "Copy".
    const runbookCopy = screen.getByRole("button", { name: /copy fetch-runbook command/i });
    fireEvent.click(runbookCopy);

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        expect.stringContaining("curl -fsS https://3d.ezop.ddns.net/agent-runbook"),
      );
    });
    const sonner = (await import("sonner")) as unknown as {
      toast: { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> };
    };
    expect(sonner.toast.success).toHaveBeenCalled();
  });
});
