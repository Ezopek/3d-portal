import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { NoteKind, NoteRead } from "@/lib/api-types";

export interface CreateNoteInput {
  model_id: string;
  kind: NoteKind;
  body: string;
}

export function useCreateNote(modelId: string) {
  const qc = useQueryClient();
  return useMutation<NoteRead, Error, CreateNoteInput>({
    mutationFn: (input) =>
      api<NoteRead>(
        "/admin/notes",
        { method: "POST", body: JSON.stringify(input) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
