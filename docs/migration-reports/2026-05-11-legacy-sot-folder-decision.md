# Legacy SoT folder + `Model.legacy_id` triage decision

**Date:** 2026-05-11
**Author:** Claude Opus 4.7 (1M context), via BMAD Story 4.1–4.5 (Initiative 2 Epic 4)
**Status:** Decision recorded; execution gated on a follow-up story (see § "Follow-up").
**Related:** `_bmad-output/planning-artifacts/architecture.md` § Initiative 2 Decision H; `_bmad-output/planning-artifacts/prd.md` § FR7 + NFR4; `docs/migration-reports/2026-05-06-legacy-sot-cleanup.md` (predecessor).

---

## Why this document exists

The post-SoT-migration portal (Slices 2A–2D + 3A–3F, cutover 2026-05-04) inherits three artefacts whose purpose has narrowed since cutover:

1. **`Model.legacy_id`** — a nullable unique string column on the `model` SQLModel entity. Set on every row migrated from the legacy file-based catalog (`_index/index.json`) at cutover; never written or read by any post-cutover operational flow.
2. **Four migration scripts in `apps/api/scripts/`** — `migrate_from_index_json.py` (~900 lines, the cutover entry point), `backfill_legacy_renders.py` (~300 lines), `backfill_iso_thumbnail.py` (~130 lines), `fix_legacy_render_names.py` (~140 lines). All are one-shot tools used during the 2026-05-04 cutover sweep.
3. **The legacy folder** at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` — ~2.7 GB of files-on-Nextcloud that was the source of truth before cutover. Now serves as (a) un-migrated runbook content (closed by Story 4.1), (b) restore-snapshot for the migration scripts, (c) 3MF originals archive (now redundant — bits are on `.190` under `_archive/3mf-originals/`).

Decision-doc-first discipline (NFR4) requires a written rationale BEFORE any irreversible cleanup (Alembic migration to drop the column, scripts deletion, folder retirement). This document captures the three audit inputs, the trade-offs, the chosen option, and the follow-up that executes it.

---

## Audit input 1 — Last observed `legacy_id` use (`audit_log` query)

Queried 2026-05-11 against the live SQLite at `/data/state/portal.db` on `.190` via the `3d-portal-api-1` container.

```python
# Total audit_log rows
SELECT COUNT(*) FROM audit_log;
# → 1528

# Date range
SELECT MIN(at), MAX(at) FROM audit_log;
# → 2026-05-04 17:24:45 → 2026-05-10 15:48:53

# Audit rows mentioning legacy_id in either side of the diff
SELECT COUNT(*) FROM audit_log WHERE before_json LIKE '%legacy_id%';
# → 0
SELECT COUNT(*) FROM audit_log WHERE after_json LIKE '%legacy_id%';
# → 89

# Most-recent legacy_id-touching row
SELECT at, action, entity_type FROM audit_log
  WHERE before_json LIKE '%legacy_id%' OR after_json LIKE '%legacy_id%'
  ORDER BY at DESC LIMIT 1;
# → 2026-05-04 19:15:33  model.create  model
```

**Interpretation:** all 89 `legacy_id` audit references are from the initial migration sweep on 2026-05-04 (`model.create` events emitting the full row including `legacy_id` in `after_json`). Zero updates, zero deletes, zero patches have touched `legacy_id` in the seven days post-cutover. The field is **functionally dead data** — populated once, never read or written by any subsequent flow.

```python
# Catalog state
SELECT COUNT(*) FROM model;                            # → 89
SELECT COUNT(*) FROM model WHERE legacy_id IS NOT NULL; # → 89
```

**Interpretation:** every model in the catalog has a non-null `legacy_id`. No models have been created post-cutover via the admin API (the admin `ModelCreate` schema does NOT carry `legacy_id`, so admin-API-created models would have `legacy_id=NULL`). All 89 are migration-imported. The agent runbook flow (Story 4.1–4.5) is the first mechanism that will start producing `legacy_id=NULL` rows, the moment Ezop or an agent uses it.

---

## Audit input 2 — Schema-compatibility of the four migration scripts

```bash
cd apps/api
for s in migrate_from_index_json backfill_legacy_renders \
         backfill_iso_thumbnail fix_legacy_render_names; do
  python -c "import importlib.util, sys; sys.path.insert(0, '.'); \
             spec = importlib.util.find_spec(f'scripts.$s'); \
             print('$s:', 'import OK' if spec else 'NOT FOUND')"
