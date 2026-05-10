import { describe, expect, it } from "vitest";

import { Route as IndexRoute } from "./index";

// Index route is a redirect-only stub: v1 has just one working module (catalog),
// so / has no useful landing — it should hand off immediately.
describe("/ (landing)", () => {
  it("redirects to /catalog via beforeLoad", () => {
    const beforeLoad = IndexRoute.options.beforeLoad;
    expect(beforeLoad).toBeTypeOf("function");
    let thrown: unknown;
    try {
      // beforeLoad is called by the router with a context; we only care that
      // it throws a redirect descriptor with the right `to`.
      (beforeLoad as (ctx: unknown) => unknown)({});
    } catch (e) {
      thrown = e;
    }
    expect(thrown).toBeDefined();
    // TanStack Router's `redirect()` returns a Response-like object; its
    // navigation target lives at `.options.to`.
    const r = thrown as { options?: { to?: string } };
    expect(r.options?.to).toBe("/catalog");
  });
});
