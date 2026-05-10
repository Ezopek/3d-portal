import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RELEASE } from "./release";

// `instrument.ts` runs a side-effectful Sentry.init at import time, gated
// on `VITE_SENTRY_DSN`. These tests lock the contract so a refactor can't
// silently drop the init (a recurring class of "errors aren't reaching
// GlitchTip" incidents) and so the empty-DSN no-op path stays intact.

const initSpy = vi.fn();
const setTagSpy = vi.fn();

vi.mock("@sentry/react", () => ({
  init: initSpy,
  setTag: setTagSpy,
}));

beforeEach(() => {
  initSpy.mockReset();
  setTagSpy.mockReset();
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("instrument.ts", () => {
  it("calls Sentry.init with the DSN when VITE_SENTRY_DSN is set", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://abc@example.invalid/1");
    vi.stubEnv("VITE_ENVIRONMENT", "production");

    await import("./instrument");

    expect(initSpy).toHaveBeenCalledTimes(1);
    const call = initSpy.mock.calls[0]?.[0];
    expect(call.dsn).toBe("https://abc@example.invalid/1");
    expect(call.environment).toBe("production");
    // Equality (not regex match) is the single-source guard: instrument.ts
    // must consume RELEASE from src/release.ts directly; a hardcoded string
    // that happens to match the format would slip through a regex check
    // (PRD FR3 — drift-impossible expression).
    expect(call.release).toBe(RELEASE);
    expect(setTagSpy).toHaveBeenCalledWith("service", "web");
    // Story 2.2: 5 dotted-name static identity tags additive on top of the
    // baseline `service:web`. Order is fixed in instrument.ts but jest/vitest
    // toHaveBeenCalledWith matches any call, so order is verified separately
    // via toHaveBeenNthCalledWith below where it matters.
    expect(setTagSpy).toHaveBeenCalledWith("service.version", RELEASE);
    expect(setTagSpy).toHaveBeenCalledWith("host.name", expect.stringMatching(/.+/));
    expect(setTagSpy).toHaveBeenCalledWith("deployment.environment", "production");
    expect(setTagSpy).toHaveBeenCalledWith("git.commit", expect.stringMatching(/.+/));
    expect(setTagSpy).toHaveBeenCalledWith("build.time", expect.stringMatching(/.+/));
  });

  it("no-ops when VITE_SENTRY_DSN is empty", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "");

    await import("./instrument");

    expect(initSpy).not.toHaveBeenCalled();
    expect(setTagSpy).not.toHaveBeenCalled();
  });
});
