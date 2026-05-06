import type { BufferGeometry } from "three";

type Entry = {
  geometry: BufferGeometry;
  refcount: number;
  evicted: boolean; // true once removed from `live`, but kept alive by subscribers
};

const DEFAULT_CAPACITY = 5;

let capacity = DEFAULT_CAPACITY;
const live = new Map<string, Entry>(); // LRU: insertion order = recency
const detached = new Map<string, Entry>(); // evicted but still has refcount > 0

function touch(url: string, entry: Entry) {
  live.delete(url);
  live.set(url, entry);
}

function maybeDisposeDetached(url: string, entry: Entry) {
  if (entry.refcount === 0 && entry.evicted) {
    entry.geometry.dispose();
    detached.delete(url);
  }
}

function evictLru() {
  while (live.size > capacity) {
    const oldest = live.keys().next();
    if (oldest.done === true) break;
    const url = oldest.value;
    const entry = live.get(url);
    if (entry === undefined) break;
    live.delete(url);
    entry.evicted = true;
    if (entry.refcount > 0) {
      detached.set(url, entry);
    } else {
      entry.geometry.dispose();
    }
  }
}

export const stlCache = {
  put(url: string, geometry: BufferGeometry): void {
    const existing = live.get(url) ?? detached.get(url);
    if (existing !== undefined) {
      live.delete(url);
      detached.delete(url);
      if (existing.refcount === 0) existing.geometry.dispose();
      else existing.evicted = true;
      if (existing.refcount > 0) detached.set(url, existing);
    }
    const entry: Entry = { geometry, refcount: 0, evicted: false };
    live.set(url, entry);
    evictLru();
  },

  peek(url: string): BufferGeometry | undefined {
    const entry = live.get(url);
    if (entry === undefined) return undefined;
    touch(url, entry);
    return entry.geometry;
  },

  acquire(url: string): BufferGeometry | undefined {
    const entry = live.get(url) ?? detached.get(url);
    if (entry === undefined) return undefined;
    entry.refcount += 1;
    if (live.has(url)) touch(url, entry);
    return entry.geometry;
  },

  release(url: string): void {
    const entry = live.get(url) ?? detached.get(url);
    if (entry === undefined) return;
    entry.refcount = Math.max(0, entry.refcount - 1);
    maybeDisposeDetached(url, entry);
  },

  clear(): void {
    for (const [, entry] of live) entry.geometry.dispose();
    for (const [, entry] of detached) entry.geometry.dispose();
    live.clear();
    detached.clear();
  },

  setCapacityForTests(n: number): void {
    capacity = n;
    evictLru();
  },
};

export function _resetStlCacheForTests(): void {
  stlCache.clear();
  capacity = DEFAULT_CAPACITY;
}
