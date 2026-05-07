# Legacy SoT Cleanup — Report

- **Date:** 2026-05-06
- **Commit:** `d92e551 chore(api): drop legacy file-based catalog and port share to SoT`
- **Scope:** remove every API surface and code path that still depended on the pre-SoT (file-based) catalog, port the remaining hybrid endpoint (`/api/share/{token}`) to SoT entity tables, drop the dead legacy DB tables, and bring docs in line.
- **Outcome:** clean deploy on `.190`. Alembic upgraded `0007 → 0008`. `/api/health` returns `0.1.0`.

## Background

The portal was originally a thin browser over a filesystem catalog: `_index/index.json` on a Windows-synced volume drove `/api/catalog/*`, `/api/files/*` served raw bytes from disk, thumbnails were path-overrides in a side table, and renders were keyed by 3-digit string IDs.

Slices 2A–2D + 3A–3F (see `docs/operations.md`) introduced the SoT entity tables (`model`, `model_file`, `tag`, `category`, `model_note`, `model_print`, `model_external_link`) and rewrote the frontend to consume only the new `/api/{models,categories,tags,...}` surface. After the UI cutover finished on 2026-05-05, the legacy backend was left in place purely for an observation window — no live frontend caller, no active operational consumer.

This cleanup pulls the trigger on that deferred work.

## What was removed

### HTTP endpoints

| Method | Path | File |
|---|---|---|
| GET | `/api/catalog/models` | `apps/api/app/modules/catalog/router.py` |
| GET | `/api/catalog/models/{model_id}` | `apps/api/app/modules/catalog/router.py` |
| GET | `/api/catalog/models/{model_id}/files` | `apps/api/app/modules/catalog/router.py` |
| GET | `/api/files/{model_id}/bundle` | `apps/api/app/modules/catalog/files.py` |
| GET | `/api/files/{model_id}/{relative:path}` | `apps/api/app/modules/catalog/files.py` |
| POST | `/api/admin/refresh-catalog` | `apps/api/app/modules/admin/router.py` |
| POST | `/api/admin/render/{string-id}` | `apps/api/app/modules/admin/router.py` |
| GET | `/api/admin/jobs/{string-id}` | `apps/api/app/modules/admin/router.py` |
| PUT | `/api/admin/models/{string-id}/thumbnail` | `apps/api/app/modules/admin/router.py` |
| DELETE | `/api/admin/models/{string-id}/thumbnail` | `apps/api/app/modules/admin/router.py` |

The SoT replacements were already in place at distinct (UUID-based) routes:

- `GET /api/models[/{uuid}[/files[/{uuid}/content]]]`
- `POST /api/admin/models/{uuid}/render`
- `PUT /api/admin/models/{uuid}/thumbnail` (takes `file_id` UUID, not a path string)

### Modules and classes

- `apps/api/app/modules/catalog/` — entire directory (`router.py`, `files.py`, `service.py`, `thumbnail_overrides.py`, `thumbnails.py`, `models.py`, `__init__.py`).
- `apps/api/app/core/db/models/_legacy.py` — `ThumbnailOverride` and `RenderSelection` ORM classes.
- `apps/api/app/config_for_tests.py` — `override_catalog_paths` helper used only by legacy tests.
- `app.state.catalog_service` and `app.state.thumbnail_overrides` — both initializations removed from `apps/api/app/main.py`.

The slimmed-down `apps/api/app/modules/admin/router.py` now holds only the audit-log readers and the `sentry-test` self-trigger; everything else was already on `apps/api/app/modules/sot/admin_router.py`.

### Database tables (Alembic 0008)

`apps/api/migrations/versions/0008_drop_legacy_tables.py` drops:

- `thumbnailoverride` — replaced by `model.thumbnail_file_id` (UUID FK to `model_file`).
- `renderselection` — replaced by `model_file.selected_for_render` (per-row bool).

Production migration ran cleanly during deploy:

```
INFO  [alembic.runtime.migration] Running upgrade 0007 -> 0008,
      Drop legacy tables: thumbnailoverride and renderselection.
```

### Worker

- `workers/render/render/config.py` — dropped unused `catalog_data_dir` and `renders_dir` settings. The worker has been on SoT (writing `ModelFile` rows under `portal-content`) since commit `4447aa8`; both fields were dead code.

### Tests

Removed (legacy-only): `test_catalog_router.py`, `test_catalog_service.py`, `test_catalog_models.py`, `test_files.py`, `test_filenames.py`, `test_thumbnail_resize.py`, `test_thumbnail_overrides_repo.py`, `test_admin_thumbnail.py`, `test_admin_refresh.py`, `test_admin_render.py`.

Updated: `test_migration_0005.py` — assertion flipped, the legacy tables must NOT exist after `alembic upgrade head` post-0008.

