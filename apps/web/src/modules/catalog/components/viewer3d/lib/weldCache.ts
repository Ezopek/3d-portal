import type { WeldedMesh } from "./welder";

type Entry = {
  welded: WeldedMesh;
  refcount: number;
  evicted: boolean;
};

const DEFAULT_CAPACITY = 5;
let capacity = DEFAULT_CAPACITY;
const live = new Map<string, Entry>();
const detached = new Map<string, Entry>();

function evictLru() {
  while (live.size > capacity) {
    const oldest = live.keys().next();
    if (oldest.done === true) break;
    const url = oldest.value;
    const entry = live.get(url);
    if (entry === undefined) break;
    live.delete(url);
    entry.evicted = true;
    if (entry.refcount > 0) detached.set(url, entry);
    // No GPU dispose: WeldedMesh is plain typed-array data.
  }
}

export const weldCache = {
  put(key: string, welded: WeldedMesh): void {
    const existing = live.get(key) ?? detached.get(key);
    if (existing !== undefined) {
      live.delete(key);
      detached.delete(key);
    }
    const entry: Entry = { welded, refcount: 0, evicted: false };
    live.set(key, entry);
    evictLru();
  },

  acquire(key: string): WeldedMesh | undefined {
    const entry = live.get(key) ?? detached.get(key);
    if (entry === undefined) return undefined;
    entry.refcount += 1;
    if (live.has(key)) {
      live.delete(key);
      live.set(key, entry);
    }
    return entry.welded;
  },

  release(key: string): void {
    const entry = live.get(key) ?? detached.get(key);
    if (entry === undefined) return;
    entry.refcount = Math.max(0, entry.refcount - 1);
    if (entry.refcount === 0 && entry.evicted) detached.delete(key);
  },

  has(key: string): boolean {
    return live.has(key) || detached.has(key);
  },

  setCapacityForTests(n: number): void {
    capacity = n;
    evictLru();
  },
};

export function _resetWeldCacheForTests(): void {
  live.clear();
  detached.clear();
  capacity = DEFAULT_CAPACITY;
}
