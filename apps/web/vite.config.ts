import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";

import { sentryVitePlugin } from "@sentry/vite-plugin";
import { TanStackRouterVite } from "@tanstack/router-vite-plugin";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

function tryGitShortSha(): string | null {
  try {
    return execSync("git rev-parse --short HEAD", { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return null;
  }
}

const GIT_COMMIT = process.env.VITE_GIT_COMMIT?.trim() || tryGitShortSha() || "unknown";
const BUILD_TIME = process.env.VITE_BUILD_TIME?.trim() || new Date().toISOString();
const PKG_VERSION = JSON.parse(readFileSync("./package.json", "utf-8")).version as string;

export default defineConfig({
  plugins: [
    TanStackRouterVite({ routesDirectory: "src/routes", routeFileIgnorePattern: "\\.js$" }),
    react(),
    // Sentry/GlitchTip source-map upload + debug-ID injection.
    // Dormant until Story 1.5 lands the BuildKit secret in the docker build
    // context; `disable: !process.env.SENTRY_AUTH_TOKEN` short-circuits the
    // plugin when the token is absent (production docker builds today,
    // off-LAN CI, plain `npm run build` from a contributor box without a
    // homelab token). Once 1.5 ships, the docker stage gets the token and
    // this gate auto-flips to active. MUST stay LAST in plugins[] per
    // architecture AR3.
    sentryVitePlugin({
      url: process.env.SENTRY_URL,
      org: "homelab",
      project: "3d-portal",
      authToken: process.env.SENTRY_AUTH_TOKEN,
      // Same `${PKG_VERSION}+${GIT_COMMIT}` expression as src/release.ts.
      // Drift-impossible: both pipelines read from the same env-var → host-git
      // → "unknown" fallback chain plus apps/web/package.json. Inlining here
      // (instead of `import { RELEASE } from "./src/release"`) avoids a
      // chicken/egg problem: vite bundles this config BEFORE the `define`
      // block is active, so ambient `__PKG_VERSION__` / `__GIT_COMMIT__` are
      // not yet substituted in src/ imports.
      release: { name: `${PKG_VERSION}+${GIT_COMMIT}` },
      sourcemaps: { filesToDeleteAfterUpload: ["./dist/**/*.map"] },
      telemetry: false,
    }),
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  define: {
    __GIT_COMMIT__: JSON.stringify(GIT_COMMIT),
    __BUILD_TIME__: JSON.stringify(BUILD_TIME),
    __PKG_VERSION__: JSON.stringify(PKG_VERSION),
  },
  build: {
    sourcemap: "hidden",
    rollupOptions: {
      output: {
        // Source maps default to paths relative to the .map file
        // (`../src/main.tsx` from `dist/assets/`); GlitchTip reflects those
        // back as the resolved frame. NFR-R1 pins the regex to
        // `^apps/web/src/.+\.tsx?$` so the verify ritual rejects permissive
        // globs. Rewrite source paths from the project's PoV (drop the
        // ../src/ prefix, anchor at apps/web/src/...) so the regex bites.
        sourcemapPathTransform: (relativeSourcePath: string) => {
          // Strip any leading `./` or `../` segments, then anchor app source
          // paths at `apps/web/<...>` (so `src/main.tsx` and `./src/main.tsx`
          // both become `apps/web/src/main.tsx`). Pre-anchored paths
          // (`apps/web/src/...`, `apps/web/public/...`) pass through. Vendor
          // paths under `node_modules/` are left untouched — symbolicator
          // resolves them best-effort.
          const stripped = relativeSourcePath.replace(/^(?:\.\.?\/)+/, "");
          if (stripped.startsWith("apps/web/src/") || stripped.startsWith("apps/web/public/")) {
            return stripped;
          }
          if (stripped.startsWith("src/") || stripped.startsWith("public/")) {
            return `apps/web/${stripped}`;
          }
          return stripped;
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
