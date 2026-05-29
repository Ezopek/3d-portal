import { describe, expect, it } from "vitest";

import { Route as IndexRoute } from "./index";
import { LandingPage } from "@/modules/landing/LandingPage";

// Story 31.4 (Init 19) — / graduates from a redirect-only stub to a real
// landing surface hosting the LowStockCard. The pre-31.4 redirect-to-
// /catalog deferral was explicitly conditioned on "second module ships";
// /spools now ships (Story 31.3), so the upgrade is intentional.
describe("/ (landing)", () => {
  it("renders the LandingPage component (no redirect)", () => {
    expect(IndexRoute.options.component).toBe(LandingPage);
    expect(IndexRoute.options.beforeLoad).toBeUndefined();
  });
});
