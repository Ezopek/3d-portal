import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FileListResponse, ModelFileKind } from "@/lib/api-types";

export type FilesKind = ModelFileKind | null;

export function useFiles(modelId: string, opts?: { kind?: FilesKind }) {
  const kind: FilesKind = opts?.kind === undefined ? "stl" : opts.kind;
  const path =
    kind === null ? `/models/${modelId}/files` : `/models/${modelId}/files?kind=${kind}`;
  return useQuery<FileListResponse>({
    queryKey: ["sot", "files", modelId, kind],
    queryFn: () => api<FileListResponse>(path),
    staleTime: 30 * 1000,
  });
}
