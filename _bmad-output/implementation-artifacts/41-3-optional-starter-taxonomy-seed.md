---
baseline_commit: efc270a
---

# Story 41.3: Optional starter-taxonomy seed (idempotent admin-run `TagGroup` + `Tag` population; no model assignments)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a catalog platform owner,
I want an **idempotent, admin-run** seed that populates the starter facet taxonomy from HANDOFF §8 — creating `TagGroup` + `Tag` rows only, with deterministic slugs, ordering, and bilingual names — **without touching any model** (models stay untagged),
so that after `0018_facet_tags` there is a ready starter set of facets/tags for admins to curate and for the E42+ read API / UI to consume, and re-running the seed (e.g. on redeploy or by mistake) never duplicates rows or clobbers admin edits.

## Context & scope guardrails (READ FIRST)

- This is the **third and final E41 story**. 41.1 landed the ORM (`TagGroup`, `Tag.group_id`/`group_position`); 41.2 landed the additive, reversible migration `0018_facet_tags`. This story adds **data-seeding logic + tests only** — no schema change, no migration, no ORM change.
- **Re-scoped back into E41.** The prior epic closeout (2026-07-18) deferred 41.3 to E42 (`DEFER_41_3`). That closeout was premature and is reversed: 41.3 is implemented **here** to actually finish Epic 41. E41 does not close until this story lands.
- **`TagGroup` + `Tag` rows ONLY.** No `model_tag` rows, no `Model` writes, no per-model tag assignment. Models remain untagged after seeding (deliberate reset per HANDOFF §1 + §5; triaged later via `untagged=true`, an E42 filter).
- **No live DB execution during dev.** All verification runs against a throwaway SQLite DB in tests (see Testing Standards). Do **not** run the seed against any real/dev/prod database, and do **not** commit/push/deploy.
- **No destructive DDL, no `Category` work.** The `0019_drop_category` destructive migration remains owed by the E42 cut-over (see `deferred-work.md`) — out of scope here.

## Acceptance Criteria

