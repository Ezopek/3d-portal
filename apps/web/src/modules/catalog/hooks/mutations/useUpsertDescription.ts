import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { NoteRead } from "@/lib/api-types";

export interface UpsertDescriptionInput {
  modelId: string;
  existingId: string | null;
  // Initiative 10 Story 16.2 revised (operator scope correction 2026-05-22):
  // bilingual editor — `body_pl` + `body_en` are first-class, `body` stays
  // populated as a legacy mirror (server-side mirrors body→body_en in
  // update_note when only body is provided per Story 16.1 P1 fix-up).
  body_pl: string;
  body_en: string;
}

export function useUpsertDescription() {
  const qc = useQueryClient();
  return useMutation<NoteRead, Error, UpsertDescriptionInput>({
    mutationFn: ({ modelId, existingId, body_pl, body_en }) => {
      // The legacy `body` field stays populated for backward compat —
      // prefer body_en when available, fall back to body_pl, fall back to
      // empty (rejected by Pydantic min_length=1, but the form prevents
      // double-empty submit via canSubmit gating).
      const legacyBody = body_en.trim() !== "" ? body_en : body_pl;
      const payload: Record<string, unknown> = {
        body: legacyBody,
        body_pl: body_pl.trim() === "" ? null : body_pl,
        body_en: body_en.trim() === "" ? null : body_en,
      };
      if (existingId === null) {
        return api<NoteRead>(`/admin/models/${modelId}/notes`, {
          method: "POST",
          body: JSON.stringify({ kind: "description", ...payload }),
        });
      }
      return api<NoteRead>(`/admin/notes/${existingId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", vars.modelId] });
    },
  });
}
