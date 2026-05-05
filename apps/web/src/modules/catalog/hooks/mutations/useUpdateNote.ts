import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { NoteKind, NoteRead } from "@/lib/api-types";

export interface UpdateNoteInput {
  kind?: NoteKind;
  body?: string;
}

export function useUpdateNote(modelId: string, noteId: string) {
  const qc = useQueryClient();
  return useMutation<NoteRead, Error, UpdateNoteInput>({
    mutationFn: (patch) =>
      api<NoteRead>(
        `/admin/notes/${noteId}`,
        { method: "PATCH", body: JSON.stringify(patch) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
