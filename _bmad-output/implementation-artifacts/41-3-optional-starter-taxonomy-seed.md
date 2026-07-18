---
baseline_commit: efc270a
---

# Story 41.3: Optional starter-taxonomy seed (idempotent admin-run `TagGroup` + `Tag` population; no model assignments)

Status: done

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

- [x] Task 1 — Author the starter dataset constant (AC: #2, #3, #4, #5)
  - [x] Add `STARTER_TAXONOMY` to `seed.py` as an ordered structure (list of groups; each group holds an ordered list of tags). Use the values in Dev Notes → Starter dataset. Every `slug` is an explicit ASCII string; `name_en` NOT NULL, `name_pl` set (bilingual); `position`/`group_position` from declared order with `Typ`=0, `Pomieszczenie`=1.
  - [x] Add a code comment marking the dataset owner-editable (HANDOFF §8) and stating slugs are hand-authored ASCII (never `_slugify(name_pl)`).
- [x] Task 2 — Implement `seed_taxonomy(engine)` (AC: #1, #5, #6, #7, #8, #9)
  - [x] Mirror `seed_admin`: `with Session(engine) as session:`; for each group, `select(TagGroup).where(TagGroup.slug == g.slug).first()` → create only if absent; capture the (existing-or-new) group `id`.
  - [x] For each tag, `select(Tag).where(Tag.slug == t.slug).first()` → create only if absent, setting `group_id` to the resolved group id + `group_position`.
  - [x] `IntegrityError` → `session.rollback()` and continue (concurrent-insert tolerance, per `seed_admin:23-26`). Choose + document the transaction boundary (AC #9) in the docstring.
  - [x] Zero references to `Model`, `ModelTag`, `Category`.
- [x] Task 3 — Admin-run entrypoint (AC: #11)
  - [x] Provide the deliberate invocation (script or documented one-liner). Do NOT add `seed_taxonomy` to `app/main.py` lifespan. Document the exact command.
- [x] Task 4 — Tests `apps/api/tests/test_seed_taxonomy.py` (AC: #6, #7, #8, #9, #10)
  - [x] Copy the `create_engine_for_url` + `init_schema(tmp_path)` fixture shape from `test_seed.py` verbatim (no live DB).
  - [x] `test_seed_taxonomy_populates_full_set` — every group + tag present exactly once; group/tag slug sets unique; `Typ`/`Pomieszczenie` are positions 0/1.
  - [x] `test_seed_taxonomy_is_idempotent` — run twice; counts equal; no duplicates.
  - [x] `test_seed_taxonomy_does_not_clobber_existing` — pre-insert a group/tag with the seeded slug but different names/positions; re-seed; assert the pre-existing row is unchanged (AC #8).
  - [x] `test_seed_taxonomy_no_model_side_effects` — pre-insert a model (or assert `model_tag` empty); seed; assert no `model_tag` rows + `Model` count unchanged (AC #6).
  - [x] `test_seed_taxonomy_group_linkage` — every seeded tag has `group_id` pointing at its declared group (AC #5).
  - [x] Error-atomicity coverage (AC #9): inject a failure mid-seed (e.g. monkeypatch to raise on the Nth row), then re-run cleanly, assert full set present exactly once.
- [x] Task 5 — Verify (AC: #12)
  - [x] `ruff check --fix` + `ruff format` on `apps/api`.
  - [x] Run backend suite 3× (`uv run pytest -q -p no:cacheprovider`), confirm identical all-green counts (prior count + new `test_seed_taxonomy` nodes).
  - [x] Confirm no live DB touched, no commit/push/deploy performed.
- [x] Task 6 — Record any residual decisions in `deferred-work.md` if scope shifts (AC: n/a) and answer the Story Creation Questions at hand-off.

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

claude-opus-4-8[1m] (BMad `bmad-dev-story` workflow)

### Debug Log References

- RED: `uv run pytest tests/test_seed_taxonomy.py` → `ImportError: cannot import name 'STARTER_TAXONOMY' from 'app.core.db.seed'` (collection error, 1 error) before implementation existed.
- GREEN: after adding `STARTER_TAXONOMY` + `seed_taxonomy` → `11 passed in 2.73s`.
- `ruff check` + `ruff format --check` clean on the three touched Python files (one `ruff format` pass applied to `seed.py`).
- AC12 determinism — full backend suite `uv run pytest -q -p no:cacheprovider` run 3× consecutively:
  - Run 1/3: `1682 passed, 3 skipped` (369.56s)
  - Run 2/3: `1682 passed, 3 skipped` (379.22s)
  - Run 3/3: `1682 passed, 3 skipped` (381.15s)
  - Baseline before this story: 1671 passed + 3 skipped (1674 collected). Delta = +11 passing nodes (the new `test_seed_taxonomy` module), zero regressions.
- Post-review [Review][Patch] pass (2026-07-19):
  - RED (item 5): `test_script_main_prints_truthful_post_condition_count` failed first — `main()` took no `engine` arg and printed nothing. GREEN after `main(engine=None)` + DB-queried count print.
  - Focused module after all 5 patches: `uv run pytest tests/test_seed_taxonomy.py -q` → `14 passed` (was 11; +2 real-IntegrityError race tests + 1 script test; items 1/2/4 hardened in place).
  - `ruff check` + `ruff format --check` clean on the 3 touched files.
  - AC12 re-run (test set changed) — full backend suite `uv run pytest -q -p no:cacheprovider` 3× consecutive: `1685 passed, 3 skipped` ×3 (381.02s / 379.79s / 381.25s) — evidence `.hermes/run-logs/E41.3-final-backend-3x-20260719_002145.log`.

### Completion Notes List

- Implemented `seed_taxonomy(engine)` in `apps/api/app/core/db/seed.py` mirroring `seed_admin`: create-if-absent by unique `slug`, never updates/deletes an existing row, concurrent-insert `IntegrityError` → `session.rollback()` treated as success. Two private helpers (`_upsert_absent_group`, `_insert_absent_tag`) keep the group/tag loops readable.
- Transaction boundary (AC #9): **per-row commit** (matches `seed_admin`'s single-entity commit). Documented in the `seed_taxonomy` docstring. Error-atomicity proved by `test_seed_taxonomy_converges_after_midrun_failure` (monkeypatched `Session.commit` raises on the 5th commit; a clean re-run converges to the full 8-group/36-tag set exactly once, no orphans).
- `STARTER_TAXONOMY` = exact §8 starter set: 8 groups / 36 tags. Group order `Typ`(0)/`Pomieszczenie`(1) primary axes then §8 order; slugs are hand-authored ASCII (never `_slugify(name_pl)`); bilingual names with mechanical EN translations; `group_position` derived dense 0-based from declared tag order. Owner-editable comment added per HANDOFF §8.
- Zero `Model`/`ModelTag`/`Category` writes (asserted by `test_seed_taxonomy_no_model_side_effects`). No ORM/schema/migration change; `_entities.py`, `app/main.py` lifespan, migrations, `admin_service.py` untouched.
- AC #11 entrypoint: `apps/api/scripts/seed_taxonomy.py` (`__main__`-guarded, `python -m scripts.seed_taxonomy`) — deliberate admin action, NOT wired into the FastAPI lifespan; documented one-liner alternative in both script + function docstring.
- No live DB touched; no commit/push/deploy performed. All verification against throwaway tmp_path SQLite (`init_schema` `create_all`, no Alembic).
- Operator decisions (Story Creation Questions) proceeded on the accepted defaults: #1 no-clobber (create-if-absent, never update), #2 derived owner-editable EN/PL dataset, #3 deliberate admin-run entrypoint (not lifespan), #4 scope = TagGroup+Tag only (no `Category`/destructive DDL; `0019_drop_category` stays owed by E42). No `deferred-work.md` change needed — no scope shift.

**Post-review [Review][Patch] pass (2026-07-19, bounded — no product-scope change):** resolved all 5 unchecked `[Review][Patch]` findings; the 2 `[Review][Defer]` items remain deferred (unchanged). Lifespan/schema/migration/model-assignment behavior untouched.
- (1) Error-atomicity now injected mid-TAG-phase (11th commit) so the no-orphan property is genuinely exercised — asserts the committed tag subset all link to their parent group, then a clean re-run converges to 8/36 exactly once (`test_seed_taxonomy_converges_after_midtag_failure`).
- (2) `test_seed_taxonomy_no_model_side_effects` now also asserts `Category` count unchanged (== 1).
- (3) Added `test_upsert_absent_group_tolerates_real_integrity_error` + `test_insert_absent_tag_tolerates_real_integrity_error`: a "racer" session pre-commits the conflicting slug and the helper's existence-check `session.exec` is monkeypatched to miss, so the real INSERT raises a **genuine** `IntegrityError` — driving the group `.one()` re-query/adopt path and the tag rollback path without threads or a live DB.
- (4) `test_seed_taxonomy_is_idempotent` now snapshots a standard seeded group + tag and asserts byte-for-byte preservation (same id/names/positions) across the 2nd identical run.
- (5) `scripts/seed_taxonomy.py::main` prints a DB-queried post-condition count (`seeded taxonomy: N groups / M tags present`, from `select(...)` not constants) and accepts an injectable `engine`; `test_script_main_prints_truthful_post_condition_count` drives it with a temp engine (no live DB).
- Focused module: 14 passed (was 11; +3 nodes: 2 IntegrityError + 1 script; items 1/2/4 strengthened in place). `ruff check` + `ruff format --check` clean on `seed.py`, `scripts/seed_taxonomy.py`, `tests/test_seed_taxonomy.py`. No commit/push/deploy; no live DB.

### File List

- `apps/api/app/core/db/seed.py` — MODIFIED (added `STARTER_TAXONOMY` constant + `seed_taxonomy` and helpers; `seed_admin` untouched; imports `uuid`, `Tag`, `TagGroup` added). Post-review pass: unchanged (helpers already correct; only test coverage of their `IntegrityError` branches was added).
- `apps/api/scripts/seed_taxonomy.py` — CREATED (deliberate admin-run entrypoint). Post-review pass: MODIFIED — `main()` gained an injectable `engine` param and prints a DB-queried post-condition count (`select(TagGroup)`/`select(Tag)`, not constants).
- `apps/api/tests/test_seed_taxonomy.py` — CREATED then post-review-HARDENED (now 14 tests): full-population, ordering, group-position density, group linkage, idempotency (now + standard-row preservation across 2nd run), no-clobber, no model side-effects (now + `Category` count unchanged), error-atomicity (now mid-TAG-phase, non-orphan-verified), slug uniqueness, dataset shape, uuid ids, **real-`IntegrityError` group + tag race branches**, **script `main` truthful-count**.
- `_bmad-output/implementation-artifacts/41-3-optional-starter-taxonomy-seed.md` — MODIFIED (task boxes, Dev Agent Record, File List, Change Log, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED (41-3 ready-for-dev → in-progress → review)

## Change Log

- 2026-07-18 — Story 41.3 created via `bmad-create-story` (Create). Re-scoped back into E41 after the prior premature closeout deferred it to E42 (`DEFER_41_3` reversed). Idempotent admin-run `seed_taxonomy` (TagGroup+Tag only, no model assignments) on `0018_facet_tags`; deterministic explicit-ASCII slugs + declared ordering + bilingual names; idempotency / no-duplicate / no-clobber-update / error-atomicity tests; no live DB in dev. Status → ready-for-dev pending validation.
- 2026-07-18 — Story 41.3 implemented via `bmad-dev-story` (test-first RED→GREEN). Added `STARTER_TAXONOMY` (8 groups/36 tags) + `seed_taxonomy` (per-row commit, create-if-absent, no-clobber, IntegrityError tolerance) to `seed.py`; added `scripts/seed_taxonomy.py` admin-run entrypoint (not lifespan); added `tests/test_seed_taxonomy.py` (11 tests). ruff clean; backend suite green 3× consecutive (1682 passed, 3 skipped; +11 vs baseline, no regressions). No schema/migration/ORM change, no `Model`/`ModelTag`/`Category` writes, no live DB, no commit/push/deploy. Status → review.
- 2026-07-19 — Bounded post-review [Review][Patch] pass via `bmad-dev-story`. Resolved all 5 unchecked `[Review][Patch]` findings without expanding product scope; 2 `[Review][Defer]` items remain deferred. Test-hardening only + one script ergonomics change (`scripts/seed_taxonomy.py::main` now injectable-engine + truthful DB-queried post-condition count). `test_seed_taxonomy.py` 11 → 14 tests: mid-TAG-phase error-atomicity with non-orphan verification; `Category`-count assertion; two real-`IntegrityError` race-branch tests (group `.one()` re-query + tag rollback, deterministic, no live DB/threads); standard-row preservation across a 2nd idempotent run; script truthful-count test. No lifespan/schema/migration/ORM/model-assignment change. ruff clean; focused module 14 passed; backend suite 3× consecutive: `1685 passed, 3 skipped` ×3 (evidence `.hermes/run-logs/E41.3-final-backend-3x-20260719_002145.log`; baseline 1671 + 14 new nodes = 1685). No commit/push/deploy, no live DB. Status remains review.

## Review Findings

Independent native BMAD code review (`bmad-code-review`, fresh context, implementer transcript NOT used) — 2026-07-19. Layers run: Acceptance Auditor (full 12-AC audit), Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`). All 3 layers completed; none failed.

**Verdict: APPROVE.** All 12 acceptance criteria PASS. Dataset is exactly 8 groups / 36 tags (12 type + 7 room + 3 system + 6 use-case + 2 printer + 4 material + 1 creator + 1 level), all slugs ASCII/lowercase/globally-unique, `type`=pos 0 / `room`=pos 1. `seed_taxonomy` faithfully mirrors `seed_admin` (create-if-absent by `slug`, never updates/deletes, `IntegrityError`→`rollback` tolerance — mandated by AC #1). Zero `Model`/`ModelTag`/`Category` references in `seed.py` (verified by grep). NOT wired into `app/main.py` lifespan (verified: `main.py` imports/calls only `seed_admin`). `scripts/__init__.py` exists so `python -m scripts.seed_taxonomy` resolves. No blocking (high) findings. Findings below are test-hardening / ergonomics recommendations — none block the merge; addressing them is at operator discretion.

- [x] [Review][Patch] Error-atomicity test injects the fault in the GROUP phase, not the tag phase — `no-orphan-tags` assertion is vacuously true [apps/api/tests/test_seed_taxonomy.py:183] — `seed_taxonomy` commits all 8 groups first (commits 1-8) then 36 tags (commits 9-44); injecting at `state["n"] == 5` fails on the `printer` group with **zero tags committed**, so the final `assert tag.group_id is not None` (test:202-203) can never fail and the mid-tag-phase convergence path is never exercised. AC #9's letter is still met (post-rerun counts asserted exactly 8/36), and the per-row-commit + create-if-absent code is genuinely convergent — but to actually test the orphan property, inject at commit ~11 (a few tags in) and assert the seeded subset re-converges. Severity: medium (test quality). **RESOLVED 2026-07-19:** renamed to `test_seed_taxonomy_converges_after_midtag_failure`; fault now injected at the **11th commit** (mid-TAG-phase: 8 groups + 2 tags committed). Test now asserts a NON-EMPTY strict subset of tags is present after the fault and that **every committed tag links to its declared parent group** (`group_id_by_slug[_TAG_PARENT_SLUG[...]]`) — the no-orphan property is now genuinely exercised — then re-runs clean and asserts full 8/36 convergence exactly once.
- [x] [Review][Patch] `test_seed_taxonomy_no_model_side_effects` never asserts `Category` count is unchanged [apps/api/tests/test_seed_taxonomy.py:155-170] — AC #6 calls out zero `Category` writes and the test pre-creates a `Category("root")` fixture specifically to be checked, but only asserts `ModelTag == 0` and `Model == 1`. Add `assert len(s.exec(select(Category)).all()) == 1`. Seed provably never touches `Category`, so this is a missing assertion, not a live bug. Severity: low. **RESOLVED 2026-07-19:** added `assert len(s.exec(select(Category)).all()) == 1` — the pre-created root Category count is now asserted unchanged after seeding.
- [x] [Review][Patch] Concurrency `IntegrityError` branches have zero test coverage [apps/api/app/core/db/seed.py:208-212, 233-236] — the `.one()` re-query (group helper) and the tag rollback exist solely for the concurrent-insert race, yet no test drives a real `IntegrityError` (the mid-run test raises `RuntimeError`, which bypasses the handler). A regression in the `.one()` path would pass CI. Consistent with the repo's existing `seed_admin` (its `IntegrityError` branch is likewise untested), so low priority. Severity: low. **RESOLVED 2026-07-19:** added two deterministic tests — `test_upsert_absent_group_tolerates_real_integrity_error` and `test_insert_absent_tag_tolerates_real_integrity_error`. Each pre-commits a conflicting slug via a separate "racer" session, then monkeypatches the helper's FIRST `session.exec` (the existence check) to miss the row, so the helper's real INSERT raises a **genuine** unique-constraint `IntegrityError`. The group test proves the post-rollback `.one()` re-query adopts the racer's row id (no duplicate, no clobber); the tag test proves the rollback branch swallows the error (no raise, no duplicate). No threads, no live DB.
- [x] [Review][Patch] `test_seed_taxonomy_is_idempotent` asserts only counts + slug-sets, not name/position preservation on the 2nd run [apps/api/tests/test_seed_taxonomy.py:100-111] — preservation is covered only for the CUSTOM=99 row in `test_seed_taxonomy_does_not_clobber_existing`, never for a standard seeded row across a second identical run. Low; create-if-absent makes this correct-by-construction. Severity: low. **RESOLVED 2026-07-19:** `test_seed_taxonomy_is_idempotent` now snapshots a standard seeded group (`type`) and tag (`vases`) — `(id, name_en, name_pl, position/group_position)` — after run 1 and asserts the tuples are byte-for-byte identical after run 2 (same `id` → not recreated; same names/positions → not updated).
- [x] [Review][Patch] Admin-run script emits no success signal / post-condition count [apps/api/scripts/seed_taxonomy.py:29-30] — for a deliberate one-shot admin action, `main()` prints nothing; a partial seed is indistinguishable from a full one to the operator. Consider printing `"seeded N groups / M tags"` or a final `SELECT count`. Ergonomics only. Severity: low. **RESOLVED 2026-07-19:** `main()` now queries the DB after seeding and prints `seeded taxonomy: {N} groups / {M} tags present` — counts are read from `select(TagGroup)`/`select(Tag)` (actual rows), NOT the dataset constants, so a partial seed is visibly distinguishable. `main()` also gained an injectable `engine` param (defaults to `get_engine()`); `test_script_main_prints_truthful_post_condition_count` drives it with a temp SQLite engine (no live DB) and asserts the printed counts equal the real DB totals AND the full `8 groups / 36 tags`.
- [x] [Review][Defer] Unqualified `except IntegrityError` in both helpers masks non-slug integrity errors [apps/api/app/core/db/seed.py:233-236, 208-212] — `_insert_absent_tag` swallows ANY `IntegrityError` (e.g. an FK violation if a group is concurrently deleted between the group loop and the tag loop) and reports success → silent tag drop that a re-run repeats; `_upsert_absent_group`'s `.one()` re-query can raise `NoResultFound` on a non-slug error. **By-design / spec-mandated:** AC #1 explicitly requires mirroring `seed_admin`'s bare `except IntegrityError: rollback` ("same rationale as seed_admin"). Requires a concurrent group deletion during a single deliberate one-shot admin run — negligible window; the group `TagGroup` schema has only the slug-unique constraint so a non-slug group `IntegrityError` is essentially unreachable with the current dataset. Deferred, not caused by this change's design latitude. Severity: low.
- [x] [Review][Defer] Idempotency keyed on `slug` only — a DB-side slug rename (not name rename) causes re-seed to recreate a duplicate group with orphaned children [apps/api/app/core/db/seed.py:196,220] — outside the documented governance model (admins rename display names / reorder, not slugs; slug is the stable identity key). Informational. Severity: low.

### Re-review note (native BMAD, focused resolution audit) — 2026-07-19

Fresh `bmad-code-review` re-audit scoped to the five resolved `[Review][Patch]` findings (correctness + no regression). **Verdict: APPROVE — all five resolutions correct, no regression introduced.**

- **(1) Mid-tag failure / non-orphan** — `test_seed_taxonomy_converges_after_midtag_failure` injects the fault on the **11th** commit. `seed_taxonomy` commits 8 groups (commits 1–8) then tags (commits 9+), so commit 11 lands after 8 groups + 2 tags (`decorations`, `vases` under `type`); the 3rd tag's `add` is rolled back when the `RuntimeError` unwinds the `with Session` block. `0 < len(partial_tags) < 36` is deterministic (=2), and the per-committed-tag parent-link assertion is now genuinely exercised. Clean re-run converges to 8/36 exactly once. **Correct.**
- **(2) Category invariance** — `assert len(select(Category)) == 1` added against the pre-created `root` fixture; `seed_taxonomy` provably never references `Category`. **Correct.**
- **(3) Real IntegrityError branches** — group test: racer pre-commits `type`, existence check monkeypatched to miss (1st `exec`), real INSERT raises a genuine unique-constraint `IntegrityError`; the `.one()` re-query (2nd `exec`, real) adopts the racer id (1 row, `name_en == "RACER"`). Tag test: racer pre-commits `vases`, INSERT raises, rollback swallows (no raise, 1 row, racer untouched). Instance-level `session.exec` patch shadows the bound method correctly; deterministic, no threads, no live DB. Drives both branches that `RuntimeError` bypassed. **Correct.**
- **(4) Standard-row preservation** — `test_seed_taxonomy_is_idempotent` snapshots `type`/`vases` tuples after run 1 and asserts byte-for-byte identity (same `id` → not recreated; same names/positions → not updated) after run 2. **Correct.**
- **(5) Injectable script main + DB-queried count** — `main(engine=None)` defaults to `get_engine()` (real admin-run path preserved), queries counts via `select(TagGroup)`/`select(Tag)` (actual rows, not constants), prints truthful `N groups / M tags`; test drives an injected temp engine and asserts printed == real DB totals == `8 groups / 36 tags`. **Correct.**

Cross-checks: production `seed.py` unchanged in the patch pass (only test coverage + script ergonomics added). No unchecked `[Review][Patch]` remains (all 5 `[x]`; 2 `[Review][Defer]` remain deferred by design). `ruff check` + `ruff format --check` clean on the 3 touched files. Backend evidence 3× `1685 passed, 3 skipped` in `.hermes/run-logs/E41.3-final-backend-3x-20260719_002145.log` (baseline 1671 + 14 nodes = 1685); focused module re-run this session: `14 passed`. Backfilled the two stale `*_COUNTS_PENDING` placeholders above with these figures. No production/test code edited; no commit/push/deploy; no live DB touched.

## Story Creation Questions / Decisions for Operator

1. **Update policy on re-seed (default chosen — please confirm).** The seed is **create-if-absent by slug and never updates/deletes an existing row** (mirrors `seed_admin` + `test_seed_is_idempotent`; honors HANDOFF §9 admin governance of renames/reorders). Consequence: once seeded, editing a `name_en`/`name_pl`/`position` in `STARTER_TAXONOMY` and re-running does **not** propagate to rows that already exist — the admin/DB value wins. Alternative (rejected as default): upsert names/positions on re-seed, which would clobber admin edits. Confirm no-clobber, or request upsert-on-slug.
2. **Bilingual English names + exact starter content (derived, owner-editable).** HANDOFF §8 gives Polish only and is explicitly owner-editable. The English names + the group/tag membership in Dev Notes → Starter dataset are **mechanically derived from §8** and shipped as an editable data constant, not frozen ACs. Dev proceeds on this dataset; the owner can edit strings/rows in `STARTER_TAXONOMY` later without a story change. Confirm the derived set is acceptable as the starter, or supply an authoritative EN/PL list. (Not a blocker — the seed *mechanism* is independent of the exact strings.)
3. **Admin-run wiring (default chosen — please confirm).** The seed is exposed as a **deliberate** admin action (documented one-liner or `scripts/seed_taxonomy.py __main__`), **not** wired into the FastAPI lifespan like `seed_admin`, so it can't resurrect owner-deleted groups on redeploy. Confirm, or request lifespan auto-seed (accepting that auto-seed re-creates any group an admin later deletes).
4. **Scope boundary confirmation:** this story creates `TagGroup` + `Tag` rows only — **zero** model/tag assignments, **zero** `Category`/destructive DDL (that stays owed by the E42 cut-over per `deferred-work.md`). Confirm E41 closes on 41.3 done, and the E42 retrospective/cut-over still owns `0019_drop_category`.
