import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { CategoryTree } from "@/lib/api-types";

export function useCategoriesTree() {
  return useQuery<CategoryTree>({
    queryKey: ["sot", "categories"],
    queryFn: () => api<CategoryTree>("/categories"),
    staleTime: 5 * 60 * 1000,
  });
}
