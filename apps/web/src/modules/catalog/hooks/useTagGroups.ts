import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagGroupsResponse } from "@/lib/api-types";

export function useTagGroups() {
  return useQuery<TagGroupsResponse>({
    queryKey: ["sot", "tag-groups"],
    queryFn: () => api<TagGroupsResponse>("/tag-groups"),
    staleTime: 5 * 60 * 1000,
  });
}
