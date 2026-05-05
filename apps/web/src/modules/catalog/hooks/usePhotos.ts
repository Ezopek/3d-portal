import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FileListResponse, ModelFileRead } from "@/lib/api-types";

function isPhoto(f: ModelFileRead): boolean {
  return f.kind === "image" || f.kind === "print";
}

function sortByPosition(a: ModelFileRead, b: ModelFileRead): number {
  // NULLS LAST: fall back to created_at if both null, otherwise a non-null wins.
  if (a.position !== null && b.position !== null) return a.position - b.position;
  if (a.position !== null) return -1;
  if (b.position !== null) return 1;
  return a.created_at.localeCompare(b.created_at);
}

export function usePhotos(modelId: string) {
  return useQuery<ModelFileRead[]>({
    queryKey: ["sot", "photos", modelId],
    queryFn: async () => {
      const res = await api<FileListResponse>(`/models/${modelId}/files`);
      return res.items.filter(isPhoto).sort(sortByPosition);
    },
    staleTime: 30 * 1000,
  });
}
