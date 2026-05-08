import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail, ModelStatus } from "@/lib/api-types";

export interface ModelPatch {
  status?: ModelStatus;
  rating?: number | null;
  name_en?: string;
  name_pl?: string | null;
  category_id?: string;
  source?: string;
}

export function useUpdateModel(modelId: string) {
  const qc = useQueryClient();
  return useMutation<ModelDetail, Error, ModelPatch>({
    mutationFn: (patch) =>
      api<ModelDetail>(
        `/admin/models/${modelId}`,
        { method: "PATCH", body: JSON.stringify(patch) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}
