import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthContext";

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

// vi.mock is hoisted above imports, so the spy must be hoisted too via
// vi.hoisted — otherwise it would be in the temporal dead zone when the
// factory runs.
const { sentrySetTagSpy } = vi.hoisted(() => ({ sentrySetTagSpy: vi.fn() }));
vi.mock("@sentry/react", () => ({
  setTag: sentrySetTagSpy,
}));

import { api } from "@/lib/api";

function Probe() {
  const a = useAuth();
  return (
    <>
      <span data-testid="loading">{String(a.isLoading)}</span>
      <span data-testid="auth">{String(a.isAuthenticated)}</span>
      <span data-testid="admin">{String(a.isAdmin)}</span>
      <span data-testid="member">{String(a.isMember)}</span>
      <span data-testid="adminOrAgent">{String(a.isAdminOrAgent)}</span>
      <span data-testid="email">{a.user?.email ?? ""}</span>
      <span data-testid="role">{a.role ?? "none"}</span>
    </>
  );
}

function wrap(children: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

afterEach(() => {
  cleanup();
  sentrySetTagSpy.mockReset();
});

describe("AuthContext (cookie-based)", () => {
  it("starts in loading state", () => {
    (api as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    render(wrap(<Probe />));
    expect(screen.getByTestId("loading").textContent).toBe("true");
    expect(screen.getByTestId("auth").textContent).toBe("false");
  });

  it("resolves to authenticated admin", async () => {
    (api as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u-1",
      email: "a@example.com",
      display_name: "Admin",
      role: "admin",
    });
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("auth").textContent).toBe("true");
      expect(screen.getByTestId("admin").textContent).toBe("true");
      expect(screen.getByTestId("adminOrAgent").textContent).toBe("true");
      expect(screen.getByTestId("email").textContent).toBe("a@example.com");
      expect(screen.getByTestId("role").textContent).toBe("admin");
    });
  });

  it("resolves to authenticated member", async () => {
    (api as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u-2",
      email: "m@example.com",
      display_name: "Member",
      role: "member",
    });
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("auth").textContent).toBe("true");
      expect(screen.getByTestId("admin").textContent).toBe("false");
      expect(screen.getByTestId("member").textContent).toBe("true");
      expect(screen.getByTestId("adminOrAgent").textContent).toBe("false");
      expect(screen.getByTestId("role").textContent).toBe("member");
    });
  });

  it("resolves to authenticated agent", async () => {
    (api as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u-3",
      email: "ag@example.com",
      display_name: "Agent",
      role: "agent",
    });
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("auth").textContent).toBe("true");
      expect(screen.getByTestId("admin").textContent).toBe("false");
      expect(screen.getByTestId("member").textContent).toBe("false");
      expect(screen.getByTestId("adminOrAgent").textContent).toBe("true");
      expect(screen.getByTestId("role").textContent).toBe("agent");
    });
  });

  it("resolves to anonymous on 401", async () => {
    (api as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("401"));
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("auth").textContent).toBe("false");
      expect(screen.getByTestId("admin").textContent).toBe("false");
    });
  });

  // Story 2.3 review fix (Codex P2 finding): the auth tag is mirrored to
  // Sentry's active scope eagerly on every auth-state change so it does not
  // go stale between router onLoad events.
  it("emits Sentry.setTag('auth.is_authenticated', 'true') when /auth/me resolves authenticated", async () => {
    (api as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u-1",
      email: "a@example.com",
      display_name: "Admin",
      role: "admin",
    });
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(sentrySetTagSpy).toHaveBeenCalledWith("auth.is_authenticated", "true");
    });
  });

  it("emits Sentry.setTag('auth.is_authenticated', 'false') when /auth/me rejects (401)", async () => {
    (api as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("401"));
    render(wrap(<Probe />));
    await waitFor(() => {
      expect(sentrySetTagSpy).toHaveBeenCalledWith("auth.is_authenticated", "false");
    });
  });
});
