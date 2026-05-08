import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ModelFileRead } from "@/lib/api-types";

export interface UploadVars {
  file: File;
  kind: "image" | "print" | "stl" | "source" | "archive_3mf";
}

export function useUploadFile(modelId: string) {
  const qc = useQueryClient();
  return useMutation<ModelFileRead, Error, UploadVars>({
    mutationFn: async ({ file, kind }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("kind", kind);
      const headers = new Headers();
      headers.set("X-Portal-Client", "web");
      const res = await fetch(`/api/admin/models/${modelId}/files`, {
        method: "POST",
        body: form,
        headers,
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`upload failed: ${res.status}`);
      }
      return (await res.json()) as ModelFileRead;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "photos", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "files", modelId] });
    },
  });
}
