---
title: 'Story 22.1 — Backend gallery tier worker + variant routing + backfill (TB-037 BE)'
type: 'feature'
status: 'ready-for-dev'
story_id: '22.1'
epic: 'E22 — Image Tier Pipeline + Symmetric Fullscreen Viewer'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-037 BE'
fr_ref: 'FR16-TIER-1'
architectural_anchor: 'Decision W'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.5 per [[feedback_codex_model_routing]] worker + storage layer)'
estimated_effort: '1.5-2 h backend + variant routing + backfill + tests + designer 1920px tier verify'
created: '2026-05-24'
---

# Story 22.1 — Backend gallery tier worker + variant routing + backfill (TB-037 BE)

Status: ready-for-dev

## Story

As a share recipient AND authenticated catalog browser viewing the in-page carousel main frame,
I want a middle-tier image variant (`.gallery.webp`, ~150-500 KB, designer-tuned 1920px longest-edge) generated server-side alongside the existing `.thumb.webp` sibling,
so that the carousel main frame can serve a substantially smaller blob than the 4-8 MB original while still delivering desktop-fullscreen-quality detail — closing the bandwidth gap that fired Story 19.2 nginx caps + producing 503s on legitimate carousel use (closes TB-037 backend pipeline).

## Acceptance Criteria

1. **AC1 — NEW `GALLERY_*` constants** in `apps/api/app/workers/generate_thumbnail.py`:
   - `GALLERY_LONGEST_SIDE_PX = 1920` (designer-locked per `_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md` §3)
   - `GALLERY_SUFFIX = ".gallery.webp"`
   - Helper `gallery_path_for(original: Path) -> Path` returning `original.with_name(original.name + GALLERY_SUFFIX)`.

2. **AC2 — NEW `generate_gallery_sync(engine, model_file_id, *, content_dir=None) -> dict`** mirroring `generate_thumbnail_sync` shape. Returns `{"status": "ok|skipped|missing|not_image|row_missing|error", "gallery_path": <rel path or None>, "size_bytes": <int or None>, "reason": <optional>}`. Idempotent: skips if `<storage_path>.gallery.webp` already exists. Same error handling (path_escape, original_missing, unidentified_image, generic) as thumbnail counterpart.

3. **AC3 — NEW `_render_gallery(original_abs, gallery_abs)` helper** mirroring `_render_thumbnail` but with `GALLERY_LONGEST_SIDE_PX=1920` instead of 800. Same Pillow pipeline: `exif_transpose → mode-fix → thumbnail(1920) → WebP @ q80 → atomic tmp+rename`. Same P2-3 unique-tmp-per-job pattern (pid + uuid hex) to defend against concurrent backfill races.

4. **AC4 — arq task `generate_thumbnail` extended to produce BOTH variants.** The async entry point at line 234 now invokes BOTH `generate_thumbnail_sync` AND `generate_gallery_sync`. Return shape: `{"thumbnail": <thumb result dict>, "gallery": <gallery result dict>}` (composite). Failure isolation: if thumbnail fails but gallery succeeds (or vice versa), return composite with both status entries — caller can act on either. Each `_sync` function handles its own error path independently.

5. **AC5 — Variant routing in `apps/api/app/modules/sot/router.py`** extended for `?variant=gallery`. New branch at the existing variant handling (~line 248): `elif variant == "gallery": gallery_candidate = candidate.with_name(candidate.name + ".gallery.webp")` — if `gallery_candidate.is_file()` return it, else silent fallback to original blob (mirror existing `?variant=thumb` fallback semantics from Story 13.2). OpenAPI doc / endpoint docstring extended to document `gallery` variant alongside `thumb`.

