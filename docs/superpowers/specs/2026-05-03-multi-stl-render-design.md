# Multi-STL render & admin selection — design

**Status:** Draft, awaiting user review.
**Date:** 2026-05-03.
**Owner:** Michał (single-developer repo).
**Related code:** `workers/render/render/worker.py`, `workers/render/render/trimesh_render.py`, `apps/api/app/modules/catalog/service.py`, `apps/api/app/modules/catalog/router.py`, `apps/api/app/modules/admin/router.py`, `apps/api/app/core/db/models.py`, `apps/web/src/modules/catalog/components/FileList.tsx`, `apps/web/src/modules/catalog/components/ModelDetailTabs.tsx`, `apps/web/src/modules/catalog/hooks/useFiles.ts`.

## 1. Goal

When a model directory contains more than one STL, the current renderer picks `stls[0]` (alphabetical first) and renders four views of just that one file. The resulting card thumbnail often fails to convey what the model is or how the parts relate. This design lets an admin pick which STLs participate in the render. When the admin selects two or more, the worker bin-packs them on the XY plane (à la Orca Slicer auto-arrange) and renders the four views of the combined scene. The default behaviour stays identical to today, so no existing renders are silently rebuilt at deploy time.

The same admin workflow lives in a tightened "Model files" tab that shows only `.stl` (today's tab also lists images, PDFs, README files — clutter that is either already in the carousel or irrelevant in the catalog context).

## 2. Non-goals

- Interactive 3D viewer in the model detail page (separate, larger feature).
- Per-mesh colouring in the render (single grey, as today; can be added later).
- Heuristic detection of "variant" STL files (e.g. `_v2`, `_scaled`) — the admin decides manually.
- Consolidation with the existing `ThumbnailOverride` mechanism (different intent: override = "use this image instead of a render"; selection = "render these files"). Both stay independent.
- Server-side cancellation of in-flight renders when selection changes (last-write-wins is acceptable).
- Slicer-grade physics or collision avoidance beyond axis-aligned bounding-box packing.

## 3. UX summary

### Tab rename and content tightening

`catalog.tabs.files` becomes `catalog.tabs.modelFiles` ("Pliki modelu" / "Model files"). The list now only shows `.stl` files. Images live in the carousel (and can be saved via browser context menu); other files (PDFs, txts, READMEs) are noise in the catalog browsing context.

### Admin row (in the Model files tab)

```
[ ☑ ]  files/dragon-body.stl                       [Download]
[ ☐ ]  files/dragon-tail.stl     [auto]            [Download]
[ ☐ ]  files/dragon-egg.stl                        [Download]

  Selected: 1                            [Apply & re-render]
```

- Admin sees a checkbox per `.stl` row.
- A subtle `auto` badge marks the file the renderer falls back to (alphabetical first) **only** when the saved selection is empty.
- A status line below the list summarises the pending state: `Selected: 0 (default)`, `Selected: 1`, `Selected: N → group render`.
- `Apply & re-render` is disabled when there are no pending changes.

### Member / share view

Same tab, no checkboxes, no badges, no Apply button. Just the list of `.stl` files and download links. Identical to today's tab content (filtered to STL only).

### Selection semantics

A single concept: a set of relative paths.

| Saved set size | Worker behaviour                                                        |
|----------------|--------------------------------------------------------------------------|
| 0              | Fallback to `stls[0]` alphabetically — identical to today.               |
| 1              | Render that one file (same `_render_mesh_views` path as today).          |
| ≥ 2            | Bin-pack on XY plane, combine into one scene, render the four views.     |

There is no separate `mode` flag — the count carries the meaning. A clear of selection is the same path as setting it to an empty set.

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/api                                                                 │
│  ├─ core/db/models.py            +RenderSelection table                  │
│  ├─ modules/catalog/             +render_selection.py (repo)             │
│  ├─ modules/catalog/service.py    list_files(kind: 'all'|'printable')    │
│  ├─ modules/catalog/router.py     /files endpoint takes ?kind=...        │
│  └─ modules/admin/router.py      +PUT/GET /models/{id}/render-selection  │
│                                   refresh-catalog purges orphan rows     │
│                                   trigger_render passes selected_paths   │
└──────────────────────────────────────────────────────────────────────────┘
                                 │ arq job kwargs
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ workers/render                                                           │
│  ├─ worker.py            render_model(model_id, *, selected_paths=None)  │
│  └─ trimesh_render.py    render_views(stl_paths: list[Path], ...)        │
│                          + _pack_meshes_xy(...) — trimesh bin-packing    │
└──────────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ HTTP
                                 │
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/web                                                                 │
│  ├─ modules/catalog/hooks/useFiles.ts          +kind: 'all'|'printable'  │
│  ├─ modules/catalog/hooks/useRenderSelection.ts (new)                    │
│  ├─ modules/catalog/components/FileList.tsx    rebuild: admin checkboxes │
│  └─ modules/catalog/components/ModelDetailTabs.tsx  tab rename           │
└──────────────────────────────────────────────────────────────────────────┘
```

The render worker stays stateless: it never touches the API DB. The selection is passed as an arq job kwarg, computed on the API side at enqueue time. This preserves the current isolation boundary — the worker has no `sqlmodel`/`sqlalchemy` dependency.

## 5. Data model

New table in `apps/api/app/core/db/models.py`, mirroring `ThumbnailOverride`:

```python
class RenderSelection(SQLModel, table=True):
    __tablename__ = "renderselection"

    model_id: str = Field(primary_key=True)
    selected_paths: str  # JSON-encoded list[str], paths relative to the model folder
    set_by_user_id: int = Field(foreign_key="user.id")
    set_at: datetime.datetime = Field(default_factory=_now_utc)
```

One row per model holding a JSON-encoded list of selected paths. Rationale for one-row-per-model rather than `RenderSelectionFile(model_id, path)` 1:N: reads are always full-set, updates are always full replacement, no query indexes by path. Single-row keeps the model trivial and avoids transactional `DELETE+INSERT` churn on every Apply.

Migration: empty table on first deploy → all models in fallback → identical behaviour to today. Schema creation follows the existing `metadata.create_all` pattern used by the other `SQLModel` tables; no data migration needed.

### Repository

`apps/api/app/modules/catalog/render_selection.py` — same shape as `thumbnail_overrides.py`:

```python
class RenderSelectionRepo:
    def get(self, model_id: str) -> list[str]: ...        # [] when no row
    def get_all(self) -> dict[str, list[str]]: ...
    def set(self, *, model_id: str, paths: list[str], user_id: int) -> None: ...
    def clear(self, model_id: str) -> bool: ...
    def purge_orphans(self, *, exists: Callable[[str, str], bool]) -> list[tuple[str, str]]: ...
```

`purge_orphans` removes paths that no longer resolve to a file. If the resulting set becomes empty, the row is deleted (so the worker falls back to `stls[0]`).

Wired in startup as `request.app.state.render_selection`, mirroring `request.app.state.thumbnail_overrides`.

## 6. API

### `GET /api/catalog/models/{id}/files` — extended

```python
@router.get("/models/{model_id}/files")
def list_files(
    model_id: str,
    request: Request,
    kind: Literal["all", "printable"] = "all",
) -> dict[str, list[str]]:
```

- `kind=all` (default) — backward-compatible: `useGallery`, `CatalogDetail.firstStl`, `hasPrintableFiles`, and `galleryCandidates` keep working unchanged.
- `kind=printable` — returns only files whose suffix is `.stl` (case-insensitive). Used by the new `FileList`.

`CatalogService.list_files` gains an optional filter parameter; the regex/match lives in the service layer, not in the router.

### `GET /api/admin/models/{id}/render-selection`

Response:

```json
{
  "paths": ["files/part-a.stl", "files/part-b.stl"],
  "available_stls": ["files/part-a.stl", "files/part-b.stl", "files/variant.stl"]
}
```

`available_stls` is bundled into the same response so the admin UI does not need to make two calls. Empty `paths` → fallback to `stls[0]`; the UI displays the `auto` badge accordingly.

### `PUT /api/admin/models/{id}/render-selection`

Body: `{ "paths": [<relative .stl paths>] }`

Validation, in order, each failing fast with a distinct error code:

1. Model exists → 404 `model_not_found`.
2. `len(paths) <= 16` → 400 `too_many_files` (soft cap; above 16 the packed render is unreadable).
3. Each path matches `^[^/.][^/]*(/[^/.][^/]*)*\.stl$` (case-insensitive on `.stl`) → 400 `invalid_path`. Disallows segments starting with `.` (no `..`, no hidden), no leading `/`, no `//`, must end with `.stl`.
4. Each path resolves (`(model_dir / rel).resolve().relative_to(model_dir.resolve())`) → 400 `invalid_path`. Defence-in-depth against symlink escapes.
5. Each path is an existing file → 400 `file_not_found`.

Effects on success:

1. Repo `set(...)` (or `clear(...)` when `paths == []`).
2. Audit event `render_selection.set` or `render_selection.cleared`.
3. **No-op detection:** if the new set is equal to the currently-stored set as an unordered set (i.e. `set(new) == set(old)`), return `204` without enqueueing a render. Stored ordering is irrelevant.
4. Otherwise enqueue `render_model(model_id, selected_paths=paths_or_None)`.
5. Return `204 No Content`.

Routing placement: both `GET` and `PUT` extend `apps/api/app/modules/admin/router.py` (alongside `set_thumbnail` / `clear_thumbnail`). Same admin-only domain, no value in a separate router file.

### `refresh-catalog` extension

After the existing `thumbnail_overrides.purge_orphans(...)` call, do the same for `render_selection.purge_orphans(...)`. Each purged path is recorded as a `render_selection.orphan_purged` audit event with `{model_id, relative_path}`.

### Job-enqueue sites

Three places enqueue `render_model`:

- `admin/router.py: refresh_catalog` — for each missing render, read selection first.
- `admin/router.py: trigger_render` — same.
- New `set_render_selection` endpoint — uses the just-validated paths directly.

In all three cases the call shape is:

```python
selection = request.app.state.render_selection.get(model_id)
await request.app.state.arq.enqueue_job(
    "render_model",
    model_id,
    selected_paths=selection or None,  # None reads cleaner than [] in worker logs
)
```

## 7. Worker

`workers/render/render/worker.py` `render_model` signature gains a kwarg:

```python
async def render_model(
    ctx: dict[str, Any],
    model_id: str,
    *,
    selected_paths: list[str] | None = None,
) -> dict[str, str]:
```

Backward-safe: in-flight jobs from before the deploy reach the new worker without the kwarg → `selected_paths=None` → today's behaviour.

Worker validation logic:

```python
all_stls = sorted(p for p in model_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".stl")
if not all_stls:
    return {"status": "failed", "reason": "no STL files in model directory"}

if selected_paths:
    chosen: list[Path] = []
    missing: list[str] = []
    for rel in selected_paths:
        candidate = (model_dir / rel).resolve()
        try:
            candidate.relative_to(model_dir.resolve())
        except ValueError:
            missing.append(rel)
            continue
        if candidate.is_file() and candidate.suffix.lower() == ".stl":
            chosen.append(candidate)
        else:
            missing.append(rel)
    if missing:
        _log.warning(
            "render: skipping missing/invalid STLs",
            extra={"model_id": model_id, "missing": missing},
        )
    if not chosen:
        chosen = [all_stls[0]]  # all selected paths gone — silent fallback
else:
    chosen = [all_stls[0]]

render_views(stl_paths=chosen, output_dir=out_dir, size=size)
```

Structured-log fields per render: `model_id`, `selected_count`, `chosen_count`, `mode` (`"single"` or `"group"`), `missing_count`. After success: `duration_ms`. Sentry captures any unexpected exception (existing pattern).

## 8. Renderer (`trimesh_render.py`)

Refactor the public function from a single path to a list, and split the rendering core out:

```python
def render_views(*, stl_paths: list[Path], output_dir: Path, size: int = 768) -> dict[str, Path]:
    if len(stl_paths) == 1:
        mesh = trimesh.load(stl_paths[0], force="mesh")
    else:
        mesh = _pack_meshes_xy(stl_paths, spacing_mm=5.0)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Not a triangle mesh: {stl_paths}")
    return _render_mesh_views(mesh, output_dir, size)


def _pack_meshes_xy(stl_paths: list[Path], spacing_mm: float) -> trimesh.Trimesh:
    placed: list[trimesh.Trimesh] = []
    extents_xy: list[tuple[float, float]] = []
    for path in stl_paths:
        m = trimesh.load(path, force="mesh")
        if not isinstance(m, trimesh.Trimesh):
            continue  # silently skip non-mesh STLs (e.g. multi-geometry Scenes)
        m = m.copy()
        m.apply_translation(-m.bounds[0])  # bbox.min → origin (bottom on z=0)
        placed.append(m)
        extents_xy.append((float(m.extents[0] + spacing_mm), float(m.extents[1] + spacing_mm)))

    if not placed:
        raise ValueError("no usable triangle meshes for packing")

    transforms_xy, _packed_size = trimesh.path.packing.rectangles(extents_xy)

    for mesh, (tx, ty) in zip(placed, transforms_xy, strict=True):
        mesh.apply_translation([tx, ty, 0.0])

    return trimesh.util.concatenate(placed)


def _render_mesh_views(mesh: trimesh.Trimesh, output_dir: Path, size: int) -> dict[str, Path]:
    # existing matplotlib render code — unchanged: centre, scale to 1.0, four views.
    ...
```

Centring (`apply_translation(-mesh.centroid)`) and scaling (`apply_scale(1.0 / max(mesh.extents))`) are applied **after** packing/concatenation, so the whole packed scene fits the matplotlib `[-0.6, 0.6]` window with proportions between parts preserved.

### Implementation notes

- `trimesh.path.packing.rectangles` exact signature must be verified against the installed trimesh version during implementation. The conceptual contract (extents in → translations out) is the design commitment.
- `spacing_mm = 5.0` is arbitrary but matches Orca-style plate margins. Because the whole scene is rescaled afterwards, the absolute value only affects relative spacing in the final image.
- Scene-typed STLs (rare, when one file holds multiple disjoint geometries) are silently skipped during packing. Documenting this is enough; rebuilding scenes into individual meshes is YAGNI.

## 9. Frontend

### `useFiles` — extended

```ts
export function useFiles(modelId: string, opts?: { kind?: 'all' | 'printable' }) {
  const kind = opts?.kind ?? 'all';
  return useQuery({
    queryKey: ['files', modelId, kind],
    queryFn: () => api<FilesResponse>(`/catalog/models/${modelId}/files?kind=${kind}`),
  });
}
```

Default `kind=all` keeps `useGallery`, `CatalogDetail`, and `galleryCandidates` working unchanged.

### `useRenderSelection` (new hook)

```ts
export function useRenderSelection(modelId: string, opts: { enabled: boolean }) {
  return useQuery({
    queryKey: ['renderSelection', modelId],
    queryFn: () => api<RenderSelectionResponse>(`/admin/models/${modelId}/render-selection`),
    enabled: opts.enabled,  // gate on isAdmin
  });
}

export function useSetRenderSelection(modelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (paths: string[]) =>
      api(`/admin/models/${modelId}/render-selection`, {
        method: 'PUT',
        body: JSON.stringify({ paths }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['renderSelection', modelId] });
      qc.invalidateQueries({ queryKey: ['files', modelId] });
      qc.invalidateQueries({ queryKey: ['model', modelId] });
    },
  });
}
```

### `FileList` rebuild

Outline (full TSX in implementation phase):

- Reads `useFiles(modelId, { kind: 'printable' })` for the row list.
- Reads `useRenderSelection(modelId, { enabled: isAdmin })`.
- Local state `pending: Set<string> | null`. `null` → no edits, show DB state. `Set` → user has toggled, Apply enabled.
- For each file row:
  - Member view: just name + Download link.
  - Admin view: checkbox (left), name + optional `auto` badge (centre), Download link (right).
- `auto` badge appears on the alphabetically-first file **only** when the saved set is empty.
- Status line + Apply button below the list. Apply is disabled when no pending changes or when `pending.size > 16`.
- On Apply: optimistic update of the `renderSelection` query, mutation fires, success toast `catalog.renderSelection.applied`, error toast surfaces the API message and rolls back `pending`.

### Other touched FE files

- `ModelDetailTabs.tsx` — change tab label to `t('catalog.tabs.modelFiles')`. The `<FileList>` content is unchanged (it owns its `kind` choice).
- `apps/web/src/locales/en.json` and `pl.json`:
  - **Add** `catalog.tabs.modelFiles`, `catalog.renderSelection.{apply, applied, errorTooMany, badgeAuto, statusDefault, statusSingle, statusGroup}`.
  - **Remove** `catalog.tabs.files` (only consumer was `ModelDetailTabs`).

## 10. Edge cases

- **Selected file disappears from disk.** Three layers: API rejects on PUT; `refresh-catalog` purges silently with audit; worker skips at job time with a log warning and falls back to `stls[0]` if everything is gone.
- **Selected STL is a multi-geometry Scene.** `trimesh.load(force="mesh")` may return a `Scene`. Packing skips it silently; if every selected file is a Scene, the worker raises `no usable triangle meshes for packing` → job result `failed`.
- **Race: admin Applies during an in-flight render.** Both jobs run; the second overwrites the first's PNGs. Acceptable — renders are idempotent and last-write-wins reflects the most recent intent. No cancellation API.
- **Concurrent worker writes to `renders/{model_id}/`.** The render worker runs as a single process today; arq's per-function queue with one consumer means jobs serialise. If concurrency is ever raised, set `max_jobs_per_function: 1` in `WorkerSettings` to preserve the invariant. Flagged for verification at implementation time.
- **Path traversal in PUT body.** Defended by regex + `resolve().relative_to(...)` (defence-in-depth).
- **Soft cap (16) bypass.** Enforced by API regardless of UI state.
- **First deploy.** Empty `RenderSelection` table → all models in fallback → no automatic re-render of existing thumbnails.

## 11. Observability

- Worker logs (structured JSON): `render: started`, `render: done`, `render: failed`, each with `model_id`, `mode`, `selected_count`, `chosen_count`, `missing_count`, and `duration_ms` on completion.
- Sentry captures unexpected packing exceptions (`trimesh.path.packing` API drift, `concatenate` failures).
- Audit events: `render_selection.set`, `render_selection.cleared`, `render_selection.orphan_purged` (in addition to existing `render.triggered`, `thumbnail.*`).

## 12. Testing

### Backend (TDD)

`workers/render/tests/test_trimesh_render.py` (new):

- `test_render_views_single_path_unchanged` — single-path call still produces front/side/top/iso.
- `test_pack_meshes_xy_combines_and_packs` — two synthetic boxes; combined mesh's XY extent ≥ 2 × box-edge + spacing.
- `test_pack_meshes_xy_skips_non_trimesh` — fixture loading as `Scene` is skipped, render proceeds with the rest.
- `test_pack_meshes_xy_all_skipped_raises` — every input is a Scene → `ValueError`.
- `test_render_views_multi_outputs_4_views` — multi-path call writes the four named PNGs.

`apps/api/tests/test_render_selection_repo.py` (new):

- `test_get_returns_empty_when_unset`
- `test_set_persists_paths` (round-trip JSON)
- `test_set_overrides_previous`
- `test_clear_removes_row`
- `test_purge_orphans_removes_dead_paths`
- `test_purge_orphans_clears_row_when_all_paths_dead`

`apps/api/tests/test_admin_render_selection_endpoint.py` (new):

- `test_unauthenticated_returns_401`, `test_member_returns_403`
- `test_set_selection_enqueues_render` (verify arq mock kwargs)
- `test_path_traversal_rejected`, `test_non_stl_rejected`, `test_missing_file_rejected`, `test_too_many_files_rejected_at_17`
- `test_setting_identical_set_does_not_enqueue` (no-op detection)
- `test_empty_paths_clears_selection`
- `test_get_returns_paths_and_available_stls`

`apps/api/tests/test_admin_refresh_catalog.py` (extension):

- `test_refresh_purges_orphan_render_selections`

`apps/api/tests/test_catalog_files_endpoint.py` (extension):

- `test_list_files_default_is_all_kind` (regression, backward compat)
- `test_list_files_printable_kind_returns_only_stl`
- `test_list_files_printable_kind_case_insensitive`

### Frontend (Vitest)

- `useFiles.test.ts` — `kind` parameter is part of the query key; different kinds = different cache entries.
- `FileList.test.tsx` (rewrite):
  - Member: rows render without checkboxes.
  - Admin: checkboxes visible, default `auto` badge on first file when selection is empty.
  - Toggle a checkbox → Apply enabled, status line updates.
  - Apply success → toast + invalidate.
  - Apply failure (e.g. mocked 400 too_many) → error toast + rollback pending.
  - 17 selected → Apply disabled + helper text.

### Visual regression (Playwright)

Update existing baseline:

- `model-detail-files-tab.png` — relabelled tab + STL-only list.

New baselines:

- `model-detail-files-tab-admin-default.png` — admin, empty selection, `auto` badge.
- `model-detail-files-tab-admin-pending.png` — admin with two boxes ticked, Apply enabled.
- `model-detail-files-tab-admin-applied.png` — clean state after Apply, two boxes saved.

The catalog card carousel snapshot does not need an update — its structure (four PNGs from `iso/front/side/top`) is unchanged; only the rendered pixels of `iso.png` & friends differ for models in group mode.

### Integration

`workers/render/tests/test_render_model_integration.py`:

- `test_render_model_with_selected_paths_renders_combined` — fixture model with two STLs, call worker entry-point with `selected_paths=[a, b]`, verify the four PNGs exist and are non-empty.
- `test_render_model_falls_back_when_all_selected_missing` — `selected_paths=[<nonexistent>]` → `chosen = [stls[0]]`, render succeeds.

### CI / lint

No new dependencies. `ruff check && ruff format --check && pytest` for backend; `npm run lint --max-warnings=0 && npm test && npm run test:visual` for frontend.

## 13. Rollout

1. Merge to `main` after standard review/visual-regression pass.
2. `infra/scripts/deploy.sh` per the standing instruction (auto-deploy after every code merge to `main`).
3. After deploy: empty `RenderSelection` table → no model is re-rendered. Verify by spot-checking a few model detail pages — tab shows STLs only, member view unchanged.
4. Smoke test: as admin, on a known multi-STL model, tick two boxes → Apply → wait ~1–2 min → reload → carousel should now show the packed render.
5. No data migration. No flag rollout. If something is wrong, revert is a single git revert + redeploy.

## 14. Open follow-ups (not blocking)

- Per-mesh colouring in group renders (currently single grey).
- Live render-status indicator next to the Apply button (today: admin reloads).
- Consolidating `ThumbnailOverride` + `RenderSelection` into a single "Card image" admin dialog if the two mechanisms feel redundant after some time in use.
- Rebuilding multi-geometry STL Scenes into individual meshes for packing (only if such files become common).
