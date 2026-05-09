/**
 * Single-source release identity for this build.
 *
 * Format: `<pkg.version>+<git_short_sha>` (e.g., `"0.1.0+946fb52"`).
 *
 * The two halves are injected at build time by Vite `define` (see
 * `apps/web/vite.config.ts`). Both `vite serve` (dev) and `vite build`
 * (prod) resolve the values; `__GIT_COMMIT__` falls back to `"unknown"`
 * if no git context is available (off-LAN CI, etc.).
 *
 * Drift between this expression and any other place that reports a
 * release tag = TypeScript compile error or `release.test.ts` failure.
 */
export const RELEASE: string = `${__PKG_VERSION__}+${__GIT_COMMIT__}`;
