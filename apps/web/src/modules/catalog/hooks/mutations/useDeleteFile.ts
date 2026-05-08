import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useDeleteFile(modelId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (fileId) =>
      api<void>(
        `/admin/models/${modelId}/files/${fileId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "photos", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "files", modelId] });
    },
  });
}
