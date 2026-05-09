// @vitest-environment node
//
// vite.config.ts pulls in the Vite plugin pipeline (esbuild, unplugin, etc.).
// Those modules check `new TextEncoder().encode("") instanceof Uint8Array`
// at import time, which fails under jsdom's TextEncoder polyfill. Force the
// node env for this single test file so the config module can load cleanly.

import { describe, expect, it } from "vitest";

import config from "../vite.config";

interface NamedPlugin {
  name: string;
}

function flattenPlugins(): NamedPlugin[] {
  // Vite's `plugins` may be `(Plugin | Plugin[] | undefined | false)[]`; the
  // Sentry bundler-plugins-core returns an array of internal plugins, so we
  // flatten one level and keep only entries that carry a `name` field.
  const raw = (config.plugins ?? []) as unknown[];
  return raw
    .flat()
    .filter((p): p is NamedPlugin => Boolean(p && typeof p === "object" && "name" in (p as object)));
}

describe("vite.config.ts plugins[]", () => {
  it("has at least one Sentry plugin entry", () => {
    const flat = flattenPlugins();
    expect(flat.some((p) => /sentry/i.test(p.name))).toBe(true);
  });

  it("places the Sentry plugin LAST in the flattened plugins[] (architecture AR3)", () => {
    const flat = flattenPlugins();
    expect(flat.length).toBeGreaterThan(0);
    const last = flat[flat.length - 1];
    expect(last).toBeDefined();
    expect(last?.name).toMatch(/sentry/i);
  });
});
