import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthContext";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  const body = btoa(JSON.stringify(payload))
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  return `${header}.${body}.sig`;
}

function setToken(payload: Record<string, unknown>): void {
  localStorage.setItem("portal.token", makeJwt(payload));
  localStorage.setItem("portal.token.exp", String(Date.now() + 30 * 60 * 1000));
}

function Wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="role">{auth.role ?? "none"}</span>
      <span data-testid="isAdmin">{String(auth.isAdmin)}</span>
      <span data-testid="isMember">{String(auth.isMember)}</span>
      <span data-testid="isAdminOrAgent">{String(auth.isAdminOrAgent)}</span>
      <span data-testid="isAuthenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="isLoading">{String(auth.isLoading)}</span>
      <span data-testid="email">{auth.user?.email ?? "none"}</span>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  fetchMock.mockReset();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("AuthContext", () => {
  it("anonymous when no token present", () => {
    render(<Probe />, { wrapper: Wrapper });
    expect(screen.getByTestId("role").textContent).toBe("none");
    expect(screen.getByTestId("isAdmin").textContent).toBe("false");
    expect(screen.getByTestId("isAuthenticated").textContent).toBe("false");
    expect(screen.getByTestId("isLoading").textContent).toBe("false");
  });

  it("admin token: synchronous role + isAdmin gates from JWT", async () => {
    setToken({ sub: "00000000-0000-0000-0000-000000000001", role: "admin" });
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000001",
          email: "admin@portal.example.com",
          display_name: "Admin",
          role: "admin",
        }),
        { status: 200 },
      ),
    );
    render(<Probe />, { wrapper: Wrapper });
    expect(screen.getByTestId("role").textContent).toBe("admin");
    expect(screen.getByTestId("isAdmin").textContent).toBe("true");
    expect(screen.getByTestId("isAdminOrAgent").textContent).toBe("true");
    expect(screen.getByTestId("isAuthenticated").textContent).toBe("true");
    await waitFor(() =>
      expect(screen.getByTestId("email").textContent).toBe("admin@portal.example.com"),
    );
  });

  it("member token: isAdmin false, isMember true", async () => {
    setToken({ sub: "00000000-0000-0000-0000-000000000002", role: "member" });
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000002",
          email: "member@portal.example.com",
          display_name: "Member",
          role: "member",
        }),
        { status: 200 },
      ),
    );
    render(<Probe />, { wrapper: Wrapper });
    expect(screen.getByTestId("role").textContent).toBe("member");
    expect(screen.getByTestId("isAdmin").textContent).toBe("false");
    expect(screen.getByTestId("isMember").textContent).toBe("true");
    expect(screen.getByTestId("isAdminOrAgent").textContent).toBe("false");
    expect(screen.getByTestId("isAuthenticated").textContent).toBe("true");
  });

  it("agent token: isAdmin false, isAdminOrAgent true", () => {
    setToken({ sub: "00000000-0000-0000-0000-000000000003", role: "agent" });
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000003",
          email: "agent@portal.example.com",
          display_name: "Agent",
          role: "agent",
        }),
        { status: 200 },
      ),
    );
    render(<Probe />, { wrapper: Wrapper });
    expect(screen.getByTestId("role").textContent).toBe("agent");
    expect(screen.getByTestId("isAdmin").textContent).toBe("false");
    expect(screen.getByTestId("isMember").textContent).toBe("false");
    expect(screen.getByTestId("isAdminOrAgent").textContent).toBe("true");
  });

  it("clears token and renders anonymous when /me responds 401", async () => {
    setToken({ sub: "00000000-0000-0000-0000-000000000004", role: "admin" });
    fetchMock.mockResolvedValueOnce(new Response("", { status: 401 }));
    render(<Probe />, { wrapper: Wrapper });
    // Initially synchronous gates show admin (token present)
    expect(screen.getByTestId("role").textContent).toBe("admin");
    // After /me 401 returns, token is cleared
    await waitFor(() => {
      expect(localStorage.getItem("portal.token")).toBeNull();
    });
  });

  it("calls GET /api/auth/me with cookies and X-Portal-Client header", async () => {
    setToken({ sub: "00000000-0000-0000-0000-000000000005", role: "admin" });
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "00000000-0000-0000-0000-000000000005",
          email: "x@y.z",
          display_name: "X",
          role: "admin",
        }),
        { status: 200 },
      ),
    );
    render(<Probe />, { wrapper: Wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/auth/me");
    expect((init as RequestInit).credentials).toBe("include");
    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get("X-Portal-Client")).toBe("web");
  });

  it("does not call /me when no token is present", async () => {
    render(<Probe />, { wrapper: Wrapper });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
