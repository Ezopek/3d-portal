import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";

import { applyBeforeSendFilters } from "./instrument-filters";

interface FakeEvent {
  request?: { url?: string };
  exception?: { values?: Array<{ value?: string; type?: string }> };
}

interface FakeHint {
  originalException?: unknown;
}

function makeEvent(overrides: Partial<FakeEvent> = {}): FakeEvent {
  return {
    request: { url: "https://3d.ezop.ddns.net/" },
    exception: { values: [{ type: "Error", value: "Real error" }] },
    ...overrides,
  };
}

function makeHint(orig: unknown = undefined): FakeHint {
  return { originalException: orig };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("applyBeforeSendFilters — 5-step ordered chain (architecture Decision H)", () => {
  it("drops_via_denyUrls when event.request.url matches a browser-extension scheme", () => {
    const event = makeEvent({ request: { url: "chrome-extension://abc/inject.js" } });

    const result = applyBeforeSendFilters(
      event as Parameters<typeof applyBeforeSendFilters>[0],
      makeHint() as Parameters<typeof applyBeforeSendFilters>[1],
    );

    expect(result).toBeNull();
  });

  it("drops_via_ignoreErrors when event.exception.values[0].value matches a noise title", () => {
    const event = makeEvent({
      exception: { values: [{ value: "ResizeObserver loop limit exceeded" }] },
    });

    const result = applyBeforeSendFilters(
      event as Parameters<typeof applyBeforeSendFilters>[0],
      makeHint() as Parameters<typeof applyBeforeSendFilters>[1],
    );

    expect(result).toBeNull();
  });

  it("drops_when_offline when navigator.onLine is false", () => {
    vi.stubGlobal("navigator", { onLine: false });
    const event = makeEvent();

    const result = applyBeforeSendFilters(
      event as Parameters<typeof applyBeforeSendFilters>[0],
      makeHint() as Parameters<typeof applyBeforeSendFilters>[1],
    );

    expect(result).toBeNull();
  });

  it("drops_access_expired when hint.originalException is an ApiError with body.detail === 'access_expired'", () => {
    const event = makeEvent();
    const orig = new ApiError(401, { detail: "access_expired" }, "401 Unauthorized");

    const result = applyBeforeSendFilters(
      event as Parameters<typeof applyBeforeSendFilters>[0],
      makeHint(orig) as Parameters<typeof applyBeforeSendFilters>[1],
    );

    expect(result).toBeNull();
  });

  it("passes_through_default for a normal error event with hint that does not match any drop branch", () => {
    const event = makeEvent();
    // navigator.onLine defaults to true in jsdom; explicitly set for determinism.
    vi.stubGlobal("navigator", { onLine: true });

    const result = applyBeforeSendFilters(
      event as Parameters<typeof applyBeforeSendFilters>[0],
      makeHint() as Parameters<typeof applyBeforeSendFilters>[1],
    );

    expect(result).toBe(event);
  });
});
