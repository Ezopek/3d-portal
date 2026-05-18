import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Node 22+ ships a native `localStorage` global (gated on
// `--localstorage-file=<path>`). When that flag is absent (our case),
// the global still exists but is an empty object `{}` with no Storage
// methods — and it shadows jsdom's Storage instance because jsdom skips
// installing its own when a same-name global is already present.
// Result: `localStorage.clear()` (and every other Storage method) throws
// `TypeError: ... is not a function`.
//
// Install a minimal in-memory Storage shim on both `globalThis` and
// `window` so tests get a working Storage interface regardless of Node
// version. Reset its contents in `beforeEach` would be ideal, but we
// preserve the existing per-test contract (tests call `localStorage.clear()`
// themselves), so we just ensure the API is present and functional.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? (store.get(key) as string) : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  };
  return storage;
}

function installStorage(): void {
  const memory = createMemoryStorage();
  // jsdom sets `window === globalThis`, so a single override on globalThis
  // also covers `window.localStorage`. Verified empirically in this setup.
  Object.defineProperty(globalThis, "localStorage", {
    value: memory,
    writable: true,
    configurable: true,
  });
}

installStorage();

// vitest.config.ts uses `globals: false`, which prevents
// @testing-library/react from registering its own afterEach(cleanup).
// Register it once globally here so every test file gets DOM teardown
// between `it` blocks without per-file boilerplate. Per-file cleanup
// calls in existing tests are now redundant but harmless (cleanup is
// idempotent — once nothing is mounted, a second cleanup is a no-op).
afterEach(() => {
  cleanup();
});