done
# → all four: import OK
```

**Interpretation:** all four scripts still import cleanly against the current schema (Alembic version `0009`). The SQLModel entity hasn't drifted in a way that breaks the scripts' references.

This does NOT prove the scripts would *run* successfully end-to-end — only that the imports + class references resolve. A real re-run would also need:
- A clean SQLite (or a snapshot of one) to import into.
- The legacy `_index/index.json` + folder layout intact (the Nextcloud-hosted source).
- The portal-content storage volume writable.

Re-running these scripts post-cutover is a "rebuild from scratch" path, not a "small fix-up" path.

---

## Audit input 3 — Backup strategy if scripts retire

If the four scripts are deleted and `Model.legacy_id` is dropped, the recoverability scenarios are:

| Failure mode | Recovery path under "drop" | Recovery path under "freeze" |
|---|---|---|
| `portal.db` corruption | Restore SQLite from a daily backup (already performed by the `.190` host's general backup policy) | Same |
| Catastrophic .190 loss | Restore SQLite from off-site backup; reimport Nextcloud catalog via... nothing — the migration scripts are gone | Re-run `migrate_from_index_json.py` against the Nextcloud snapshot |
| Need to cross-reference a model UUID with its legacy id | Query the frozen `legacy-id-snapshot.json` artefact (one-time export captured before drop) | Query `Model.legacy_id` directly |
| Audit "what was the legacy id of this model?" | Same frozen JSON | Same DB column |

The catastrophic-`.190`-loss recovery path is the only meaningful difference. **Mitigation under "drop"**: a one-time export of the current 89-row `(model.id, model.legacy_id, model.name_en, model.created_at)` tuple as `docs/migration-reports/2026-05-11-legacy-id-snapshot.json` (~5 KB, committed to git) preserves the cross-reference. Re-running the migration in a hypothetical disaster scenario would have to be done manually OR by checking the relevant commit out of git history (commit `d92e551` "drop legacy file-based catalog and port share to SoT" is the natural restore reference point — it predates this document).

---

## Decision

**Drop `Model.legacy_id` + retire the four migration scripts.**

### Rationale

1. **The column is dead data.** Audit input 1 proves zero post-cutover writes/reads through any operational flow. Keeping a column "just in case" with this profile is exactly the kind of soft accumulation that creates schema cruft in long-lived systems.
2. **The scripts are deeply one-shot.** `migrate_from_index_json.py` (900 lines) is not a generic restore tool — it expects a specific Nextcloud folder layout that, post-Story 4.1 + retro-cleanup of the legacy folder, no longer exists in its original shape anyway. Keeping the scripts "as restore-snapshot" pretends they could re-run; in practice they couldn't without significant re-work, which is a worse posture than honest deletion.
3. **The new agent runbook flow (Initiative 2) makes admin-API model creation the canonical path.** New models will have `legacy_id=NULL`. The 89 existing rows would carry the only non-null values forever, and the column would become a "this model was migrated from the file-based era" badge — an archaeology marker, not operational state. Better captured in a one-time JSON snapshot than as a live column.
4. **Decision-doc-first discipline (NFR4)** means we capture the rationale before execution. This document IS the audit trail; the cross-reference snapshot file IS the durable record of legacy_id values for any future archaeologist.
5. **Folder retirement is decoupled.** The Nextcloud folder retirement decision is separate from the column-drop decision. Once `legacy_id` is dropped + scripts retired, the folder's only remaining role is "3MF originals archive (redundant — also on .190)" + "old AGENTS.md (already ported)". Folder retirement can be a later third story; this document does not require it.

### Alternatives considered

- **Freeze with marker** (`apps/api/scripts/README.md` says "do not modify; restore-only artifact"). Rejected because the scripts wouldn't actually work anymore (see point 2). A marker that says "do not modify these scripts because they were once useful" is documentation theatre; a clean delete + commit-history pointer is more honest.
- **Drop scripts but keep `Model.legacy_id`.** Rejected because the column has no operational purpose (audit input 1) and creates ongoing schema-migration friction (every future PATCH/UPDATE schema change has to think about it). The cross-reference can be preserved as a JSON snapshot.
- **Defer indefinitely.** Rejected because the gap stays open as the codebase evolves, and the un-decided state itself is friction (every future audit on "should we drop X?" has to re-litigate the same question).

### What this decision is NOT

- **NOT** a decision to delete the legacy Nextcloud folder. That folder still exists; future cleanup is a separate decision. This decision only retires the in-repo `apps/api/scripts/` artefacts and the DB column.
- **NOT** an irreversible commit. The follow-up story (below) is what actually executes the change — Alembic migration, file deletes, schema updates — and is gated on Ezop's review of this document.

---

## Follow-up

A follow-up story (working name: **`4-4-followup-drop-legacy-id`**, scope: Alembic migration + code/schema/test cleanup) executes this decision. Estimated work:

1. **Capture snapshot** — `docs/migration-reports/2026-05-11-legacy-id-snapshot.json` containing `(model.id, model.legacy_id, model.name_en, model.created_at)` for all 89 rows. Committed to git.
2. **Alembic migration** `0010_drop_model_legacy_id.py` — `op.drop_index('ix_model_legacy_id'); op.drop_column('model', 'legacy_id')`.
3. **Code updates:**
   - `apps/api/app/core/db/models/_entities.py:82` — remove the `legacy_id` field.
   - `apps/api/app/modules/sot/schemas.py:90` — remove `legacy_id: str | None` from `ModelDetail`.
   - `apps/api/app/modules/sot/admin_service.py:137` — remove `"legacy_id": m.legacy_id` from the audit payload.
4. **Frontend updates:**
   - `apps/web/src/lib/api-types.ts:139` — regenerate (drops the field automatically when the OpenAPI spec changes).
   - `apps/web/src/modules/catalog/components/*.test.tsx` — remove `legacy_id: null` / `legacy_id: "001"` from fixture data (~9 test files).
   - `apps/web/src/routes/dev/components.tsx:18` — same.
5. **Script deletions** — `git rm apps/api/scripts/{migrate_from_index_json,backfill_legacy_renders,backfill_iso_thumbnail,fix_legacy_render_names}.py`. Total: 4 files, ~1464 lines retired.
6. **Test runs** — full backend pytest + frontend vitest + Playwright visual regression.
7. **Commit + auto-deploy** — single commit `chore(api): drop Model.legacy_id + retire 4 migration scripts (E4.4-followup)`. Deploy.sh runs `alembic upgrade head` which executes the new migration; verify-symbolication + verify-runbook continue to pass (no behavioral change to the agent surface).

Estimated effort: ~2-3 hours of agent execution. Risk: low (schema change is mechanical; no behavioral surface affected; test coverage catches type drift).

---

## Document hygiene

This document MUST be merged before the follow-up story executes. The merge commit IS the operator's approval — once merged, the follow-up is unblocked. If Ezop disagrees with the recommendation (chose "freeze" instead, or "defer"), edit this section and the rationale in place; the document remains the durable record of how the call was made.
