import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ProfileLibraryBlock } from "@/lib/api-types";

export interface ImportProfileBlockVars {
  file: File;
  portal_label?: string;
}

/**
 * PROFILE-LIB-1 (AC-17) — the operator profile-block import mutation.
 *
 * Posts the multipart `{file, portal_label?}` through `api()` (which adds the CSRF header and
 * never stamps a JSON content-type on a `FormData` body). NO slot fields — the backend
 * derives the target tree from the classified profile type. On success it invalidates the
 * whole `["admin","profile-library"]` subtree so the list (and any per-type filter) refetch.
 *
 * Cache topology (per the story's enumeration): NO auto-retry on the write (NFR21-OBS-1
 * one-audit-event-per-import + admin-fails-closed); the admin re-submits explicitly. The list
 * is never optimistically inserted — it reconciles from the server.
 */
export function useImportProfileBlock() {
  const qc = useQueryClient();
  return useMutation<ProfileLibraryBlock, Error, ImportProfileBlockVars>({
    mutationFn: ({ file, portal_label }) => {
      const form = new FormData();
      form.append("file", file);
      if (portal_label) form.append("portal_label", portal_label);
      return api<ProfileLibraryBlock>("/admin/profiles/library", {
        method: "POST",
        body: form,
      });
    },
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-library"] });
    },
  });
}
