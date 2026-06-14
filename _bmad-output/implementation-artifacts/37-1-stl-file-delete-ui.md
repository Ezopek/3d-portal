# Story 37.1: Portal UI — delete STL/source/3MF files from a model

Status: done

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


## Dev Agent Record

### Agent Model Used

Laura/Hermes controller implementation with strict TDD; Aider routine diff review via `laura-aider-review-diff`.

### Completion Notes List

- 2026-06-14 — Implemented on branch `feat/E37.1-stl-file-delete-ui`.
- RED evidence: `npm run test -- --run src/modules/catalog/components/tabs/FilesTab.test.tsx --reporter=verbose` failed on the new delete-affordance tests because no delete buttons existed.
- GREEN targeted evidence: `FilesTab.test.tsx` passed **26 tests**, including admin visibility for STL/source/3MF delete buttons, confirmation-before-delete, DELETE endpoint call, and expanded-STL state cleanup.
- Additional targeted evidence: i18n parity + `ConfirmDialog` + `useDeleteFile` tests passed **3 files / 5 tests**.
- Web evidence: `npm run typecheck`, `npm run lint -- --max-warnings=0`, and full Vitest passed **126 files / 660 tests**.
- Review evidence: `laura-aider-review-diff` returned `REQUEST_CHANGES` due a false-positive claim that `catalog.actions.delete` was missing. Controller verified the key exists in both `en.json` and `pl.json`, and the targeted i18n/ConfirmDialog tests passed. Non-blocking notes were accepted as UX trade-offs.
- Full gate evidence after visual baseline refresh: `.hermes/run-logs/check-all-20260614_033356-E37.1-after-baselines.log` — `infra/scripts/check-all.sh` passed **16/16**, including visual regression **472 passed / 24 skipped**.
- Scope held: reused existing `useDeleteFile(modelId)` and backend `DELETE /api/admin/models/{model_id}/files/{file_id}`; no backend/API change, no estimate data purge, no member exposure.

### File List

- `_bmad-output/implementation-artifacts/37-1-stl-file-delete-ui.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx`
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/*.png`
- `apps/web/tests/visual/__snapshots__/catalog-filestab-estimate.spec.ts/*.png`
- `apps/web/tests/visual/__snapshots__/share-member-enriched*.spec.ts/*.png`
