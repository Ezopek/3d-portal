import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagRead } from "@/lib/api-types";

export interface CreateTagInput {
  slug: string;
  name_en: string;
  name_pl?: string | null;
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation<TagRead, Error, CreateTagInput>({
    mutationFn: (input) =>
      api<TagRead>(
        "/admin/tags",
        { method: "POST", body: JSON.stringify(input) },
        { authenticated: true },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tags"] });
    },
  });
}
