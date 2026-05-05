import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useDeletePrint(modelId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (printId) =>
      api<void>(
        `/admin/prints/${printId}`,
        { method: "DELETE" },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