Pruned legacy fixture setup from: `test_admin_audit.py`, `test_admin_sentry_test_endpoint.py` (removed `override_catalog_paths` and `CATALOG_DATA_DIR`).

### Infra scripts

- `infra/scripts/sync-data.sh` — deleted. The Windows → `.190` rsync is no longer the source of truth; the SoT lives in `portal.db`.
- `infra/scripts/render-all.sh` — rewritten against SoT. Now lists `/api/models?limit=200` (auth-required), enqueues via `POST /api/admin/models/{uuid}/render` with body `{}`.

### Docs

- `docs/operations.md` — wholesale rewrite of "Sync catalog" section, troubleshooting row updated from `/api/catalog/models` → `/api/models`, "Retrigger render" snippet shows the SoT endpoint, "Force catalog refresh" snippet removed, "What remains" section trimmed (legacy removal moved to a "Legacy cleanup completed" entry under the SoT migration heading).
- `docs/architecture.md` — diagram updated to show `portal-content` and `portal-state` volumes (replacing `catalog-data` / `portal-renders`); container responsibilities and "Data flow" rewritten to describe the DB-as-SoT model.
- `AGENTS.md` — repo layout shows `render-all.sh` instead of `sync-data.sh`.

## What was ported, not removed

### `/api/share/{token}` and `/api/admin/share`

The share feature was the last consumer of `CatalogService`. Two paths were on the table: drop the public endpoint entirely, or port it to SoT. Chose the port — it was ~50 lines of work and keeps the surface available when we wire up a share UI again.

Changes:

- `ShareToken.model_id` is now `uuid.UUID` (was string). Existing tokens in Redis become unparseable after deploy and will be rejected as 404, which is acceptable: the frontend has no `/share/:token` view yet (only the `AppShell` routing stub), so no real user flow is affected.
- `POST /api/admin/share` now validates the model exists in the SoT `model` table (UUID lookup), not via `CatalogService`.
- `GET /api/share/{token}` reads `Model`, `Category`, `Tag`, `ModelFile` rows from the DB and emits image / thumbnail / STL URLs in the unified `/api/models/{id}/files/{file_id}/content` shape (with `?download=1` for the STL link).
- `ShareModelView.id` is `uuid.UUID`, `category` carries the slug, tags come from the M2M join.

Tests rewritten on a SoT-native fixture: `test_share_admin.py`, `test_share_public.py`, `test_share_service.py` all seed `Category` + `Model` + `ModelFile` rows directly via SQLModel and exercise the round-trip with UUIDs.

## What was deliberately kept

- `Model.legacy_id` (nullable, unique) — still referenced by the one-shot migration scripts in `apps/api/scripts/` (`migrate_from_index_json.py`, `backfill_legacy_renders.py`, `backfill_iso_thumbnail.py`, `fix_legacy_render_names.py`, `hydrate_local_tree.py`). They allow a fresh `.190` to be rehydrated from a legacy snapshot. Field can be dropped when those scripts are retired.
- `Settings.catalog_data_dir` and `Settings.renders_dir` on the API — the API no longer reads them at runtime, but `backfill_legacy_renders.py` still does. Fine to leave.
- `apps/api/scripts/` migration tooling — none of the actual one-shots is reachable through the API anymore; they remain runnable from the CLI as historical backstops.

## Verification

| Check | Result |
|---|---|
| `ruff check` (apps/api) | All checks passed |
| `pytest apps/api/tests` | 354 passed |
| `ruff check` (workers/render) | 2 pre-existing `RUF059` warnings in `tests/test_worker_sot.py` (untouched by this PR) |
| `pytest workers/render/tests` | 12 passed |
| `npm run lint` (apps/web) | 0 warnings |
| `tsc -b` (apps/web) | clean |
| Production smoke `GET /api/health` | `{"status":"ok","version":"0.1.0"}` |

## Diff stats

```
40 files changed, 353 insertions(+), 2562 deletions(-)
```

Net code reduction across api + worker + infra + docs: ~2.2k lines.

## Follow-ups (not blocking)

1. **Drop `Model.legacy_id`** once the legacy backfill scripts are retired (no near-term need; revisit if the schema gets refactored for any other reason).
2. **Drop `Settings.catalog_data_dir` and `Settings.renders_dir`** from `apps/api/app/core/config.py` at the same time as (1).
3. **Resurrect a `/share/:token` UI.** The backend is ready; the frontend currently has only an `AppShell` stub. Tracked in the "UI deferrals" list in `docs/operations.md`.
4. **Frozen fixtures under `apps/api/tests/fixtures/catalog/`** — only used by the legacy backfill tests now. Could be moved next to those tests or deleted along with the scripts.

## References

- Commit: `d92e551`
- Alembic head: `0008_drop_legacy_tables`
- Pre-cleanup audit summary: this conversation log
- Operations runbook (post-state): `docs/operations.md`
- Architecture (post-state): `docs/architecture.md`
