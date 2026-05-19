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

function buildRouter(node: ReactNode, initialPath: string) {
  const root = createRootRoute();
  const settings2faRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/2fa",
    component: () => <>{node}</>,
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
  const sessionsRoute = createRoute({
    getParentRoute: () => root,
    path: "/settings/sessions",
    component: () => <div>sessions</div>,
  });
  return createRouter({
    routeTree: root.addChildren([settings2faRoute, queueRoute, sessionsRoute]),
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });
}

function mount(node: ReactNode) {
  const router = buildRouter(node, "/settings/2fa");
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function mountAtSettings2fa(node: ReactNode, next: string) {
  const router = buildRouter(
    node,
    `/settings/2fa?next=${encodeURIComponent(next)}`,
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router };
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

describe("Settings2faPage — forced-enrollment mode (Story 7.4)", () => {
  it("renders forced-enrollment banner when next URL param is present", async () => {
    // S1 — banner is visible when arriving from the forced-enrollment login branch.
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") {
        return {
          enabled: false,
          batch_id: null,
          generated_at: null,
          codes_remaining: null,
        };
      }
      throw new Error(`unexpected api path: ${path}`);
    });
    mountAtSettings2fa(<Settings2faPage />, "/queue");
    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      const forced = alerts.find((el) =>
        el.textContent?.includes("Your role requires two-factor"),
      );
      expect(forced).toBeTruthy();
    });
  });

  it("navigates to next after enrollment-confirm success when forced-enrollment mode", async () => {
    // S2 — after the user finishes the wizard, the page hands them back to `next`.
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") {
        return {
          enabled: false,
          batch_id: null,
          generated_at: null,
          codes_remaining: null,
        };
      }
      if (path === "/auth/2fa/enroll") {
        return {
          qr_svg: '<svg><title>fixture</title></svg>',
          manual_secret: "AAAA1111BBBB2222CCCC3333DDDD4444",
          enrollment_token: "tok-s2",
        };
      }
      if (path === "/auth/2fa/enroll/confirm") {
        return {
          recovery_codes: ["aaaa1111", "bbbb2222"],
          batch_id: "batch-s2",
          generated_at: "2026-05-19T00:00:00Z",
        };
      }
      throw new Error(`unexpected api path: ${path}`);
    });
    const { router } = mountAtSettings2fa(<Settings2faPage />, "/queue");

    // Step 1: status → click Enable.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /enable|włącz/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /enable|włącz/i }));

    // Step 2: enroll panel → type code + click Verify.
    await waitFor(() => {
      expect(screen.getByTestId("totp-qr")).toBeTruthy();
    });
    const codeInput = screen.getByLabelText(/6-digit|6-cyfrowy/i) as HTMLInputElement;
    fireEvent.change(codeInput, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /verify|zweryfikuj/i }));

    // Step 3: show-codes → check the "saved" box + click Continue.
    await waitFor(() => {
      expect(screen.getByTestId("totp-recovery-codes")).toBeTruthy();
    });
    const savedCheckbox = screen.getByRole("checkbox") as HTMLInputElement;
    fireEvent.click(savedCheckbox);
    fireEvent.click(screen.getByRole("button", { name: /continue|kontynuuj/i }));

    // Forced-enrollment mode → router should now be at /queue, not the done panel.
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/queue");
    });
  });
});

