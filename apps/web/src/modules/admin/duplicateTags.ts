import type { TagReadWithCount } from "@/lib/api-types";

// Story 46.3 — pure client-side duplicate-tag detection over the already-loaded
// `useTagGroups()` data. No new endpoint, no server-side similarity computation
// (see the frozen intent-contract's "Never" list in the spec).

// Ł/ł have no NFD decomposition (they aren't a base letter + combining diacritic
// in Unicode), so they need an explicit map before/independent of the NFD pass.
const POLISH_L_MAP: Record<string, string> = { ł: "l", Ł: "L" };

/**
 * Normalize a tag name field for similarity comparison: NFD-decompose + strip
 * combining diacritics, map ł/Ł → l/L, lowercase, trim, collapse internal
 * whitespace. Two fields that normalize identically (or within the
 * length-scaled Levenshtein threshold) are considered the same for clustering.
 */
export function normalizeTagText(input: string): string {
  const lMapped = input.replace(/[łŁ]/g, (ch) => POLISH_L_MAP[ch] ?? ch);
  // U+0300-U+036F is the Unicode "Combining Diacritical Marks" block that NFD
  // decomposition splits accented base letters into.
  const decomposed = lMapped.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return decomposed.toLowerCase().trim().replace(/\s+/g, " ");
}

/** Classic Levenshtein edit distance (insert/delete/substitute), O(len(a)*len(b)). */
export function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;

  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  let curr = new Array<number>(n + 1).fill(0);

  for (let i = 1; i <= m; i++) {
    curr[0] = i;
    for (let j = 1; j <= n; j++) {
      const prevRow = prev[j] ?? 0;
      const prevDiag = prev[j - 1] ?? 0;
      const currLeft = curr[j - 1] ?? 0;
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(prevRow + 1, currLeft + 1, prevDiag + cost);
    }
    [prev, curr] = [curr, prev];
  }
  return prev[n] ?? 0;
}

// Length-scaled Levenshtein threshold (Design Notes table): short normalized
// strings only cluster on an exact match, to avoid false positives like
// "PLA"/"ABS" (both length 3, distance 3).
function maxDistanceFor(length: number): number {
  if (length <= 4) return 0;
  if (length <= 8) return 1;
  return 2;
}

/** Whether two ALREADY-NORMALIZED, non-empty strings are similar enough to cluster. */
function fieldsSimilar(a: string, b: string): boolean {
  if (a === b) return true;
  const threshold = maxDistanceFor(Math.max(a.length, b.length));
  if (threshold === 0) return false; // already excluded exact-equality above
  return levenshtein(a, b) <= threshold;
}

/**
 * Two tags are "similar" if, for either language field independently (en-vs-en,
 * pl-vs-pl; only when both sides are non-empty), the normalized strings match
 * exactly or fall within the length-scaled Levenshtein threshold. Deliberately
 * never compares an en field against a pl field (out of scope per the intent
 * contract — no cross-language/semantic matching).
 */
function tagsSimilar(a: TagReadWithCount, b: TagReadWithCount): boolean {
  const aEn = normalizeTagText(a.name_en);
  const bEn = normalizeTagText(b.name_en);
  if (aEn !== "" && bEn !== "" && fieldsSimilar(aEn, bEn)) return true;

  const aPl = a.name_pl !== null ? normalizeTagText(a.name_pl) : "";
  const bPl = b.name_pl !== null ? normalizeTagText(b.name_pl) : "";
  if (aPl !== "" && bPl !== "" && fieldsSimilar(aPl, bPl)) return true;

  return false;
}

/**
 * Union-find clustering over pairwise `tagsSimilar` matches (transitive: if
 * A~B and B~C, all three land in one cluster even if A and C aren't directly
 * similar). Returns only clusters with >= 2 tags, sorted by (descending size,
 * then representative normalized name_en) for deterministic output.
 */
export function findDuplicateClusters(tags: TagReadWithCount[]): TagReadWithCount[][] {
  const parent = new Map<string, string>(tags.map((t) => [t.id, t.id]));

  function find(id: string): string {
    let root = id;
    while (true) {
      const next = parent.get(root);
      if (next === undefined || next === root) break;
      root = next;
    }
    // Path compression.
    let cur = id;
    while (cur !== root) {
      const next = parent.get(cur);
      parent.set(cur, root);
      if (next === undefined) break;
      cur = next;
    }
    return root;
  }

  function union(a: string, b: string) {
    const rootA = find(a);
    const rootB = find(b);
    if (rootA !== rootB) parent.set(rootA, rootB);
  }

  for (let i = 0; i < tags.length; i++) {
    const a = tags[i];
    if (a === undefined) continue;
    for (let j = i + 1; j < tags.length; j++) {
      const b = tags[j];
      if (b === undefined) continue;
      if (tagsSimilar(a, b)) union(a.id, b.id);
    }
  }

  const groups = new Map<string, TagReadWithCount[]>();
  for (const tag of tags) {
    const root = find(tag.id);
    const group = groups.get(root);
    if (group) {
      group.push(tag);
    } else {
      groups.set(root, [tag]);
    }
  }

  function representativeName(group: TagReadWithCount[]): string {
    // Deterministic regardless of insertion order: the alphabetically-first
    // normalized name_en among the cluster's members.
    let best = "";
    for (const tag of group) {
      const normalized = normalizeTagText(tag.name_en);
      if (best === "" || normalized < best) best = normalized;
    }
    return best;
  }

  return [...groups.values()]
    .filter((group) => group.length >= 2)
    .sort((x, y) => {
      if (y.length !== x.length) return y.length - x.length;
      return representativeName(x).localeCompare(representativeName(y));
    });
}