6. **AC6 — Backfill script extension.** `infra/scripts/backfill-thumbnails.sh` (and any underlying `enqueue_thumbnail_backfill.py` if present) extended OR renamed to `backfill-variants.sh` to cover both tiers. Script runs `generate_thumbnail` arq task which now produces both → no separate `generate_gallery` enqueue needed (BOTH variants written per job). Smoke output shape: `inspected=N already_present_thumb=T already_present_gallery=G enqueued=E rendered_thumb=R1 rendered_gallery=R2 missing_original=0 errors=N`. Verify script invocation matches Init 11-15 backfill precedent (Story 23.2 spec referenced these scripts; verify path).

7. **AC7 — Pytest fixture for gallery tier ≤500 KB per NFR16-PERF-1.** Extend `apps/api/tests/test_thumbnail_pipeline.py` (or NEW `test_gallery_pipeline.py`) with:
   - Test that `generate_gallery_sync` on representative samples (3000×4000 JPEG, 4000×3000 JPEG, 2000×3000 PNG with alpha) produces `gallery_path` blob ≤500 KB.
   - Test idempotency (rerun returns `skipped`).
   - Test fallback semantics: `?variant=gallery` on a file lacking the gallery sibling falls back to original.
   - Test happy path: variant routing returns the gallery blob with correct WebP MIME type when sibling exists.

8. **AC8 — Backend pytest 892+/892+ PASS 3× consecutive.** Story 23.3 baseline 892 + ~5-10 new gallery-tier tests → expect 897-902 PASS deterministic.

9. **AC9 — Ruff + alembic check clean.** No schema migration (file-system sibling pattern, same as Story 13.2 thumbnail).

10. **AC10 — Codex review CLEAN (gpt-5.5 worker + storage layer).** Per [[feedback_codex_model_routing]]. Round-2 fix-up acceptable.

