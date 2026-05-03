import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

interface FilesResponse { files: string[] }

export type FilesKind = "all" | "printable";

export function useFiles(id: string, opts?: { kind?: FilesKind }) {
  const kind: FilesKind = opts?.kind ?? "all";
  return useQuery<FilesResponse>({
    queryKey: ["catalog", "models", id, "files", kind],
    queryFn: () => api<FilesResponse>(`/catalog/models/${id}/files?kind=${kind}`),
  });
}
