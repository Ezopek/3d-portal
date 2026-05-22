import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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

import { api } from "@/lib/api";
import i18n from "@/locales/i18n";
import { AuthProvider } from "@/shell/AuthContext";
import { Route as HubRoute } from "./index";

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
  display_name: "Member",
  role: "member",
};

function mount(initialPath = "/settings") {
  const root = createRootRoute();
  // The hub route + three placeholder sibling routes, so the Link `to`
  // resolves and href is generated without a "could not resolve" warning.
  const hubRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/",
    component: HubRoute.options.component,
  });
  const profileRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/profile",
    component: () => <div>profile placeholder</div>,
  });
  const twofaRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/2fa",
    component: () => <div>2fa placeholder</div>,
  });
  const sessionsRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/sessions",
    component: () => <div>sessions placeholder</div>,
  });
  const shareLinksRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/share-links",
    component: () => <div>share-links placeholder</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([
      hubRoute,
      profileRoute,
      twofaRoute,
      sessionsRoute,
      shareLinksRoute,
    ]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
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

describe("Settings — hub landing", () => {
  it("renders four cards (Profile, 2FA, Sessions, My share links) for authenticated users", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    // h1 with hub title
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: /settings/i }),
      ).toBeTruthy();
    });

    // Three card titles — match against EN i18n strings. We scope to
    // CardTitle elements (data-slot="card-title") so the description copy
    // (which may legitimately echo the title) doesn't double-match.
    const titles = document.querySelectorAll('[data-slot="card-title"]');
    const titleTexts = Array.from(titles).map((el) => el.textContent?.trim() ?? "");
    expect(titleTexts).toEqual([
      "Profile",
      "Two-factor authentication",
      "Active sessions",
      "My share links",
    ]);

    // Each card has an associated description (paired with title).
    expect(screen.getByText(/Edit your display name/i)).toBeTruthy();
    expect(
      screen.getByText(/Add a one-time code from an authenticator app/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/Review devices currently signed in/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/List and revoke share links you've generated/i),
    ).toBeTruthy();
  });

  it("each card is a keyboard-reachable link routing to its sibling settings page", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: /settings/i }),
      ).toBeTruthy();
    });

    // Three navigation links — TanStack <Link> renders an <a> with href.
    const links = screen.getAllByRole("link");
    const hrefs = links.map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/settings/profile");
    expect(hrefs).toContain("/settings/2fa");
    expect(hrefs).toContain("/settings/sessions");

    // Anchor elements are keyboard-reachable by default (tabIndex 0); confirm
    // we did NOT regress them to tabIndex=-1 via a stray class/prop override.
    for (const a of links.filter((el) =>
      ["/settings/profile", "/settings/2fa", "/settings/sessions"].includes(
        el.getAttribute("href") ?? "",
      ),
    )) {
      // tabIndex is a property — anchors default to 0; an explicit
      // tabIndex=-1 would surface here as the property value -1.
      expect((a as HTMLAnchorElement).tabIndex).not.toBe(-1);
    }
  });

  it("renders the hub inside a single <nav> landmark labelled with the hub title (a11y)", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/me") return ME_RESPONSE;
      throw new Error(`unexpected call: ${path}`);
    });
    mount();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: /settings/i }),
      ).toBeTruthy();
    });

    const nav = screen.getByRole("navigation", { name: /settings/i });
    expect(nav).toBeTruthy();
    // The nav contains the four sibling links (Story 16.3 added share-links);
    // no stray external links inside.
    const navLinks = nav.querySelectorAll("a");
    expect(navLinks.length).toBe(4);
  });
});
