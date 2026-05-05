import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";

export function useSetThumbnail(modelId: string) {
  const qc = useQueryClient();
  return useMutation<ModelDetail, Error, string | null>({
    mutationFn: (fileId) =>
      api<ModelDetail>(
        `/admin/models/${modelId}/thumbnail`,
        { method: "PUT", body: JSON.stringify({ file_id: fileId }) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models"] }); // catalog list refreshes
    },
  });
}
