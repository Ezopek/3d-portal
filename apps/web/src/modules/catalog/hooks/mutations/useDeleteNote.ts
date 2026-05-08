import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useDeleteNote(modelId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (noteId) =>
      api<void>(
        `/admin/notes/${noteId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
