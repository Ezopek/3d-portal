import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useDeleteModel(modelId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, { hard?: boolean }>({
    mutationFn: ({ hard = false }) =>
      api<void>(
        `/admin/models/${modelId}${hard ? "?hard=true" : ""}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}
