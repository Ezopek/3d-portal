// Initiative 18 Story 30.2 — ShareMemberContextInfoBar unit tests.
//
// IB-1: renders banner + action + dismiss button on first mount.
// IB-2: clicking dismiss hides the info-bar.
// IB-3: dismissing modelId A does not silence a different modelId B.
// IB-4: sessionStorage pre-seed renders nothing on mount.
//
// Per [[feedback_vitest_manual_cleanup]] global vitest.setup.ts auto-
// registers afterEach(cleanup); no per-file boilerplate needed beyond
// sessionStorage cleanup which is test-state, not DOM-state.

import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import "@/locales/i18n";

import { ShareMemberContextInfoBar } from "./ShareMemberContextInfoBar";

function renderWithRouter(node: React.ReactNode) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <>{node}</>,
  });
  const catalogRoute = createRoute({
    getParentRoute: () => root,
    path: "/catalog/$id",
    component: () => <div>catalog-page</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([indexRoute, catalogRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(<RouterProvider router={router} />);
  return router;
}

describe("Story 30.2 — ShareMemberContextInfoBar", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("IB-1: renders banner + action link + dismiss button on first mount", async () => {
    renderWithRouter(<ShareMemberContextInfoBar modelId="m1" />);
    await waitFor(() => {
      expect(
        screen.getByText(
          /Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i,
        ),
      ).toBeTruthy();
    });
    expect(
      screen.getByRole("link", { name: /Otwórz w katalogu|Open in catalog/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Zamknij informację|Dismiss notice/i }),
    ).toBeTruthy();
  });

  it("IB-2: clicking dismiss button hides the info-bar", async () => {
    renderWithRouter(<ShareMemberContextInfoBar modelId="m1" />);
    const dismissBtn = await waitFor(() =>
      screen.getByRole("button", {
        name: /Zamknij informację|Dismiss notice/i,
      }),
    );
    fireEvent.click(dismissBtn);
    await waitFor(() => {
      expect(
        screen.queryByText(
          /Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i,
        ),
      ).toBeNull();
    });
    expect(sessionStorage.getItem("share-context-dismissed:m1")).toBe("1");
  });

  it("IB-3: dismissing modelId A does not silence modelId B", async () => {
    sessionStorage.setItem("share-context-dismissed:m1", "1");
    renderWithRouter(<ShareMemberContextInfoBar modelId="m2" />);
    await waitFor(() => {
      expect(
        screen.getByText(
          /Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i,
        ),
      ).toBeTruthy();
    });
  });

  it("IB-4: pre-seeded sessionStorage renders nothing on mount", async () => {
    sessionStorage.setItem("share-context-dismissed:m1", "1");
    renderWithRouter(<ShareMemberContextInfoBar modelId="m1" />);
    // Give the router a tick to mount, then assert the bar is absent.
    await new Promise((r) => setTimeout(r, 50));
    expect(
      screen.queryByText(
        /Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i,
      ),
    ).toBeNull();
  });
});
