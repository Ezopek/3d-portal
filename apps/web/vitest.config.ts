import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { hostname as osHostname } from "node:os";
import path from "node:path";

import { defineConfig } from "vitest/config";

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
const BUILD_HOST = process.env.VITE_BUILD_HOST?.trim() || osHostname() || "unknown";
const PKG_VERSION = JSON.parse(readFileSync("./package.json", "utf-8")).version as string;

export default defineConfig({
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  define: {
    __GIT_COMMIT__: JSON.stringify(GIT_COMMIT),
    __BUILD_TIME__: JSON.stringify(BUILD_TIME),
    __BUILD_HOST__: JSON.stringify(BUILD_HOST),
    __PKG_VERSION__: JSON.stringify(PKG_VERSION),
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./vitest.setup.ts"],
    exclude: ["**/node_modules/**", "**/tests/visual/**"],
  },
});
