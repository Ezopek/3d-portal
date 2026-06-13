# Story 37.1: Portal UI — delete STL/source/3MF files from a model

Status: backlog

<!--
  Source: operator queue request 2026-06-14 — "Nie mogę z poziomu portalu usunąć plików STL z modelu... Nie ma takiego przycisku..."
  Backlog capture only. Not authorized for implementation until explicit dev-go.
-->

## Story

As an **admin/operator managing a catalog model**,
I want **a visible delete action for model files in the Files/STL tab**,
so that **I can remove an uploaded STL/source/3MF from the portal without leaving the model page or using API/manual DB workarounds**.

## Current-state note

Backend/file-delete plumbing already exists for admin files:

- API: `DELETE /api/admin/models/{model_id}/files/{file_id}`.
- Frontend hook: `useDeleteFile(modelId)`.
- Existing UI usage: `PhotosTab` already shows a `Trash2` delete action with confirmation.

The gap is the **Files tab UI** (`apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`): STL/source/3MF rows have upload/download/render/estimate affordances, but no delete button/confirmation.

## Acceptance sketch

- Add a delete affordance for file rows shown in `FilesTab` for at least `stl`; prefer shared behavior for visible file kinds `stl`, `source`, and `archive_3mf` unless product decides to limit the scope.
- Use the existing `useDeleteFile(modelId)` mutation; do not introduce a new backend endpoint unless tests reveal the existing contract is insufficient.
- Show a confirmation dialog before deletion, matching the Photos tab safety pattern.
- After successful deletion, the model detail/files queries are invalidated and the deleted file disappears from the row list / 3D viewer selector.
- If the deleted STL was selected for render or active in the viewer, the UI must not keep a stale selected file ID; it should gracefully fall back to another STL or the empty state.
- Preserve existing backend semantics: 204 success, 404 cross-model/missing file, storage/thumbnail sidecar cleanup handled server-side.
- Keep role/auth behavior admin-scoped if the existing endpoint remains admin-only; do not accidentally expose delete to normal members.
- Add tests for: button visible for STL row, confirmation required, mutation URL/method, successful removal/refetch behavior, and selected-STL fallback/empty state.
- Add/adjust i18n keys in both `en.json` and `pl.json`; avoid hard-coded delete copy.
- Visual check/baseline for Files tab with at least one STL row and delete affordance.

## Likely files

- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx`
- `apps/web/src/modules/catalog/hooks/mutations/useDeleteFile.ts` (likely reuse only)
- `apps/web/src/i18n/en.json`
- `apps/web/src/i18n/pl.json`
- Existing backend tests around `apps/api/tests/test_sot_admin_files.py` only if a backend gap is discovered.

## Notes / risks

- Deleting a file that backs current estimates may leave existing estimate records on disk; this story is UI deletion only and should not silently purge estimate history unless a separate backend/data-retention decision is made.
- Check whether deleting the last STL should block, warn, or allow empty-STL state. Default backlog assumption: allow delete with confirmation and render empty state honestly.
- If 36.3 member offer picker lands first, ensure the picker/estimate display tolerates the selected STL disappearing after delete/refetch.

## Change Log

- 2026-06-14 — captured from operator queue request; status `backlog`.