describe("Settings2faPage — Regenerate + Disable flows (Story 7.5)", () => {
  function statusEnabledFixture() {
    return {
      enabled: true,
      batch_id: "batch-existing",
      generated_at: "2026-05-19T00:00:00Z",
      codes_remaining: 5,
    };
  }

  async function fillReauthModal(password: string, code: string) {
    const passwordInput = screen.getByLabelText(/password|hasło/i) as HTMLInputElement;
    const codeInput = screen.getByLabelText(/6-digit|6-cyfrowy/i) as HTMLInputElement;
    fireEvent.change(passwordInput, { target: { value: password } });
    fireEvent.change(codeInput, { target: { value: code } });
  }

  it("V7 — Regenerate flow: clicking regenerate button opens reauth modal; submit transitions to show-codes step displaying new cleartext codes", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") return statusEnabledFixture();
      if (path === "/auth/2fa/recovery-codes/regenerate") {
        return {
          recovery_codes: [
            "aaaa1111",
            "bbbb2222",
            "cccc3333",
            "dddd4444",
            "eeee5555",
            "ffff6666",
            "00007777",
            "11118888",
          ],
          batch_id: "batch-new",
          generated_at: "2026-05-19T00:00:00Z",
        };
      }
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
      ).toBeTruthy();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    });
    await fillReauthModal("Sup3rPassword!", "123456");
    fireEvent.click(
      screen.getByRole("button", { name: /generate new codes|wygeneruj nowe kody/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("totp-recovery-codes")).toBeTruthy();
    });
    expect(screen.getByText(/aaaa1111/)).toBeTruthy();
    expect(screen.queryByTestId("reauth-2fa-modal")).toBeNull();
  });

  it("V8 — Regenerate 401 keeps modal open with error message; does NOT advance to show-codes", async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") return statusEnabledFixture();
      if (path === "/auth/2fa/recovery-codes/regenerate") {
        const { ApiError } = await import("@/lib/api");
        throw new ApiError(401, { detail: "invalid_credentials" }, "401");
      }
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
      ).toBeTruthy();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    });
    await fillReauthModal("wrong-pw", "123456");
    fireEvent.click(
      screen.getByRole("button", { name: /generate new codes|wygeneruj nowe kody/i }),
    );

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      const credErr = alerts.find((el) =>
        el.textContent?.match(/incorrect password or code|nieprawidłowe hasło/i),
      );
      expect(credErr).toBeTruthy();
    });
    // Modal still open + we did NOT advance to show-codes.
    expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    expect(screen.queryByTestId("totp-recovery-codes")).toBeNull();
  });

  it("V9 — Disable flow: clicking disable button opens reauth modal; submit closes modal, invalidates status query, resets to status step", async () => {
    let statusCalls = 0;
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") {
        statusCalls += 1;
        // First call returns enabled; subsequent (post-invalidate) returns disabled.
        return statusCalls === 1
          ? statusEnabledFixture()
          : {
              enabled: false,
              batch_id: null,
              generated_at: null,
              codes_remaining: null,
            };
      }
      if (path === "/auth/2fa/disable") {
        return undefined;
      }
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /disable 2fa|wyłącz 2fa/i }),
      ).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /disable 2fa|wyłącz 2fa/i }));

    await waitFor(() => {
      expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    });
    await fillReauthModal("Sup3rPassword!", "123456");
    // The modal renders TWO "Disable 2FA" buttons (the enabled-panel button
    // behind it + the modal submit). Pick the submit by querying inside the
    // dialog.
    const dialog = screen.getByTestId("reauth-2fa-modal");
    const submit = dialog.querySelectorAll("button");
    // Last button inside the form is the submit (Cancel + Submit pair).
    fireEvent.click(submit[submit.length - 1] as HTMLButtonElement);

    await waitFor(() => {
      expect(screen.queryByTestId("reauth-2fa-modal")).toBeNull();
    });
    // Status query refetched -> disabled panel CTA rendered.
    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: /enable two-factor|włącz uwierzytelnianie/i,
        }),
      ).toBeTruthy();
    });
    expect(statusCalls).toBeGreaterThanOrEqual(2);
  });

  it("V10 — Disable 401 keeps modal open with error message; status query is NOT invalidated", async () => {
    let statusCalls = 0;
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === "/auth/2fa/status") {
        statusCalls += 1;
        return statusEnabledFixture();
      }
      if (path === "/auth/2fa/disable") {
        const { ApiError } = await import("@/lib/api");
        throw new ApiError(401, { detail: "invalid_credentials" }, "401");
      }
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /disable 2fa|wyłącz 2fa/i }),
      ).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /disable 2fa|wyłącz 2fa/i }));

    await waitFor(() => {
      expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    });
    await fillReauthModal("wrong-pw", "123456");
    const dialog = screen.getByTestId("reauth-2fa-modal");
    const formButtons = dialog.querySelectorAll("button");
    fireEvent.click(formButtons[formButtons.length - 1] as HTMLButtonElement);

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      const credErr = alerts.find((el) =>
        el.textContent?.match(/incorrect password or code|nieprawidłowe hasło/i),
      );
      expect(credErr).toBeTruthy();
    });
    expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    // Status query was NOT invalidated -> still exactly one call.
    expect(statusCalls).toBe(1);
  });

  it("V11 — Cancel button in reauth modal closes modal without firing API call", async () => {
    const calls: string[] = [];
    vi.mocked(api).mockImplementation(async (path: string) => {
      calls.push(path);
      if (path === "/auth/2fa/status") return statusEnabledFixture();
      throw new Error(`unexpected api path: ${path}`);
    });

    mount(<Settings2faPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
      ).toBeTruthy();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /regenerate codes|wygeneruj nowe kody/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("reauth-2fa-modal")).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /cancel|anuluj/i }));

    await waitFor(() => {
      expect(screen.queryByTestId("reauth-2fa-modal")).toBeNull();
    });
    expect(
      calls.filter(
        (p) =>
          p === "/auth/2fa/recovery-codes/regenerate" || p === "/auth/2fa/disable",
      ),
    ).toHaveLength(0);
  });
});