11. **AC11 — Designer-locked dimension preserved.** `GALLERY_LONGEST_SIDE_PX = 1920` MUST match designer UX spec at `22-3-designer-ux-spec.md` §3 (operator surface scope decision + designer's "1920 px is the cleanest tradeoff" rationale). NOT a free-choice tunable — locked at this value per spec.

## Tasks / Subtasks

- [ ] **T1 — Worker constants + helpers** (AC: #1, #2, #3)
  - [ ] T1.1 — Add `GALLERY_LONGEST_SIDE_PX = 1920`, `GALLERY_SUFFIX = ".gallery.webp"`, `gallery_path_for()` to `generate_thumbnail.py`.
  - [ ] T1.2 — Add `_render_gallery()` mirroring `_render_thumbnail` with 1920px constant.
  - [ ] T1.3 — Add `generate_gallery_sync()` mirroring `generate_thumbnail_sync` shape + error handling.

- [ ] **T2 — arq task composite return** (AC: #4)
  - [ ] T2.1 — Update `generate_thumbnail(_ctx, model_file_id)` to invoke BOTH `generate_thumbnail_sync` + `generate_gallery_sync`.
  - [ ] T2.2 — Return composite `{"thumbnail": ..., "gallery": ...}` shape.
  - [ ] T2.3 — Failure isolation: each `_sync` failure is contained; composite return still surfaces both status entries.

- [ ] **T3 — Variant routing** (AC: #5)
  - [ ] T3.1 — Add `?variant=gallery` branch in sot/router.py variant handler (mirror existing `?variant=thumb` shape).
  - [ ] T3.2 — Update endpoint docstring + OpenAPI summary to document `gallery` variant + fallback semantics.

- [ ] **T4 — Backfill script** (AC: #6)
  - [ ] T4.1 — Verify existing backfill script path (`infra/scripts/backfill-thumbnails.sh` per Story 23.2 spec reference).
  - [ ] T4.2 — Confirm the script invokes `generate_thumbnail` arq task → no script-side changes needed since the task now produces both variants. ELSE if the script enqueues a different task name OR uses a direct call, extend it accordingly.
  - [ ] T4.3 — Update script smoke output messaging to reflect both-tier semantics (per AC6).

- [ ] **T5 — Tests** (AC: #7, #8, #9)
  - [ ] T5.1 — Extend `test_thumbnail_pipeline.py` (preferred) or NEW `test_gallery_pipeline.py` with gallery-tier test cases.
  - [ ] T5.2 — Sample sizes: 3000×4000 JPEG, 4000×3000 JPEG, 2000×3000 PNG with alpha; assert `≤500 KB` gallery blob.
  - [ ] T5.3 — Idempotency + fallback + happy-path routing.
  - [ ] T5.4 — Full pytest 3× consecutive determinism per NFR16-DETERMINISM-1.

- [ ] **T6 — Pre-merge gates**
  - [ ] T6.1 — ruff check + format clean on touched files.
  - [ ] T6.2 — alembic check "No new upgrade operations".
  - [ ] T6.3 — Full pytest 3× consecutive.

- [ ] **T7 — Commit + Codex review + auto-deploy** (orchestrator handles)
  - [ ] T7.1 — Commit: `feat(workers,sot): gallery tier variant pipeline (Story 22.1, TB-037)`.
  - [ ] T7.2 — Codex review default gpt-5.5 (worker + storage class).
  - [ ] T7.3 — Round-2 fix-up if P1/P2.
  - [ ] T7.4 — Auto-deploy + backfill rerun on .190 to populate gallery tier for existing files.
  - [ ] T7.5 — Sprint-status flip + TB-037 BE side noted as done.

## Dev Notes

### Existing pattern (Story 13.2 / Decision P — already shipped)

`apps/api/app/workers/generate_thumbnail.py:32-243`:
- Constants: `THUMBNAIL_LONGEST_SIDE_PX = 800`, `WEBP_QUALITY = 80`, `THUMBNAIL_SUFFIX = ".thumb.webp"`
- Helper: `thumbnail_path_for(original)` → sibling path
- Sync: `generate_thumbnail_sync(engine, model_file_id, content_dir=None) -> dict` with status enum
- Render: `_render_thumbnail(original_abs, thumb_abs)` — Pillow EXIF + mode-fix + thumbnail + WebP + atomic tmp+rename
- arq task: `generate_thumbnail(_ctx, model_file_id)` wrapping the sync function

Story 22.1 ADDS a parallel gallery-tier branch using IDENTICAL shape:
- Constants: `GALLERY_LONGEST_SIDE_PX = 1920` (designer-locked)
- Helper: `gallery_path_for(original)`
- Sync: `generate_gallery_sync(engine, model_file_id, content_dir=None) -> dict`
- Render: `_render_gallery(original_abs, gallery_abs)`
- arq task: extends `generate_thumbnail` to call BOTH sync functions

### Fix sketch (paste-ready)

```python
# generate_thumbnail.py — top constants
THUMBNAIL_LONGEST_SIDE_PX = 800
GALLERY_LONGEST_SIDE_PX = 1920  # Story 22.1 / Decision W — designer-locked
WEBP_QUALITY = 80
THUMBNAIL_SUFFIX = ".thumb.webp"
GALLERY_SUFFIX = ".gallery.webp"  # Story 22.1


def thumbnail_path_for(original: Path) -> Path:
    return original.with_name(original.name + THUMBNAIL_SUFFIX)


def gallery_path_for(original: Path) -> Path:  # NEW Story 22.1
    return original.with_name(original.name + GALLERY_SUFFIX)


def generate_gallery_sync(engine, model_file_id, *, content_dir=None) -> dict:
    """Generate gallery-tier WebP for image ModelFile (Story 22.1 / FR16-TIER-1).

    Mirrors generate_thumbnail_sync shape — 1920px longest-edge instead of 800px.
    Sibling file: <storage_path>.gallery.webp. Idempotent on existing sibling.
    """
    if content_dir is None:
        content_dir = get_settings().portal_content_dir

    with Session(engine) as s:
        row = s.exec(select(ModelFile).where(ModelFile.id == model_file_id)).first()
        if row is None:
            return {"status": "row_missing", "gallery_path": None, "size_bytes": None}
        if row.kind not in (ModelFileKind.image, ModelFileKind.print):
            return {
                "status": "not_image",
                "gallery_path": None,
                "size_bytes": None,
                "reason": f"kind={row.kind.value}",
            }

        original_abs = (content_dir / row.storage_path).resolve()
        base = content_dir.resolve()
        try:
            original_abs.relative_to(base)
        except ValueError:
            return {"status": "error", "gallery_path": None, "size_bytes": None, "reason": "path_escape"}

        if not original_abs.is_file():
            return {"status": "missing", "gallery_path": None, "size_bytes": None, "reason": "original_missing"}

        gallery_abs = gallery_path_for(original_abs)
        gallery_rel = row.storage_path + GALLERY_SUFFIX

        if gallery_abs.exists():
            return {
                "status": "skipped",
                "gallery_path": gallery_rel,
                "size_bytes": gallery_abs.stat().st_size,
            }

        try:
            size_bytes = _render_gallery(original_abs, gallery_abs)
        except UnidentifiedImageError as exc:
            _LOG.warning("gallery.unidentified", extra={...})
            return {"status": "error", "gallery_path": None, "size_bytes": None, "reason": "unidentified_image"}
        except Exception as exc:
            _LOG.exception("gallery.error", extra={...})
            return {"status": "error", "gallery_path": None, "size_bytes": None, "reason": repr(exc)}

        _LOG.info("gallery.ok", extra={...})
        return {"status": "ok", "gallery_path": gallery_rel, "size_bytes": size_bytes}


def _render_gallery(original_abs: Path, gallery_abs: Path) -> int:
    """1920px longest-edge WebP. Mirrors _render_thumbnail."""
    with Image.open(original_abs) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode == "P":
            im = im.convert("RGBA")
        im.thumbnail((GALLERY_LONGEST_SIDE_PX, GALLERY_LONGEST_SIDE_PX))
        tmp_abs = gallery_abs.with_name(f"{gallery_abs.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        try:
            im.save(tmp_abs, format="WEBP", quality=WEBP_QUALITY, method=6)
            tmp_abs.replace(gallery_abs)
        finally:
            tmp_abs.unlink(missing_ok=True)
    return gallery_abs.stat().st_size


async def generate_thumbnail(_ctx, model_file_id: uuid.UUID | str) -> dict:
    """arq task: produce BOTH thumb AND gallery tiers (Story 22.1)."""
    if isinstance(model_file_id, str):
        model_file_id = uuid.UUID(model_file_id)
    engine = get_engine()
    return {
        "thumbnail": generate_thumbnail_sync(engine, model_file_id),
        "gallery": generate_gallery_sync(engine, model_file_id),
    }
```

```python
# sot/router.py — variant routing (around line 248)
if variant == "thumb":
    thumb_candidate = candidate.with_name(candidate.name + ".thumb.webp")
    if thumb_candidate.is_file():
        return _serve_file(thumb_candidate, "image/webp", ...)
    # silent fallback to original
elif variant == "gallery":  # NEW Story 22.1
    gallery_candidate = candidate.with_name(candidate.name + ".gallery.webp")
    if gallery_candidate.is_file():
        return _serve_file(gallery_candidate, "image/webp", ...)
    # silent fallback to original (mirror thumb semantics)
```

### Designer-locked dimension (NOT operator-tunable)

`GALLERY_LONGEST_SIDE_PX = 1920` is locked per designer UX spec rationale at `22-3-designer-ux-spec.md` §3:
- Covers 1080p fullscreen-but-not-zoomed (where the in-page carousel main frame renders) AND all 2x DPR laptop main frames (MacBook 2x ≈ 1440 px physical-bitmap demand on longest edge).
- Falls short only on 4K/5K monitors viewing the gallery frame at full bleed — which is exactly the case the **fullscreen viewer tier** (original blob via `?variant=full`) handles.
- Payload stays in the 150-500 KB band per TB-037 + NFR16-PERF-1 contract.

If operator surfaces "wanting different dimension" post-deploy → discuss as Init 17+ tuning candidate, NOT a Story 22.1 deviation.

### Composite arq-task return + caller compat

Existing callers of `generate_thumbnail` arq task (from `apps/api/app/modules/sot/admin_router.py` upload paths + any cron + backfill scripts) likely consume the return dict via logs only (it's an arq job, fire-and-forget from the dispatch path). The composite shape `{"thumbnail": ..., "gallery": ...}` should be backward-compatible since callers don't deep-inspect the return.

Verify by grep: `grep -rn "await.*generate_thumbnail\|arq.enqueue.*generate_thumbnail" apps/api/` to find all dispatch sites. None should pattern-match on `["status"]` directly on the arq result — if any do, fix in same commit.

### Backfill script context

Per Story 23.2 spec reference: `apps/api/scripts/enqueue_thumbnail_backfill.py` + `infra/scripts/backfill-thumbnails.sh` already exist (ran 2026-05-23 per Init 11-15 close-out). Since the arq task now produces both variants, the backfill script needs NO logic change — invocation still enqueues `generate_thumbnail` per row → worker produces both `.thumb.webp` AND `.gallery.webp`. Operator just re-runs the backfill post-deploy to populate gallery tier for existing files.

Smoke output messaging may benefit from updating to show both-tier rendering counts. Optional polish.

## File List

**MODIFIED (3):**
- `apps/api/app/workers/generate_thumbnail.py` — +constants, +`gallery_path_for`, +`generate_gallery_sync`, +`_render_gallery`, composite return in arq task
- `apps/api/app/modules/sot/router.py` — +`?variant=gallery` branch
- `apps/api/tests/test_thumbnail_pipeline.py` — +gallery tier tests (or split to NEW test_gallery_pipeline.py)

**OPTIONAL:**
- `apps/api/scripts/enqueue_thumbnail_backfill.py` — output messaging tweak (optional polish)
- `infra/scripts/backfill-thumbnails.sh` — same (optional polish)

**Diff stats expected:**
- ~80-120 LOC added across worker + router
- ~50-80 LOC test additions
- Net: +130-200 LOC

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Ruff check | `cd apps/api && uv run ruff check app/workers/generate_thumbnail.py app/modules/sot/router.py tests/` | Clean |
| Ruff format | `cd apps/api && uv run ruff format --check ...` | Clean |
| Alembic | `cd apps/api && uv run alembic check` | "No new upgrade operations" |
| Pytest × 3 | `cd apps/api && timeout 600 uv run pytest -q tests/` | 897+/897+ PASS deterministic |
| Codex review | `codex review --commit <SHA>` (default gpt-5.5) | CLEAN OR fix-up |
| Post-deploy backfill (operator) | `infra/scripts/backfill-thumbnails.sh --inline` on .190 | `rendered_thumb` + `rendered_gallery` counts match |

## References

- [Init 16 SCP §4.1 Story 22.1](sprint-change-proposal-2026-05-24-init16.md#41-epic-e22--image-tier-pipeline--symmetric-fullscreen-viewer)
- [architecture.md § Decision W](../planning-artifacts/architecture.md#decision-w--gallery-tier-variant-pipeline-shape-epic-22--fr16-tier-1)
- [prd.md § FR16-TIER-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep)
- [22-3-designer-ux-spec.md §3](22-3-designer-ux-spec.md) — designer-locked 1920px rationale
- Story 13.2 / Decision P precedent — `generate_thumbnail.py` shape
- Memory: [[feedback_codex_model_routing]] (gpt-5.5 worker/storage), [[feedback_pytest_timeout]], [[feedback_pre_merge_gate_checklist]], [[feedback_auto_deploy_dev]]

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
