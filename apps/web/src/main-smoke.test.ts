import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// `main.tsx` runs side-effect Sentry init + smoke handler at import time.
// To unit-test the smoke handler in isolation we mock @sentry/react before
// import and assert the captureException shape. Mirrors the vi.mock pattern
// in instrument.test.ts to keep the contract explicit: production smoke
// triggered via `?__sentry_smoke=<uuid>` MUST emit exactly one
// `Sentry.captureException` call with the run id attached as a tag —
// `verify-symbolication.sh` queries GlitchTip by that tag, so any drift in
// the attachment shape silently breaks the verify ritual.

const initSpy = vi.fn();
const setTagSpy = vi.fn();
const captureExceptionSpy = vi.fn();
const flushSpy = vi.fn().mockResolvedValue(true);

vi.mock("@sentry/react", () => ({
  init: initSpy,
  setTag: setTagSpy,
  captureException: captureExceptionSpy,
  flush: flushSpy,
}));

// react-dom/client.createRoot().render() must be a no-op in jsdom or it
// pulls in App, routes, and a heap of providers. Replace with a stub so the
// import-time evaluation of main.tsx exercises only the smoke-handler block.
vi.mock("react-dom/client", () => ({
  default: {
    createRoot: () => ({ render: vi.fn() }),
  },
  createRoot: () => ({ render: vi.fn() }),
}));

beforeEach(() => {
  initSpy.mockReset();
  setTagSpy.mockReset();
  captureExceptionSpy.mockReset();
  flushSpy.mockClear();
  vi.resetModules();
  // jsdom seeds location at about:blank — replace via history API so the
  // URLSearchParams probe resolves the query param under test.
  document.body.innerHTML = '<div id="root"></div>';
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("main.tsx smoke handler", () => {
  it("captures an exception tagged with smoke.run_id when ?__sentry_smoke=<uuid> is present", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://abc@example.invalid/1");
    window.history.replaceState(null, "", "/?__sentry_smoke=test-uuid-1234");

    await import("./main");

    expect(captureExceptionSpy).toHaveBeenCalledTimes(1);
    const [err, ctx] = captureExceptionSpy.mock.calls[0] ?? [];
    expect(err).toBeInstanceOf(Error);
    expect((err as Error).message).toBe("smoke test-uuid-1234");
    expect(ctx).toEqual({ tags: { "smoke.run_id": "test-uuid-1234" } });
  });

  it("does not capture an exception when ?__sentry_smoke is absent", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://abc@example.invalid/1");
    window.history.replaceState(null, "", "/");

    await import("./main");

    expect(captureExceptionSpy).not.toHaveBeenCalled();
  });
});
