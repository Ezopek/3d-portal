export type SortKey = "recent" | "oldest" | "name_asc" | "name_desc" | "status";

export const SORT_OPTIONS: readonly { value: SortKey; labelKey: string }[] = [
  { value: "recent", labelKey: "catalog.sort.recent" },
  { value: "oldest", labelKey: "catalog.sort.oldest" },
  { value: "name_asc", labelKey: "catalog.sort.name_asc" },
  { value: "name_desc", labelKey: "catalog.sort.name_desc" },
  { value: "status", labelKey: "catalog.sort.status" },
];

export const SORT_KEYS: readonly SortKey[] = SORT_OPTIONS.map((o) => o.value);
