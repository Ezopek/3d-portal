// @vitest-environment node
//
// vite.config.ts pulls in the Vite plugin pipeline (esbuild, unplugin, etc.).
// Those modules check `new TextEncoder().encode("") instanceof Uint8Array`
// at import time, which fails under jsdom's TextEncoder polyfill. Force the
// node env for this single test file so the config module can load cleanly.

import { describe, expect, it, vi } from "vitest";

// TB-002: stub out plugin imports that transitively load `unplugin`.
// `unplugin/dist/index.mjs` evaluates `path.resolve(import.meta.dirname, ...)`
// at the top of the rspack/webpack sections (lines 873-874 / 1015-1016).
// `import.meta.dirname` is only defined in Node ≥ 20.11; on hosts running
// Node 18 (the dev box at the time of writing this comment) it is undefined
// and `resolve(undefined, "...")` throws
// `TypeError: paths[0] must be string` at module load — failing the whole
// test file before any `it` runs. `package.json#engines.node` pins >=20.11 as
// a soft constraint, so npm only warns; a hard host fix (`nvm use 22`) would
// also resolve TB-002 root-cause, but stubbing keeps this test runnable on
// any Node and isolates it from a concern (host Node version) it has no
// reason to depend on.
//
// The assertions below only check plugin name + position in plugins[], not
// real plugin behavior, so no-op factories returning named objects are
// sufficient. Two direct unplugin transitives must be stubbed:
//   - `@tanstack/router-vite-plugin` (via `@tanstack/router-plugin`)
//   - `@sentry/vite-plugin` (via `@sentry/bundler-plugin-core`) — belt-and-
//     suspenders; observed under Node 18 the TanStack import was the first
//     to throw at module-evaluation time, but which transitive evaluates
//     first is an implementation detail of the package graph at any given
//     version.
//
// `sentryVitePlugin()` in production returns `Plugin[]` (an internal array),
// so the stub returns `[{ name: ... }]` to mirror the real shape — keeps
// `flattenPlugins()` semantics identical and protects against Sentry adding
// a second internal plugin to the array.
//
// If this test starts failing again under a similar TypeError, check
// `vite.config.ts` for newly-added plugins that depend transitively on
// `unplugin` and add a matching `vi.mock` here.
vi.mock("@tanstack/router-vite-plugin", () => ({
  TanStackRouterVite: () => ({ name: "tanstack-router-vite-plugin" }),
}));
vi.mock("@sentry/vite-plugin", () => ({
  sentryVitePlugin: () => [{ name: "sentry-vite-plugin" }],
}));

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