1. **New idempotent seed function `seed_taxonomy(engine: Engine) -> None`** added to `apps/api/app/core/db/seed.py`, mirroring the existing `seed_admin` contract exactly: opens `with Session(engine) as session:`, is **create-if-absent** keyed on the unique `slug`, **never updates or deletes** an existing row, and tolerates a concurrent-insert `IntegrityError` by `session.rollback()`-ing and treating "row already exists" as success (same rationale as `seed_admin` lines 21-26). Imports `TagGroup`, `Tag` from `app.core.db.models` (both already exported — `models/__init__.py:26-27`).
2. **Deterministic starter dataset** lives as a module-level constant in `seed.py` (e.g. `STARTER_TAXONOMY`), a plain ordered Python data structure derived from HANDOFF §8, containing for each group: `slug` (explicit ASCII), `name_en`, `name_pl`, `position`, and its ordered tags each with `slug` (explicit ASCII), `name_en`, `name_pl`, `group_position`. The concrete starter values are in **Dev Notes → Starter dataset**; treat them as **owner-editable seed content**, not frozen ACs (HANDOFF §8 header: *"do edycji przez właściciela"*).
3. **Slugs are explicit ASCII constants, NOT derived from the Polish names.** Do **not** feed `name_pl` through `admin_service._slugify` — its regex `[^a-z0-9]+` on `str.lower()` is diacritic-lossy (`"Łazienka" → "azienka"`, `"Oświetlenie" → "o-wietlenie"`) and would produce mangled, potentially colliding slugs. Each seed row carries a hand-authored ASCII slug (English-derived). All group slugs are globally unique; all tag slugs are globally unique (matches `TagGroup.slug` / `Tag.slug` uniqueness).
4. **Deterministic ordering.** `TagGroup.position` and `Tag.group_position` are assigned from the dataset's declared order (0-based, or dense per the dataset), so a fresh seed yields a stable, reproducible ordering. Group order follows HANDOFF §8 top-to-bottom; per §9.3, `Typ` (position 0) and `Pomieszczenie` (position 1) are the primary axes and MUST be the first two groups.
5. **`Tag.group_id` is resolved to the parent group's row id** (each tag is linked to its group via the FK created in 41.2). No tag is left with a dangling/None `group_id` in the starter dataset (every starter tag belongs to a group). `Tag.group_position` orders tags within their group.
6. **Zero model/category side effects.** `seed_taxonomy` performs **no** `Model`, `ModelTag`, or `Category` reads/writes. A test asserts model/tag-assignment tables are untouched (e.g. no `model_tag` rows created; `Model` count unchanged when models pre-exist).
7. **Idempotency + no-duplicate:** running `seed_taxonomy(engine)` **twice** yields exactly one row per group slug and one row per tag slug (counts equal after run 1 and run 2). Mirrors `test_seed.py::test_seed_is_idempotent`.
8. **Update-policy (no-clobber):** if a row with a seeded `slug` already exists with a **different** `name_en`/`name_pl`/`position`/`group_position` (simulating an admin rename/reorder), re-running the seed **leaves that row unchanged** (create-if-absent, never update — same semantics `test_seed_is_idempotent` asserts for the admin user). This is the conservative default derived from `seed_admin` + HANDOFF §9 (admin owns rename/reorder governance). See Story Creation Question #1.
9. **Error-atomicity:** a failure partway through seeding does not leave a partially-committed inconsistent set that a re-run cannot converge. The seed either (a) commits per-row so a re-run completes the remainder idempotently (preferred — matches `seed_admin`'s single-entity commit), or (b) commits once at the end so a mid-run failure rolls the whole batch back; whichever is chosen, a test proves that after an injected failure + a clean re-run, the full dataset is present exactly once with no duplicates or orphans. Document the chosen transaction boundary in the function docstring.
10. **New test module `apps/api/tests/test_seed_taxonomy.py`**, mirroring `test_seed.py` fixture shape (`create_engine_for_url(f"sqlite:///{tmp_path}/…db")` + `init_schema(engine)`; **no** live DB, no `TestClient`, no `session` app fixture). Covers AC #6-#9 plus: full-population count (every group + tag present), group/tag slug uniqueness, `Typ`/`Pomieszczenie` first-two ordering (AC #4), and `group_id` linkage (AC #5). Because `init_schema()` builds the schema from the ORM (`session.py:31`), the test needs no migration.
11. **Admin-run entrypoint (mechanism, not auto-startup).** Expose the seed as a **deliberate** admin action, NOT wired into the FastAPI lifespan the way `seed_admin` is. Default: a thin invocable (e.g. module callable runnable via `python -c "from app.core.db.seed import seed_taxonomy; from app.core.db.session import get_engine; seed_taxonomy(get_engine())"`, or a small `apps/api/scripts/seed_taxonomy.py` guarded by `if __name__ == "__main__":`). Rationale: auto-seeding a fixed taxonomy at every startup/deploy would resurrect owner-deleted groups and fight the admin governance HANDOFF §9 establishes. Document the exact invocation in the function docstring / script. See Story Creation Question #3. (No live execution performed in dev — mechanism + docs only.)
12. **Backend suite green, 3× consecutive identical pass counts** (NFR25-DETERMINISM-1); `ruff check` + `ruff format` clean on `apps/api`. Only the new `test_seed_taxonomy` nodes add to the count; no existing test regresses (the seed function is not invoked by the existing suite or app startup).

## Tasks / Subtasks

- [ ] Task 1 — Author the starter dataset constant (AC: #2, #3, #4, #5)
  - [ ] Add `STARTER_TAXONOMY` to `seed.py` as an ordered structure (list of groups; each group holds an ordered list of tags). Use the values in Dev Notes → Starter dataset. Every `slug` is an explicit ASCII string; `name_en` NOT NULL, `name_pl` set (bilingual); `position`/`group_position` from declared order with `Typ`=0, `Pomieszczenie`=1.
  - [ ] Add a code comment marking the dataset owner-editable (HANDOFF §8) and stating slugs are hand-authored ASCII (never `_slugify(name_pl)`).
- [ ] Task 2 — Implement `seed_taxonomy(engine)` (AC: #1, #5, #6, #7, #8, #9)
  - [ ] Mirror `seed_admin`: `with Session(engine) as session:`; for each group, `select(TagGroup).where(TagGroup.slug == g.slug).first()` → create only if absent; capture the (existing-or-new) group `id`.
  - [ ] For each tag, `select(Tag).where(Tag.slug == t.slug).first()` → create only if absent, setting `group_id` to the resolved group id + `group_position`.
  - [ ] `IntegrityError` → `session.rollback()` and continue (concurrent-insert tolerance, per `seed_admin:23-26`). Choose + document the transaction boundary (AC #9) in the docstring.
  - [ ] Zero references to `Model`, `ModelTag`, `Category`.
- [ ] Task 3 — Admin-run entrypoint (AC: #11)
  - [ ] Provide the deliberate invocation (script or documented one-liner). Do NOT add `seed_taxonomy` to `app/main.py` lifespan. Document the exact command.
- [ ] Task 4 — Tests `apps/api/tests/test_seed_taxonomy.py` (AC: #6, #7, #8, #9, #10)
  - [ ] Copy the `create_engine_for_url` + `init_schema(tmp_path)` fixture shape from `test_seed.py` verbatim (no live DB).
  - [ ] `test_seed_taxonomy_populates_full_set` — every group + tag present exactly once; group/tag slug sets unique; `Typ`/`Pomieszczenie` are positions 0/1.
  - [ ] `test_seed_taxonomy_is_idempotent` — run twice; counts equal; no duplicates.
  - [ ] `test_seed_taxonomy_does_not_clobber_existing` — pre-insert a group/tag with the seeded slug but different names/positions; re-seed; assert the pre-existing row is unchanged (AC #8).
  - [ ] `test_seed_taxonomy_no_model_side_effects` — pre-insert a model (or assert `model_tag` empty); seed; assert no `model_tag` rows + `Model` count unchanged (AC #6).
  - [ ] `test_seed_taxonomy_group_linkage` — every seeded tag has `group_id` pointing at its declared group (AC #5).
  - [ ] Error-atomicity coverage (AC #9): inject a failure mid-seed (e.g. monkeypatch to raise on the Nth row), then re-run cleanly, assert full set present exactly once.
- [ ] Task 5 — Verify (AC: #12)
  - [ ] `ruff check --fix` + `ruff format` on `apps/api`.
  - [ ] Run backend suite 3× (`uv run pytest -q -p no:cacheprovider`), confirm identical all-green counts (prior count + new `test_seed_taxonomy` nodes).
  - [ ] Confirm no live DB touched, no commit/push/deploy performed.
- [ ] Task 6 — Record any residual decisions in `deferred-work.md` if scope shifts (AC: n/a) and answer the Story Creation Questions at hand-off.

## Dev Notes

### Seed mechanism — reuse the `seed_admin` pattern verbatim (do NOT invent a new one)

The repo already has one idempotent seed: `apps/api/app/core/db/seed.py::seed_admin` (lines 9-27). It is the template for this story:

- `with Session(engine) as session:` — plain SQLModel `Session`, not the async app session.
- **Create-if-absent by unique key:** `select(User).where(User.email == email)).first()` → `if existing is not None: return`. For 41.3 the key is `slug` (both `TagGroup.slug` and `Tag.slug` are unique).
- **Never updates existing rows** — `test_seed.py::test_seed_is_idempotent` asserts re-seeding with a *changed* password does **not** change the stored user. This is exactly the update policy AC #8 requires (no-clobber), and it is why the answer to "what happens on re-seed after an admin rename?" is *nothing* — the admin edit wins.
- **Concurrent-insert tolerance:** `except IntegrityError: session.rollback()` treats a race as success. Reuse this so two workers / a double-run can't crash on the unique constraint.

`seed_admin` is wired into app startup (`app/main.py:84`, inside the lifespan, after `init_schema` in non-prod). **Do NOT** wire `seed_taxonomy` there (AC #11 rationale): the admin taxonomy is a curated, mutable dataset (HANDOFF §9 — admin renames/reorders/deletes groups), so auto-seeding at every boot would undo owner deletions. It is an admin-triggered one-off.

### ORM shapes the seed writes (already landed in 41.1)

`apps/api/app/core/db/models/_entities.py:61-96`:

- `TagGroup`: `id` (uuid PK, default factory), `slug: str` (unique via `Index("uq_tag_group_slug", "slug", unique=True)` @ `_entities.py:66-70`), `name_en: str` (NOT NULL), `name_pl: str | None`, `position: int = 0`, `created_at`/`updated_at` (default `_now_utc`). Set `slug`, `name_en`, `name_pl`, `position`; let id/timestamps default.
- `Tag`: `id` (uuid PK), `slug: str` (unique + index), `name_en: str` (NOT NULL), `name_pl: str | None`, `group_id: uuid.UUID | None` (FK `tag_group.id` `ON DELETE SET NULL`), `group_position: int = 0`, timestamps default. Set `slug`, `name_en`, `name_pl`, `group_id` (resolved parent id), `group_position`.
- Both exported from `app.core.db.models` (`__init__.py:26-27`) — import from there, not the private `_entities`.

`name_en` is NOT NULL on both entities → every seed row **must** carry an English name. HANDOFF §8 gives Polish labels only; the English names in the dataset below are mechanically translated from §8 and are **owner-editable** (Story Creation Question #2).

### Starter dataset (derived from HANDOFF §8; owner-editable content, not a frozen AC)

Group order = §8 top-to-bottom; §9.3 pins `Typ`, `Pomieszczenie` as the two primary axes (positions 0,1). Slugs are explicit ASCII (English-derived), globally unique. `group_position` is 0-based within each group in listed order.

| position | group slug | name_en | name_pl |
|---|---|---|---|
| 0 | `type` | Type | Typ |
| 1 | `room` | Room | Pomieszczenie |
| 2 | `system` | System | System |
| 3 | `use-case` | Use case | Zastosowanie |
| 4 | `printer` | Printer | Drukarka |
| 5 | `material` | Material | Materiał |
| 6 | `creator` | Creator (premium) | Twórca (premium) |
| 7 | `level` | Level | Poziom |

Tags (group → ordered tags as `slug` = `name_en` / `name_pl`):

- **type:** `decorations`=Decorations/Dekoracje, `vases`=Vases/Wazony, `containers`=Containers/Pojemniki, `organizers`=Organizers/Organizery, `articulated-figures`=Articulated figures/Figurki ruchome, `holders`=Holders/Uchwyty, `lighting`=Lighting/Oświetlenie, `furniture`=Furniture/Meble, `clips`=Clips/Klipsy, `gadgets`=Gadgets/Gadżety, `cases`=Cases/Etui, `plant-pots`=Plant pots/Doniczki
- **room:** `kitchen`=Kitchen/Kuchnia, `bathroom`=Bathroom/Łazienka, `desk`=Desk/Biurko, `home`=Home/Dom, `car`=Car/Auto, `pets`=Pets/Zwierzęta, `garden`=Garden/Ogród
- **system:** `gridfinity`=Gridfinity/Gridfinity, `multiboard`=Multiboard/Multiboard, `bin-shells`=Bin Shells/Bin Shells
- **use-case:** `repairs`=Repairs/Naprawy, `storage`=Storage/Przechowywanie, `electronics`=Electronics/Elektronika, `soldering`=Soldering/Lutowanie, `inserts`=Inserts/Wkładki, `calibration`=Calibration/Kalibracja
- **printer:** `k1-max`=K1 Max/K1 Max, `accessories`=Accessories/Akcesoria
- **material:** `pla`=PLA/PLA, `petg`=PETG/PETG, `pctg`=PCTG/PCTG, `tpu`=TPU/TPU
- **creator:** `jarek`=Jarek/Jarek  *(§8 lists "Jarek, …" — the ellipsis is illustrative; seed only the confirmed entry. Owner adds more via admin governance.)*
- **level:** `premium`=Premium/Premium

All 8 group slugs distinct; all 36 starter tag slugs distinct — 12 type + 7 room + 3 system + 6 use-case + 2 printer + 4 material + 1 creator + 1 level (verify no collision — e.g. `premium` the tag lives under group `level`, group `creator` is separate). Proper nouns pass through untranslated (`Gridfinity`, `Multiboard`, `K1 Max`, `Jarek`, material codes); `Bin Shells` is already English.

### Slug determinism — why explicit, not `_slugify(name_pl)` (AC #3)

`apps/api/app/modules/sot/admin_service.py:65-77`: `_SLUG_RE = re.compile(r"[^a-z0-9]+")`, `_slugify` = `_SLUG_RE.sub("-", text.lower()).strip("-")`. On Polish diacritics this is lossy and collision-prone: `"Łazienka".lower()="łazienka"` → `"-azienka"`→`"azienka"`; `"Oświetlenie"`→`"o-wietlenie"`; `"Gadżety"`→`"gad-ety"`. That is unacceptable for stable, human-meaningful, unique slugs. The seed therefore ships **hand-authored ASCII slugs** (English-derived, like `_slugify(name_en)` would give but pinned so they never drift). Do not import or call `_slugify` here.

### Files being created/modified — current state & what must be preserved

- **MODIFY** `apps/api/app/core/db/seed.py` — add `STARTER_TAXONOMY` constant + `seed_taxonomy(engine)`. Preserve `seed_admin` untouched. Keep imports additive (`TagGroup`, `Tag`, `IntegrityError` already imported / add as needed).
- **CREATE** `apps/api/tests/test_seed_taxonomy.py` — mirror `test_seed.py` fixture shape (tmp_path SQLite + `init_schema`, no live DB).
- **CREATE (optional per AC #11)** `apps/api/scripts/seed_taxonomy.py` — thin `__main__` guard invoking `seed_taxonomy(get_engine())`; or document the one-liner instead. No new CLI dependency (repo has no typer/click).
- **MODIFY** `_bmad-output/implementation-artifacts/sprint-status.yaml` — 41-3 status transitions during dev (ready-for-dev → in-progress → review → done) + `last_updated`.
- **Do NOT modify** `_entities.py`, `app/main.py` lifespan, any migration, `admin_service.py`, `sot/`, `share/`, or any `Category`-referencing module. No frontend changes (E43+ owns FE). No planning monoliths (`epics.md`, sprint-change-proposal).

### Testing standards

- Backend pytest, `asyncio_mode="auto"`, but this is a **plain sync** test using a tmp-path SQLite engine — copy the fixture idiom from `test_seed.py:9-11` (`create_engine_for_url(f"sqlite:///{tmp_path}/seed.db")` → `init_schema(engine)`). No `TestClient`, no app `session` fixture, no async, **no live DB** (AC: "no live DB execution during dev").
- `init_schema()` = `SQLModel.metadata.create_all()` (`session.py:31`), so the ORM-defined `tag_group`/`tag` tables exist in the throwaway DB with **no** Alembic run — same as every existing seed/entity test.
- Determinism (NFR25-DETERMINISM-1): run the full backend suite 3× with identical green counts before marking done. `ruff` clean (`E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312).
- Error-atomicity test (AC #9): inject the fault via `monkeypatch`/a raising stub on the Nth insert, assert the re-run converges. Do not rely on wall-clock or ordering nondeterminism.

### Project Structure Notes

- Seed logic belongs in `app/core/db/seed.py` (established location; `seed_admin` lives there). Tests in `apps/api/tests/test_*.py`. Optional script under `apps/api/scripts/` (create the dir if adopting the script form). No variance from project structure.
- The sprint-status key `41-3-optional-starter-taxonomy-seed` says "optional" — treat as a **slug only**. Per operator re-scope this story is in-scope and required to close E41; "optional" reflects the epic-sketch phrasing (§Story 41.3 "Optional/separate seed"), i.e. optional *relative to the migration*, not skippable.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 41.3 — Optional starter-taxonomy seed (line ~4214)] — "Optional/separate seed of the SCP §8 starter taxonomy as `tag_group` + `tag` rows … Idempotent; no per-model assignment (models stay untagged)."
- [Source: docs/design/HANDOFF-tagi-fasetowe.md#8 — Proponowana taksonomia startowa] — the starter taxonomy content (owner-editable: "do edycji przez właściciela").
- [Source: docs/design/HANDOFF-tagi-fasetowe.md#9 — Decyzje (rozstrzygnięte 2026-07-16)] — §9.2 creators are a separate facet (no tag prefixes); §9.3 `Typ`/`Pomieszczenie` are the primary axes (first two by position); §9.4 `TagGroup` is a table, admin-managed (rename/reorder) → informs the no-clobber update policy.
- [Source: docs/design/HANDOFF-tagi-fasetowe.md#1 + #5] — models are reset to untagged after migration (no data migration; `untagged` triage) → seed creates NO model assignments.
- [Source: apps/api/app/core/db/seed.py:9-27] — `seed_admin`: idempotent create-if-absent + `IntegrityError` rollback tolerance — the mechanism to mirror.
- [Source: apps/api/tests/test_seed.py] — fixture shape (`create_engine_for_url` + `init_schema` on tmp_path, no live DB) + `test_seed_is_idempotent` (no-clobber semantics to replicate).
- [Source: apps/api/app/core/db/models/_entities.py:61-96] — `TagGroup` + `Tag` field shapes; `uq_tag_group_slug` @ :66; `Tag.slug` unique @ :83; `Tag.group_id` FK SET NULL.
- [Source: apps/api/app/core/db/models/__init__.py:26-27,57-58] — `TagGroup`/`Tag` public exports.
- [Source: apps/api/app/core/db/session.py:12,31,43] — `create_engine_for_url`, `init_schema` (`create_all`), `get_engine`.
- [Source: apps/api/app/main.py:82-88] — `seed_admin` wired into lifespan after `init_schema` (why `seed_taxonomy` is deliberately NOT wired there).
- [Source: apps/api/app/modules/sot/admin_service.py:65-77] — `_slugify`/`_SLUG_RE` diacritic-lossy behavior (why the seed uses explicit ASCII slugs).
- [Source: _bmad-output/implementation-artifacts/41-2-alembic-0018-facet-tags-drop-category.md] — 41.2 migration this seed runs on top of; `deferred-work.md` for the still-owed E42 destructive drop (out of scope here).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-07-18 — Story 41.3 created via `bmad-create-story` (Create). Re-scoped back into E41 after the prior premature closeout deferred it to E42 (`DEFER_41_3` reversed). Idempotent admin-run `seed_taxonomy` (TagGroup+Tag only, no model assignments) on `0018_facet_tags`; deterministic explicit-ASCII slugs + declared ordering + bilingual names; idempotency / no-duplicate / no-clobber-update / error-atomicity tests; no live DB in dev. Status → ready-for-dev pending validation.

## Story Creation Questions / Decisions for Operator

1. **Update policy on re-seed (default chosen — please confirm).** The seed is **create-if-absent by slug and never updates/deletes an existing row** (mirrors `seed_admin` + `test_seed_is_idempotent`; honors HANDOFF §9 admin governance of renames/reorders). Consequence: once seeded, editing a `name_en`/`name_pl`/`position` in `STARTER_TAXONOMY` and re-running does **not** propagate to rows that already exist — the admin/DB value wins. Alternative (rejected as default): upsert names/positions on re-seed, which would clobber admin edits. Confirm no-clobber, or request upsert-on-slug.
2. **Bilingual English names + exact starter content (derived, owner-editable).** HANDOFF §8 gives Polish only and is explicitly owner-editable. The English names + the group/tag membership in Dev Notes → Starter dataset are **mechanically derived from §8** and shipped as an editable data constant, not frozen ACs. Dev proceeds on this dataset; the owner can edit strings/rows in `STARTER_TAXONOMY` later without a story change. Confirm the derived set is acceptable as the starter, or supply an authoritative EN/PL list. (Not a blocker — the seed *mechanism* is independent of the exact strings.)
3. **Admin-run wiring (default chosen — please confirm).** The seed is exposed as a **deliberate** admin action (documented one-liner or `scripts/seed_taxonomy.py __main__`), **not** wired into the FastAPI lifespan like `seed_admin`, so it can't resurrect owner-deleted groups on redeploy. Confirm, or request lifespan auto-seed (accepting that auto-seed re-creates any group an admin later deletes).
4. **Scope boundary confirmation:** this story creates `TagGroup` + `Tag` rows only — **zero** model/tag assignments, **zero** `Category`/destructive DDL (that stays owed by the E42 cut-over per `deferred-work.md`). Confirm E41 closes on 41.3 done, and the E42 retrospective/cut-over still owns `0019_drop_category`.
