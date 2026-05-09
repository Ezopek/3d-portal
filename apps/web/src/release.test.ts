import { describe, expect, it } from "vitest";

import { RELEASE } from "./release";

describe("RELEASE", () => {
  it("matches the documented format `<semver>+<sha-or-unknown>`", () => {
    expect(RELEASE).toMatch(/^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$/);
  });

  it("contains the package.json version as the prefix", async () => {
    const pkg = (await import("../package.json")).default;
    expect(RELEASE.startsWith(`${pkg.version}+`)).toBe(true);
  });

  it("does not embed a literal `__PKG_VERSION__` token (define must substitute)", () => {
    expect(RELEASE).not.toContain("__PKG_VERSION__");
    expect(RELEASE).not.toContain("__GIT_COMMIT__");
  });
});
