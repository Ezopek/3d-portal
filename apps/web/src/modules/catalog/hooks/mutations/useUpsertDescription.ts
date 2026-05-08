import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { NoteRead } from "@/lib/api-types";

export interface UpsertDescriptionInput {
  modelId: string;
  existingId: string | null;
  body: string;
}

export function useUpsertDescription() {
  const qc = useQueryClient();
  return useMutation<NoteRead, Error, UpsertDescriptionInput>({
    mutationFn: ({ modelId, existingId, body }) => {
      if (existingId === null) {
        return api<NoteRead>(
          "/admin/notes",
          {
            method: "POST",
            body: JSON.stringify({ model_id: modelId, kind: "description", body }),
          },
        );
      }
      return api<NoteRead>(
        `/admin/notes/${existingId}`,
        { method: "PATCH", body: JSON.stringify({ body }) },
      );
    },
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", vars.modelId] });
    },
  });
}
