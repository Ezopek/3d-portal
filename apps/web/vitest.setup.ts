import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest.config.ts uses `globals: false`, which prevents
// @testing-library/react from registering its own afterEach(cleanup).
// Register it once globally here so every test file gets DOM teardown
// between `it` blocks without per-file boilerplate. Per-file cleanup
// calls in existing tests are now redundant but harmless (cleanup is
// idempotent — once nothing is mounted, a second cleanup is a no-op).
afterEach(() => {
  cleanup();
});
