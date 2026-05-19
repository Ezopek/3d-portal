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
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message?: string) {
      super(message);
      this.status = status;
    }
  },
  api: vi.fn(),
}));

import { api } from "@/lib/api";
import i18n from "@/locales/i18n";
import { Settings2faPage } from "./Settings2faPage";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function mount(node: ReactNode) {
  const root = createRootRoute({ component: () => <>{node}</> });
  const sessionsRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/sessions",
    component: () => <div>sessions</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([sessionsRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("Settings2faPage — Restart wizard regression (Codex P2 UX)", () => {
  it("keeps the enroll panel mounted while the restart /enroll request is in flight", async () => {
    // Hand-rolled router to resolve /enroll once, then hang the restart call
    // so we can observe the in-flight state. The done panel must NOT appear
    // — clearing enrollState eagerly used to fall through to "2FA enabled".
    let resolveSecondEnroll: (value: unknown) => void = () => undefined;
    const calls: string[] = [];
    let enrollCallCount = 0;
    vi.mocked(api).mockImplementation(async (path: string) => {
      calls.push(path);
      if (path === "/auth/2fa/status") {
        return {
          enabled: false,
          batch_id: null,
          generated_at: null,
          codes_remaining: null,
        };
      }
      if (path === "/auth/2fa/enroll") {
        enrollCallCount += 1;
        if (enrollCallCount === 1) {
          return {
            qr_svg: '<svg data-testid="initial-qr"><title>initial</title></svg>',
            manual_secret: "AAAA1111BBBB2222CCCC3333DDDD4444",
            enrollment_token: "tok-initial",
          };
        }
        // Second /enroll (the restart) — hang until we resolve it manually.
        return new Promise((res) => {
          resolveSecondEnroll = res;
        });
      }
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    // Wait for status → enroll → enroll panel mount.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /enable|włącz/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /enable|włącz/i }));

    await waitFor(() => {
      expect(screen.getByTestId("totp-qr")).toBeTruthy();
    });
    expect(screen.getByTestId("totp-qr").innerHTML).toContain("initial");

    // Click Restart — second /enroll fires but never resolves yet.
    fireEvent.click(screen.getByRole("button", { name: /restart|zacznij od nowa/i }));

    // Give React the chance to commit the post-click render. The fix preserves
    // enrollState until the new /enroll succeeds, so the enroll panel must
    // still be on screen and the done panel must NOT have rendered.
    await waitFor(() => {
      // The Restart button is disabled while enroll.isPending — assertion that
      // the click actually kicked off the mutation.
      const restart = screen.getByRole("button", {
        name: /restart|zacznij od nowa/i,
      }) as HTMLButtonElement;
      expect(restart.disabled).toBe(true);
    });

    // Regression assertion: the done panel must NOT be rendered while restart
    // is in-flight. enroll panel (QR + code input + verify button) must stay.
    expect(
      screen.queryByText(/two-factor authentication enabled|włączone/i),
    ).toBeNull();
    expect(screen.queryByText(/use your authenticator app|użyj aplikacji/i)).toBeNull();
    expect(screen.getByTestId("totp-qr")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /verify|zweryfikuj/i }),
    ).toBeTruthy();

    // Now let the restart resolve with a fresh payload — the new QR should
    // replace the old one, and we should remain on the enroll panel.
    await act(async () => {
      resolveSecondEnroll({
        qr_svg: '<svg data-testid="restart-qr"><title>restart</title></svg>',
        manual_secret: "EEEE5555FFFF6666GGGG7777HHHH8888",
        enrollment_token: "tok-restart",
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-qr").innerHTML).toContain("restart");
    });

    // Still on enroll step — never advanced to done.
    expect(
      screen.queryByText(/two-factor authentication enabled|włączone/i),
    ).toBeNull();
    expect(calls.filter((c) => c === "/auth/2fa/enroll")).toHaveLength(2);
  });
});
