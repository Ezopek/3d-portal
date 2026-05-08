import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface TriggerRenderInput {
  selected_stl_file_ids: string[];
}

export interface TriggerRenderResponse {
  status: "queued";
  status_key: string;
}

export function useTriggerRender(modelId: string) {
  const qc = useQueryClient();
  return useMutation<TriggerRenderResponse, Error, TriggerRenderInput>({
    mutationFn: (input) =>
      api<TriggerRenderResponse>(
        `/admin/models/${modelId}/render`,
        { method: "POST", body: JSON.stringify(input) },
      ),
    onSuccess: () => {
      // Worker writes new ModelFile rows + updates thumbnail; FE doesn't know
      // exactly when it'll finish, but we can invalidate aggressively so the
      // user sees fresh data as soon as the next refetch hits.
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "photos", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}
