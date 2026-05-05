import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PrintRead } from "@/lib/api-types";

export interface CreatePrintInput {
  model_id: string;
  photo_file_id?: string | null;
  printed_at?: string | null;
  note?: string | null;
}

export function useCreatePrint(modelId: string) {
  const qc = useQueryClient();
  return useMutation<PrintRead, Error, CreatePrintInput>({
    mutationFn: (input) =>
      api<PrintRead>(
        "/admin/prints",
        { method: "POST", body: JSON.stringify(input) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
