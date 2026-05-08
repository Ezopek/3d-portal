import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelFileRead } from "@/lib/api-types";

interface Vars {
  fileId: string;
  selected: boolean;
}

export function useSetFileRenderSelection(modelId: string) {
  const qc = useQueryClient();
  return useMutation<ModelFileRead, Error, Vars>({
    mutationFn: ({ fileId, selected }) =>
      api<ModelFileRead>(
        `/admin/models/${modelId}/files/${fileId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ selected_for_render: selected }),
        },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "files", modelId] });
    },
  });
}
