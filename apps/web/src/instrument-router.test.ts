import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock @sentry/react and @/shell/AuthContext BEFORE importing the SUT.
// The SUT imports both at module load time; vi.mock hoists above imports
// so the spies are in place when ./instrument-router pulls them in.
const setTagSpy = vi.fn();
vi.mock("@sentry/react", () => ({
  setTag: setTagSpy,
}));

const getAuthSnapshotSpy = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  getAuthSnapshot: getAuthSnapshotSpy,
}));

interface FakeMatch {
  routeId: string;
  params?: Record<string, string>;
}

interface FakeRouterHarness {
  router: {
    subscribe: ReturnType<typeof vi.fn>;
    state: { matches: FakeMatch[] };
  };
  fire: (event: { toLocation: { pathname: string } }) => void;
  setMatches: (m: FakeMatch[]) => void;
}

function makeFakeRouter(): FakeRouterHarness {
  let listener: ((event: unknown) => void) | null = null;
  const router = {
    subscribe: vi.fn((event: string, fn: (event: unknown) => void) => {
      if (event === "onLoad") listener = fn;
      return () => {
        listener = null;
      };
    }),
    state: { matches: [] as FakeMatch[] },
  };
  return {
    router,
    fire: (event) => listener?.(event),
    setMatches: (m) => {
      router.state.matches = m;
    },
  };
}

beforeEach(() => {
  setTagSpy.mockReset();
  getAuthSnapshotSpy.mockReset();
  // Default snapshot — individual tests override.
  getAuthSnapshotSpy.mockReturnValue({ isAuthenticated: false });
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("instrument-router.ts", () => {
  it("subscribes to the router 'onLoad' event exactly once", async () => {
    const { router } = makeFakeRouter();
    const { attachRouterContext } = await import("./instrument-router");

    const unsubscribe = attachRouterContext(router as never);

    expect(router.subscribe).toHaveBeenCalledTimes(1);
    expect(router.subscribe).toHaveBeenCalledWith("onLoad", expect.any(Function));
    expect(typeof unsubscribe).toBe("function");
  });

  it("sets route.pathname from event.toLocation.pathname on each onLoad", async () => {
    const harness = makeFakeRouter();
    const { attachRouterContext } = await import("./instrument-router");
    attachRouterContext(harness.router as never);

    harness.fire({ toLocation: { pathname: "/catalog/m_142" } });

    expect(setTagSpy).toHaveBeenCalledWith("route.pathname", "/catalog/m_142");
  });

  it("sets model.id when /catalog/$id is in router.state.matches", async () => {
    const harness = makeFakeRouter();
    harness.setMatches([
      { routeId: "/catalog/$id", params: { id: "m_142" } },
      { routeId: "__root", params: {} },
    ]);
    const { attachRouterContext } = await import("./instrument-router");
    attachRouterContext(harness.router as never);

    harness.fire({ toLocation: { pathname: "/catalog/m_142" } });

    expect(setTagSpy).toHaveBeenCalledWith("model.id", "m_142");
  });

  it("clears model.id (passes undefined) when /catalog/$id is NOT matched", async () => {
    const harness = makeFakeRouter();
    harness.setMatches([
      { routeId: "/catalog/", params: {} },
      { routeId: "__root", params: {} },
    ]);
    const { attachRouterContext } = await import("./instrument-router");
    attachRouterContext(harness.router as never);

    harness.fire({ toLocation: { pathname: "/catalog" } });

    expect(setTagSpy).toHaveBeenCalledWith("model.id", undefined);
  });

  it("sets auth.is_authenticated as a stringified boolean from getAuthSnapshot()", async () => {
    const harness = makeFakeRouter();

    getAuthSnapshotSpy.mockReturnValue({ isAuthenticated: true });
    const { attachRouterContext } = await import("./instrument-router");
    attachRouterContext(harness.router as never);
    harness.fire({ toLocation: { pathname: "/" } });
    expect(setTagSpy).toHaveBeenCalledWith("auth.is_authenticated", "true");

    setTagSpy.mockReset();
    getAuthSnapshotSpy.mockReturnValue({ isAuthenticated: false });
    harness.fire({ toLocation: { pathname: "/login" } });
    expect(setTagSpy).toHaveBeenCalledWith("auth.is_authenticated", "false");
  });
});
