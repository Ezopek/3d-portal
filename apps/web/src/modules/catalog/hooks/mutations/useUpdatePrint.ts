import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PrintRead } from "@/lib/api-types";

export interface UpdatePrintInput {
  photo_file_id?: string | null;
  printed_at?: string | null;
  note?: string | null;
}

export function useUpdatePrint(modelId: string, printId: string) {
  const qc = useQueryClient();
  return useMutation<PrintRead, Error, UpdatePrintInput>({
    mutationFn: (patch) =>
      api<PrintRead>(
        `/admin/prints/${printId}`,
        { method: "PATCH", body: JSON.stringify(patch) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
