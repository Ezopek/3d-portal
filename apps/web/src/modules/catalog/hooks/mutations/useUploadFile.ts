import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ModelFileRead } from "@/lib/api-types";
import { refreshAccessToken } from "@/lib/refresh";

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

      async function doUpload(): Promise<Response> {
        return fetch(`/api/admin/models/${modelId}/files`, {
          method: "POST",
          body: form,
          headers,
          credentials: "include",
        });
      }

      let res = await doUpload();
      if (res.status === 401) {
        const body = await res.clone().json().catch(() => ({}));
        const detail = (body as { detail?: string })?.detail;
        if (detail === "access_expired" || detail === "missing_access") {
          const ok = await refreshAccessToken();
          if (ok) res = await doUpload();
        }
      }
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
