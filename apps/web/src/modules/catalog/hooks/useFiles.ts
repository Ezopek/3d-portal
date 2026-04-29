import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

interface FilesResponse { files: string[] }

export function useFiles(id: string) {
  return useQuery<FilesResponse>({
    queryKey: ["catalog", "models", id, "files"],
    queryFn: () => api<FilesResponse>(`/catalog/models/${id}/files`),
  });
}
