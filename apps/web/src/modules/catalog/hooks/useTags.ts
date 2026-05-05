import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagRead } from "@/lib/api-types";

const DEFAULT_LIMIT = 50;

export function useTags(q?: string) {
  const params = new URLSearchParams();
  if (q !== undefined && q.length > 0) params.set("q", q);
  params.set("limit", String(DEFAULT_LIMIT));
  const path = `/tags?${params.toString()}`;
  return useQuery<TagRead[]>({
    queryKey: ["sot", "tags", q ?? ""],
    queryFn: () => api<TagRead[]>(path),
    staleTime: 5 * 60 * 1000,
  });
}
