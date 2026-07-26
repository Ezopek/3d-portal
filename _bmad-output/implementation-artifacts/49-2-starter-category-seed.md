---
baseline_commit: 88a683a51916aa02a57f085471963de4320558e6
create_validate_baseline_commit: df922f955fea42bbdbc76827406b008d28733718
---

# Story 49.2: Idempotent starter-category seed

Status: done

<!-- Provenance. CREATE: native bmad-create-story (action=create, menu CS), 2026-07-26, Claude Opus 5 agent session, routed via native bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story`; baseline HEAD df922f9 on branch docs/init26-e49-2-create-validate, working tree clean. VALIDATE: native bmad-create-story (action=validate, menu VS) COMPLETED 2026-07-26 in a fresh independent context at the same baseline -> VERDICT PASS, status ready-for-dev; amendments and the independent re-trace are recorded in §16. NO Ezop review or sign-off is recorded or implied. The native verdict is Claude/BMAD only. Laura/controller later granted this story's G26-DEVGO under the standing Initiative 26 authorization; that controller decision is recorded below and is not an Ezop signature or review. DEV: native bmad-dev-story (menu DS), 2026-07-26, Claude Opus 5 agent session, on branch feat/E49.2-starter-category-seed in worktree /home/ezop/worktrees/3d-portal-e49-2-dev at implementation baseline 88a683a51916aa02a57f085471963de4320558e6 (`docs: create and validate story 49.2`), working tree clean at start. `baseline_commit` front matter now records that ACTUAL implementation baseline; the create/validate source baseline df922f9 is preserved as historical provenance in `create_validate_baseline_commit`. Implementer only: no native code review, no Aider review, no commit/push/merge/deploy, no live database access. See §15. -->

## 1. Story

As the **catalog owner**,
I want **the eight approved starter browse categories to be created in the database by a deliberate, re-runnable admin command that never duplicates a row and never overwrites anything I have edited**,
so that **the browse taxonomy exists as real content ready for curation, without a schema change and without any model being auto-assigned to a category.**

**Epic:** E49 — Browse-category data + additive API foundation (backend).
**Story key:** `49-2-starter-category-seed` *(renumbered from 49.3 by the 2026-07-26 controller review)*.
**Requirements:** FR26-CAT-1 (content half), FR26-GOV-1 (inclusion criterion stored with the entity), NFR26-DETERMINISM-1.
**Architecture:** Decision AX supplies the entity shape this story populates. **Decision AZ is explicitly out of scope** — `0020` is shipped and byte-frozen here.
**Depends on:** Story 49.1 (`done`, ff-merged as `df922f9`). Nothing in E49 depends on this story except curation itself; 49.3–49.5 read/write the same table but do not require seeded rows.

## 2. Gate and authorization posture (truthful)

- **G26-CAT-SET — closed** 2026-07-26 by commit `48db6bb` (`ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md`). The eight categories, their slugs, labels, order and one-sentence inclusion criteria are fixed content, not a story-time judgement call. [Source: `epics.md:4475`; `sprint-status.yaml:380`]
- **The real-distribution evidence obligation that `EXPERIENCE.md:192` left open is DISCHARGED for all eight categories** — read-only, by the controller, before this pass, and re-traced independently at validation. See §6 F-1 and F-3 for the full proof and its one fragile row. This story **cites** that evidence; it does not re-derive it, and it does not re-open the live database.
- **G26-MIGRATE** — does not apply. This story ships **no DDL at all**: no new revision, no edit to `0020`, no `alembic` invocation in any test.
- **G26-DEVGO — GRANTED** for this story on 2026-07-26 by **Laura/controller**, under Ezop's standing Initiative 26 authorization, after `bmad-create-story:validate` returned `PASS`. Implementation therefore proceeded in this dev-story pass. **This is a controller decision only — it is NOT an Ezop signature, NOT an Ezop review, and NOT a claim that any human read this document or the diff.** The grant is scoped to the three execution-critical product files plus the two workflow records in §7; it authorizes no model assignment, no boot auto-seeding, no migration edit, no API/UI/admin CRUD, no dependency change, no live database access, no production seeding, and no push/merge/deploy. The gate's open-at-validation-time state is preserved historically in §16.
- **G26-ROUTE-PATH, G26-UXGATE, G26-SCP-RATIFY** — closed; none of them gate this story. G26-LIB (E53) is unrelated.
- **This story requires no live-DB action of any kind.** Every test runs against a throwaway `tmp_path` SQLite database built by `init_schema` (`session.py:31`), exactly as `test_seed_taxonomy.py` does.
- **Live posture at this pass (controller-supplied, not re-measured here).** Story 49.1 is merged, **pushed and deployed successfully**. Live Alembic revision is `0020_browse_categories`; both `browse_category` and `model_browse_category` exist; **132 `model` rows preserved**; `browse_category` count **0**; `model_browse_category` count **0**; integrity check ok; foreign-key violations **0**. Consequence for this story: the target table exists live and is empty, so the eventual admin-run seed will be a pure eight-row insert — but **the seed is not run against the live database during dev or review**; that invocation is a controller/admin action after merge.

## 3. Binding constraints (carried verbatim; a violation is a story defect, not a preference)

1. Seed **exactly** the approved eight categories in §4 AC-1 — not seven, not nine, not a reordering, not a "close enough" label.
2. **The stable `slug` is the idempotency key.** Existence is decided by `slug` and by nothing else.
3. **Create missing rows only.** A re-run must not duplicate a row and must not overwrite an existing row's `name_en`, `name_pl`, `description_en`, `description_pl`, `inclusion_criterion`, `position`, `parent_id`, `id`, `created_at` or `updated_at`. The only timestamps this story may write are those naturally produced by a genuinely **new** row.
4. **No FastAPI lifespan / boot auto-seeding.** `app/main.py` is byte-unchanged; the admin runs the entrypoint on purpose. This is the 41.3 posture and its reason still holds: a boot-time seed resurrects owner-deleted categories on every redeploy and fights admin governance.
5. **No model↔category assignments.** Zero rows are written to `model_browse_category`. A model with zero categories is valid and stays public (FR26-CAT-2).
6. **No change to migration `0020_browse_categories` and no new migration.** Content stays out of schema — the 41.3 precedent, adopted deliberately by Decision AZ.
7. **No category API, router, service, schema or admin UI work.** `GET /api/categories` is Story 49.3; admin CRUD is Story 49.5.
8. **No destructive behaviour anywhere.** The seed never `UPDATE`s and never `DELETE`s. No live DB is opened in development or review.
9. **Follow the Story 41.3 taxonomy-seed shape** (`app/core/db/seed.py`, `apps/api/scripts/seed_taxonomy.py`, `tests/test_seed_taxonomy.py`) as the structural precedent — extend it, do not invent a parallel mechanism and do not refactor it.
10. **Strict RED→GREEN.** Every behavioural assertion in §4 is proven by a test that was observed failing before the code that satisfies it existed, with the failure output quoted verbatim in §15.

## 4. Acceptance Criteria

**AC-1 — The dataset is exactly the approved eight rows, in the approved order.**
`apps/api/app/core/db/seed.py` defines a module-level `STARTER_BROWSE_CATEGORIES: list[dict]` whose entries are, in this exact list order:

| `position` | `slug` | `name_pl` | `name_en` |
|---:|---|---|---|
| 0 | `storage-organization` | Przechowywanie i organizacja | Storage & Organization |
| 1 | `home-decor` | Dekoracje i wystrój | Home Decor |
| 2 | `holders-mounts` | Uchwyty i mocowania | Holders & Mounts |
| 3 | `electronics-cables` | Elektronika i kable | Electronics & Cables |
| 4 | `tools-workshop` | Narzędzia i warsztat | Tools & Workshop |
| 5 | `printer-3d` | Drukarka 3D i akcesoria | 3D Printer & Accessories |
| 6 | `toys-games` | Zabawki, gry i figurki | Toys, Games & Figures |
| 7 | `replacement-parts` | Części zamienne | Replacement Parts |

[Source: `EXPERIENCE.md:80-91` — the eight-row table, verbatim]

**AC-2 — Each row carries its canonical one-sentence `inclusion_criterion` (FR26-GOV-1).**
The stored strings are exactly:

| `slug` | `inclusion_criterion` |
|---|---|
| `storage-organization` | `The model's primary purpose is to hold, sort or tidy other objects.` |
| `home-decor` | `The model is chosen mainly for how it looks in a living space, not for a job it performs.` |
| `holders-mounts` | `The model exists to hold one specific object in a fixed position, or to attach something to a surface.` |
| `electronics-cables` | `The model houses, routes, protects or mounts electronics, wiring or connectors.` |
| `tools-workshop` | `The model is a tool, jig, fixture or aid used while making, measuring or repairing something.` |
| `printer-3d` | `The model only makes sense to someone who owns a 3D printer — it upgrades, maintains or feeds the printer itself.` |
| `toys-games` | `The model's purpose is play, collecting, or display as a character or object of interest.` |
| `replacement-parts` | `The model replaces or repairs a broken or missing part of an existing manufactured object.` |

**Canonical text semantics — decided here, explicitly, not left to the dev agent (§6 F-2).** The shipped entity has exactly **one** `inclusion_criterion` field (`_entities.py:157`), and `EXPERIENCE.md:101-156` supplies each criterion in **English only**. Therefore `inclusion_criterion` stores the **canonical English sentence**. No Polish criterion is invented, no second field is added, and no schema change is proposed. If a Polish criterion is ever wanted, that is an additive schema decision owned by a later story (49.5 / 54.3), never a silent widening here.

**The normalisation is exactly two deterministic transformations, and nothing else.** Applied to the `EXPERIENCE.md` "Inclusion criterion:" sentence, in this order:

1. **Strip markdown emphasis markers** (`*`). This affects **exactly one** row: `storage-organization`, whose source reads `… to hold, sort or tidy *other* objects.` → `… to hold, sort or tidy other objects.` The other seven source sentences contain no emphasis markers, so this step is a no-op for them.
2. **Capitalise the first letter** (the source sentences all begin lower-case because they follow the label `**Inclusion criterion:**`).

Everything else is preserved byte-for-byte: the trailing full stop, the em dash in `printer-3d` (`— it upgrades…`), the Oxford comma in `toys-games`, and all internal wording. **No rewording, no re-punctuation, no truncation, no synonym.** The table above is the authoritative post-normalisation text — if a dev agent's transformation of `EXPERIENCE.md` disagrees with a table cell, the table wins and the discrepancy is a defect to report, not to reconcile silently.

**AC-3 — Fields the seed deliberately leaves unset.**
Every seeded row has `description_en = None`, `description_pl = None`, and `parent_id = None`. `EXPERIENCE.md` supplies no description text distinct from the criterion, and its rejected-candidates table explicitly rejects a starter parent→child tree ("Seeding a tree would ship UI-invisible structure that immediately drifts"). Inventing descriptions or a hierarchy would fabricate approved content. `id`, `created_at` and `updated_at` come from the ORM defaults (`default_factory`), never from the dataset.

**AC-4 — `seed_browse_categories(engine)` exists and is create-if-absent by `slug`.**
`apps/api/app/core/db/seed.py` defines `def seed_browse_categories(engine: Engine) -> None`. For each dataset entry it selects `BrowseCategory` by `slug`; if a row exists it returns without touching it; otherwise it inserts a new row and commits.

**AC-5 — Seeding an empty database produces exactly the eight rows.**
After one call against an empty `browse_category` table: the set of slugs equals the eight approved slugs, the row count is exactly 8 (no duplicates), and every row's `name_en` / `name_pl` / `position` / `inclusion_criterion` matches AC-1 and AC-2 exactly.

**AC-6 — Re-running is idempotent and byte-stable.**
A second identical call leaves the table with exactly 8 rows and the same slug set, and a previously seeded row is unchanged in `id`, `name_en`, `name_pl`, `description_en`, `description_pl`, `inclusion_criterion`, `position`, `parent_id`, `created_at` **and** `updated_at`. Same `id` proves it was not recreated; same field values and same `updated_at` prove it was not updated.

**AC-7 — An admin-edited row survives a re-seed untouched.**
Given a pre-existing `browse_category` row with an approved `slug` but deliberately divergent values (renamed labels, rewritten `inclusion_criterion`, a moved `position`, a set `description_pl`, a non-null `parent_id` pointing at another category), a seed run leaves that row's `id` and every one of those fields exactly as the admin left them, and creates no second row for that slug.

**AC-8 — A partial existing dataset is completed, not disturbed.**
Given a database containing a strict, non-empty subset of the approved slugs (for example three of the eight, one of which is admin-edited), a seed run creates exactly the missing rows, leaves every pre-existing row byte-identical (including the edited one), and converges to exactly 8 rows with no duplicates.

**AC-9 — Zero writes to `model_browse_category`, zero writes to `model`.**
With a pre-existing `Model` row present, a seed run leaves `select(ModelBrowseCategory)` empty and the `Model` row count and contents unchanged. The seed module performs no `Model`, `ModelBrowseCategory`, `Tag`, `TagGroup` or `ModelTag` write on this code path.

**AC-10 — No boot / lifespan auto-seeding.**
`apps/api/app/main.py` is byte-unchanged: its `lifespan` (`main.py:64-93`) still calls `seed_admin` and nothing else. `grep -rn "seed_browse_categories" apps/api/app/` returns **only** its definition in `app/core/db/seed.py` — no import in `main.py`, no router, no dependency, no worker.

**AC-11 — Deliberate admin-run entrypoint with a truthful post-condition.**
`apps/api/scripts/seed_browse_categories.py` defines `def main(engine: Engine | None = None) -> None` which calls `seed_browse_categories(engine or get_engine())` and then prints a count **queried from the database after seeding**, not printed from the dataset constant — so a partial seed is visibly distinguishable from a full one. Format: `seeded browse categories: {n} categories present`. It is runnable as `python -m scripts.seed_browse_categories` and guarded by `if __name__ == "__main__":`. The `engine` parameter is injectable so the test never touches a real database.

**AC-12 — The approved decision is pinned by a drift guard. (This is NOT the evidence gate, and does not pretend to be.)**

**What discharges the live evidence gate:** the controller's read-only production capture plus **two independent analyses** of it (§6 F-1). Nothing in this story's test suite can re-derive that — a unit test runs against an empty `tmp_path` SQLite file and has no access to the live catalogue, so **no test here proves anything about the real model distribution.** Any wording that calls the live evidence "made executable" by a unit test would be false and is deliberately not used.

**What AC-12 actually requires:** a **post-decision drift guard** over the approved dataset constant. The dataset's module comment in `seed.py` records the evidence source, date and both report verdicts (§6 F-1), and a test asserts that `[(c["slug"], c["position"]) for c in STARTER_BROWSE_CATEGORIES]` equals the approved `(slug, position)` sequence in AC-1, that `position` values are dense `0..7` and strictly increasing in list order, and that all eight slugs are unique, lowercase, ASCII and `[a-z0-9-]` only. Its purpose is narrow and real: the evidence review's conclusion was **keep the approved eight, reorder nothing, merge nothing**, so a silent reorder, rename or drop by a later editor becomes a failing test rather than an unnoticed content change. `replacement-parts` clearing the bar at exactly three is recorded in §6 F-3 and §9 R-1 as a monitoring obligation, not as a shortfall in the set.

**AC-13 — Failure partway through does not wedge the seed.**
Transaction boundary is **per-row commit**, matching `seed_taxonomy` (`seed.py:167-171`). If a commit fails mid-run, the rows committed before the fault are a consistent, non-empty strict subset of the approved set with no duplicates, and a clean re-run completes the remainder and converges to exactly 8 rows.

**AC-14 — A concurrent insert of the same slug is tolerated, never duplicated.**
If the existence `SELECT` misses a row that another writer commits before this session's `INSERT`, the resulting `IntegrityError` is caught, the session is rolled back, and the run continues without raising. The racer's row is left untouched and exactly one row exists for that slug.

**AC-15 — No schema change, and the shipped parity gate stays green unmodified.**
`apps/api/app/core/db/models/_entities.py`, `apps/api/app/core/db/models/__init__.py`, every file under `apps/api/migrations/`, and `apps/api/tests/test_orm_migration_parity.py` are byte-unchanged. `alembic` is not invoked by any test this story adds. `pytest tests/test_orm_migration_parity.py tests/test_migration_0020.py -q` passes with those files untouched.

**AC-16 — Merge gate.**
The single implementation commit passes `infra/scripts/check-all.sh` **16/16 stages** standalone with a teed log, no stage skipped, plus the determinism run required by NFR26-DETERMINISM-1 (three identical API summaries), plus an **independent Aider review** (`laura-aider-review-diff`) after the native `bmad-code-review` passes. `apps/web`, `workers/render`, visual baselines and locale files must require **no** change; a delta there is an environmental drift signal to investigate, never something to blanket-update in this commit.

## 5. Tasks / Subtasks — strict RED → GREEN

**The RED→GREEN contract for this story, stated once and binding.**

1. **Test-module-first.** The **complete** relevant test surface — every behaviour in AC-1 … AC-14 — is authored in `apps/api/tests/test_seed_browse_categories.py` **before any production symbol exists** (T2). At that point the whole module is red, and it is red for the right reason: the behaviour it asserts is absent.
2. **Every recorded RED must fail because behaviour is missing or wrong** — never because an assertion was deliberately written false. **Writing a knowingly-false assertion so a "red" can be quoted is forbidden**; it proves nothing about the code and misrepresents the record.
3. **Where a test would pass the moment the seeder is written correctly** (the idempotency and preservation tests are exactly this class — create-if-absent satisfies them by construction), its load-bearingness is proven by a **labelled mutation sensitivity check**, not by faking a red: temporarily mutate the **production** code in the direction the test forbids (e.g. make `_insert_absent_category` overwrite instead of skip), observe the test fail, revert, and re-run green. §15 records the mutation, the observed failure, and the `git diff` proving the revert. **This is explicitly recorded as a sensitivity check, never as the original RED.**
4. Every quoted failure in §15 is **verbatim command output**, with the command line and the working directory.

### T1 — Baseline (evidence-first, no code change)

- [x] T1.1 At `df922f9`, run `pytest tests/test_seed_taxonomy.py tests/test_seed.py tests/test_browse_category_entity.py tests/test_orm_migration_parity.py -q` and record the passing counts. This proves every later red is caused by this story.
- [x] T1.2 Record `git rev-parse HEAD` and `git status --porcelain` (must be clean).

### T2 — RED: author the complete test module before any production code (AC-1 … AC-14)

`apps/api/tests/test_seed_browse_categories.py` is written in full in this task. No line of `seed.py` or `scripts/` is touched until T3.

- [x] T2.1 Create the module with the imports the story needs: `STARTER_BROWSE_CATEGORIES`, `seed_browse_categories`, `_insert_absent_category` from `app.core.db.seed`; `main as seed_categories_script_main` from `scripts.seed_browse_categories`; `BrowseCategory`, `ModelBrowseCategory`, `Model`, `Tag`, `TagGroup`, `ModelTag` from `app.core.db.models`. Fixture idiom (`create_engine_for_url` + `init_schema` on `tmp_path`) copied verbatim from `test_seed_taxonomy.py:32-35`.
- [x] T2.2 Dataset-shape tests (AC-1, AC-2, AC-3, AC-12): exact ordered `(slug, position)` sequence; exact `name_pl` / `name_en` / `inclusion_criterion` per slug compared **literally** against the §4 tables; `description_en` / `description_pl` / `parent_id` absent-or-`None` in every entry; slug charset, lowercase, ASCII, uniqueness; dense `0..7` positions strictly increasing in list order.
- [x] T2.3 Behaviour tests, all of AC-5 … AC-11 and AC-13, AC-14 — i.e. every test enumerated in T4, T5 and T6 below, authored **now**, in this module, while the production symbols still do not exist.
- [x] T2.4 **RED, observed and quoted** — run `pytest tests/test_seed_browse_categories.py -q`. Expected: a collection error, `ImportError: cannot import name 'STARTER_BROWSE_CATEGORIES' from 'app.core.db.seed'` (or the `ModuleNotFoundError: No module named 'scripts.seed_browse_categories'` raised first, depending on import order — quote whichever actually appears, and quote the second after the first is resolved). Record the full output in §15. **Zero tests may be passing at this point.**

### T3 — GREEN: dataset + seeder (AC-1 … AC-9, AC-12, AC-13, AC-14)

- [x] T3.1 Add `STARTER_BROWSE_CATEGORIES` and `seed_browse_categories` + `_insert_absent_category` to `apps/api/app/core/db/seed.py`, mirroring `_insert_absent_tag` (`seed.py:217-236`) — including its `try/except IntegrityError → rollback` branch, which AC-14 requires and which the unique index `uq_browse_category_slug` makes load-bearing. Include the module comment carrying the §6 F-1 evidence citation. Add `BrowseCategory` to the existing `from app.core.db.models import …` line (`seed.py:8`).
- [x] T3.2 Re-run the module. Everything except the AC-11 script tests must now be green. Record the summary.
- [x] T3.3 **Mutation sensitivity check, explicitly labelled — not a RED.** The AC-6 / AC-7 / AC-8 preservation tests pass by construction once create-if-absent exists, so prove they are load-bearing: temporarily change `_insert_absent_category` to overwrite an existing row's fields instead of returning early, observe the AC-6, AC-7 and AC-8 tests fail, revert, and re-run green. §15 records: the mutation diff, the verbatim failure output, and the post-revert `git diff apps/api/app/core/db/seed.py` proving the mutation is gone. Repeat with a second mutation — drop the `try/except IntegrityError` — to prove the AC-14 test is load-bearing rather than trivially satisfied.

### T4 — Behaviour coverage authored in T2, verified green in T3 (AC-9, AC-10)

- [x] T4.1 Test (AC-9): pre-insert a `Model`, one `TagGroup` and one `Tag`; seed; assert `select(ModelBrowseCategory)` is empty, and that the `Model`, `Tag`, `TagGroup` and `ModelTag` row sets are unchanged in count and content — the seed touches `browse_category` and nothing else.
- [x] T4.2 Test (AC-10): assert `app.main` does not reference `seed_browse_categories` — a source-level assertion on the module (import-free `grep`-equivalent), so a later accidental lifespan wiring fails the suite.
- [x] T4.3 Confirm `apps/api/app/main.py` shows in `git diff --stat` as untouched.

### T5 — Transaction and race behaviour (AC-13, AC-14)

- [x] T5.1 Convergence-after-failure test (AC-13): monkeypatch `Session.commit` to raise `RuntimeError` on the Nth call (`N = 4` lands after three of eight rows), assert the committed subset is a **non-empty strict** subset with no duplicates, undo the patch, re-run, assert convergence to exactly 8. Model on `test_seed_taxonomy.py:190-240`. **`RuntimeError`, never `IntegrityError`** — the latter is swallowed by design and would make the test vacuous.
- [x] T5.2 Genuine-`IntegrityError` test (AC-14): reuse the `_MissingRow` / `_first_call_misses` idiom (`test_seed_taxonomy.py:262-289`) so the existence `SELECT` misses a row a racer already committed. Assert exactly what `test_insert_absent_tag_tolerates_real_integrity_error` (`test_seed_taxonomy.py:316-348`) asserts, no more: **no raise**, exactly **one** row for that slug, and **the racer's row values preserved** (`name_en == "RACER"`-style check, proving the failed INSERT neither duplicated nor clobbered). Nothing broader than the shipped 41.3 handler is introduced — no re-query-and-adopt, no partial update.

### T6 — GREEN: admin-run entrypoint (AC-11)

The AC-11 test is authored in T2 and is red from T2.4 onward with `ModuleNotFoundError: No module named 'scripts.seed_browse_categories'` — quote that failure in §15 before this task's code exists.

- [x] T6.1 Test content (AC-11, authored in T2.3): call `main(engine=<tmp engine>)`, capture stdout with `capsys`, assert the printed number equals the count **queried from the DB** after seeding **and** equals `8` on a full seed. Precedent: `test_seed_taxonomy.py:351-363`.
- [x] T6.2 **GREEN** — create `apps/api/scripts/seed_browse_categories.py` mirroring `scripts/seed_taxonomy.py` (docstring stating why it is *not* lifespan-wired, `main(engine: Engine | None = None)`, DB-queried count, `__main__` guard).
- [x] T6.3 Re-run the full module — every test green. Record the summary.

### T7 — Non-regression sweep (AC-15)

- [x] T7.1 `pytest tests/test_orm_migration_parity.py tests/test_migration_0020.py tests/test_migration_0019.py tests/test_browse_category_entity.py tests/test_seed_taxonomy.py tests/test_seed.py -q` → all green with those files unmodified.
- [x] T7.2 `git diff --stat` restricted to product paths (`apps/`, `workers/`, `infra/`, `docs/`, root `*.md`, `pyproject.toml`, `uv.lock`) shows **exactly** the three execution-critical files in §7. Any other product path is a defect. `_bmad-output/**` is **not** counted here — see §7 and §11: the story artifact and `sprint-status.yaml` are workflow records, legitimately part of the same closeout commit.
- [x] T7.3 `ruff format --check` and `ruff check` clean in `apps/api`.

### T8 — Merge gate (AC-16) — controller-owned, not checkable by the dev agent alone

- [x] T8.1 `infra/scripts/check-all.sh` standalone, teed to `.hermes/run-logs/`, exit 0, `all green.`, 16/16 stages, no stage skipped. **DONE — controller-owned frozen run** `.hermes/run-logs/e49-2-controller-check-all-20260726.log`; tracked `seed.py` diff SHA-256 identical before/after (`80af7532…aa11d`); API 1780 passed / 3 skipped, Web 785 passed, visual 536 passed / 32 expected skips.
- [x] T8.2 Determinism: three consecutive API pytest runs with identical summaries (NFR26-DETERMINISM-1). **DONE — controller-owned**, `.hermes/run-logs/e49-2-controller-api-determinism-proof-20260726.txt`: 3× `(1780 passed, 3 skipped, 2014 warnings)`, every run exit 0, `identical=True`.
- [x] T8.3 Native `bmad-code-review`, then the independent `laura-aider-review-diff` pass. Findings loop back to `bmad-dev-story`. **DONE** — native Claude/Opus `APPROVE`, Critical 0 / Important 0 (§18); independent Aider/DeepSeek `APPROVE`, Critical 0 / Important 0 (§19). No blocking fix loop was required.
- [x] T8.4 One commit, ff-only merge. **DONE — controller-owned.** One atomic story commit with subject `feat(api): seed starter browse categories` was created on `feat/E49.2-starter-category-seed`; this final status/evidence closeout is folded into that same commit by amend. The branch is a one-commit descendant of baseline `88a683a` and is integrated into `main` by ff-only immediately after this artifact is committed. The final SHA and merge proof live in Git/run logs rather than this self-referential file.

## 6. Verify-at-create findings (traced at HEAD `df922f9` this session, not carried from the epic sketch)

**F-1 — The real-distribution evidence obligation is DISCHARGED for all eight categories, read-only, by a dataset plus two independent analyses.**
`EXPERIENCE.md:192` records the obligation honestly: *"Story 49.2 owes, before seeding: a distribution check against the real catalogue confirming each of the eight would land ≥ 3 models under deliberate curation, and a documented reorder or merge for any that would not."*

**How it was discharged** — controller-run, read-only, against the production SQLite database opened through a `mode=ro` URI (no write was possible), then analysed twice, independently:

| Artefact | Content | Location *(local, gitignored — deliberately not copied into any tracked artifact)* |
|---|---|---|
| Primary dataset | 131 active records, fields **only** `name` + tag slugs/labels. No ids, paths, user data, assignments or writes. SHA-256 `4597db80…8000` | `.hermes/run-logs/e49-2-live-model-name-tags-20260726.json` |
| Earlier tag-signal capture | Aggregate tag counts at revision `0019_drop_category` | `.hermes/run-logs/e49-2-live-distribution-20260726.json` |
| Analysis 1 — full curation | Full M:N curation of all 131 records against the `EXPERIENCE.md:101-186` criteria and tie-breaks. **Verdict PASS.** Coverage 122/131 (93.1 %), 9 ambiguous/uncategorised, 5 multi-category, max 2 categories per model. Counts: storage-organization 30, home-decor 17, holders-mounts 31, electronics-cables 14, tools-workshop 3, printer-3d 17, toys-games 12, replacement-parts 3 | `subagent-summary-0-20260726_144201_572028.txt` |
| Analysis 2 — adversarial | Deliberate attempt to **falsify** the "≥ 3 per category" claim, counting only records needing no expansive interpretation. **Verdict PASS** — the claim could not be refuted. Conservative minima: storage-organization 19, home-decor 14, holders-mounts 23, electronics-cables 16, tools-workshop 6, printer-3d 10, toys-games 11, replacement-parts 3 | `subagent-summary-1-20260726_144201_572403.txt` |

The two count sets differ **as expected and for a stated reason**: analysis 1 is a full many-to-many curation, analysis 2 is a conservative lower bound. They agree on the only thing the gate asks — **every one of the eight clears ≥ 3** — and they agree that `replacement-parts` clears it at exactly 3.

**Supporting facts from the same captures, still true and still load-bearing:**

- 132 models total, **131 active**; **31 active models carry zero tags (23.7 %)** — tags alone therefore cannot categorise the catalogue automatically, which independently confirms the "no automatic tag→category inference" posture rather than merely restating it.
- Leading tag signals (model counts): `organizer` 13, `print-in-place` 12, `stand` 11, `k1_max` 8, `kitchen` 8, `articulated` 7, `holder` 6, `planter` 6, `cable` 5, `calibration` 5, `clip` 5, `desk` 5, `mod` 5, `plants` 5, `riser` 5, `stackable` 5, `winder` 5, `fidget` 4.
- **Conclusion:** keep the approved eight, **reorder nothing, merge nothing, remove nothing** before the seed. `EXPERIENCE.md:192`'s remedy clause ("a documented reorder or merge for any that would not") is not triggered, because none of the eight fails the bar. The evidence validates the **starter vocabulary and order only** — this story still creates **no assignments**.
- **What this evidence is NOT.** It is a curation *feasibility* proof against names and tags, not a curation. No model is assigned anywhere by this story, and no test in this story can re-derive any of the above (see AC-12).

**F-2 — `inclusion_criterion` is single-valued, and the criteria exist only in English. Resolved, not guessed.**
`_entities.py:157` is `inclusion_criterion: str | None = None` — one field. `epics.md:4475` asks for "bilingual labels … and a one-sentence `inclusion_criterion` each" — **bilingual applies to the labels, not to the criterion**, so there is no contradiction between the artifacts and therefore no validation blocker to raise. `EXPERIENCE.md:101-156` supplies each criterion in English only. AC-2 binds the English sentence and forbids both inventing a Polish translation and adding a second column.

**F-3 — `replacement-parts` clears the bar at exactly 3. Affirmative, named, and fragile — a monitoring obligation, not a shortfall.**

Both independent analyses land on the **same three** records, and both reached them from the `EXPERIENCE.md` criterion ("the model replaces or repairs a broken or missing part of an existing manufactured object") plus its boundary rules:

1. `3D Printable Switch Replacement` — an explicit replacement component (no tags at all; classified on name).
2. `Jura Coffee Machine Parts (for Jarek)` — tags `coffee-machine, jarek, jura, repair`; parts for an existing branded appliance.
3. `Quechua Backpack Buckle 50x55mm` — tags `backpack, buckle, quechua, repair`; a specific replacement buckle for an existing backpack.

The adversarial pass **explicitly excluded** the tempting near-misses, each under a rule already written in `EXPERIENCE.md:180-186`: the dropper-post seat-bag adapters, the Bosch connector/charger and the clothes-hanger connector (nothing is being restored → holders/electronics); the calibration spacers and Stealth Press (tools used *to* work, not the restored object); the CTEK and Window holders (holders); the Rosa3D spool adapter and the K1 hinge/fan/riser/bumper/PTFE parts (**printer-specific always wins** → `printer-3d`); the VW mount and XT30 bracket (electronics/holder, not restoration).

**Disposition:** the row stays, unchanged and un-merged, because it *passes*. Its margin is zero, so it is registered as a **priority curation and tiny-category monitoring item for Story 52.3** (the curation-QA "empty or tiny category" advisory already planned there). **Named future trigger:** if `replacement-parts` still holds fewer than three curated models when 52.3's queue runs, merging it into `tools-workshop` or retiring it is an admin governance action (49.5), never a re-seed and never an edit to this dataset. **Nothing in this story is contingent on that outcome** — the seed writes eight rows and zero assignments either way.

**F-4 — Live tag vocabulary ≠ the shipped `STARTER_TAXONOMY`; nothing in this story depends on either.**
The observed live tags (`organizer`, `k1_max`, `3x4`, `magsafe`, `repair`, …) are free-form ingest tags, not the 41.3 starter slugs (`organizers`, `k1-max`, …). `EXPERIENCE.md`'s "crosses ≥ 2 tag groups" derivation was written against `STARTER_TAXONOMY`, so it is a *design* justification, not a live-data claim. F-1's evidence is therefore name-and-tag *classification*, not a `STARTER_TAXONOMY` lookup — which is why it is honest evidence for the ≥ 3 gate while the "crosses ≥ 2 groups" line remains design rationale. This changes nothing for this story — the seed writes only `browse_category` rows and reads no tag data at all — but it is recorded so a later reader does not mistake the derivation for measured evidence.

**F-5 — The 41.3 precedent is real, current, and directly extensible.** Verified at HEAD: `seed.py:160-192` (`seed_taxonomy`), `:195-214` (`_upsert_absent_group`), `:217-236` (`_insert_absent_tag`); `scripts/seed_taxonomy.py:33-50`; `tests/test_seed_taxonomy.py` (364 lines, 14 tests). `seed_browse_categories` needs only the *simpler* half of that shape — `BrowseCategory` has no parent-child seeding phase, so there is **no** two-phase group→tag pass and **no** id-returning `_upsert_absent_*` helper. Copy `_insert_absent_tag`, not `_upsert_absent_group`.

**F-6 — Nothing in the application layer writes `browse_category` yet.** `grep -rn "browse_category\|BrowseCategory" apps/api --include=*.py` returns hits in exactly five files: `app/core/db/models/_entities.py` (11), `app/core/db/models/__init__.py` (4), `tests/test_browse_category_entity.py` (49), `tests/test_migration_0020.py` (46), `tests/test_migration_0004.py` (2), plus `migrations/versions/0020_browse_categories.py`. **All of them are entity, migration or migration-test code — there is no existing category seed, router, service or schema, and no application code path writes the table.** (The three test files and the migration are on §7's must-stay-unchanged list; the earlier claim that only the entity files and `test_browse_category_entity.py` match was an under-count of the same conclusion.) The `0019`-era capture recorded `has_browse_category: false`; **the table now exists live** at revision `0020_browse_categories` and is empty (§2, live posture).

**F-7 — `main.py` lifespan calls `seed_admin` and only `seed_admin`** (`main.py:84-89`); `seed_taxonomy` is deliberately absent. AC-10 preserves that shape and makes a future accidental wiring a test failure rather than a silent behaviour change.

**F-8 — `check-all.sh` is exactly 16 stages.** `grep -n run_stage infra/scripts/check-all.sh` yields 17 hits: the function definition at `:30` plus 16 invocations (`:54, 57, 60, 63, 66, 77, 80, 83, 86, 89, 95, 98, 104, 110, 112, 119`). "16/16" in AC-16 is verified, not assumed.

**F-9 — `scripts.` is importable from the test suite.** `tests/test_seed_taxonomy.py:23` already does `from scripts.seed_taxonomy import main` and passes at HEAD, so T6.1's expected `ModuleNotFoundError` is caused by the missing *module*, not by a missing import path.

**F-10 — REPORTED, NOT FIXED (unchanged from the 49.1 pass): `architecture.md:3351` still calls this seed story "49.3".** `epics.md:4473`, `sprint-status.yaml:380` and this document use the post-renumber `49.2`. Correcting a planning artifact is `bmad-correct-course` territory, not story creation, and the staleness is harmless to this story's execution. Also still open from 49.1's F-15: `architecture.md:3386` and `implementation-readiness-report-2026-07-26.md:204` describe G26-CAT-SET as open/routed while `epics.md:4475` and `sprint-status.yaml:380` record it **closed** by `48db6bb`. Same class, same disposition.

## 7. Predicted file changes (exact)

**Execution-critical application/test files — exactly 3:**

| File | Action | Why |
|---|---|---|
| `apps/api/app/core/db/seed.py` | **MODIFY** | Append `STARTER_BROWSE_CATEGORIES`, `seed_browse_categories`, `_insert_absent_category`. `seed_admin`, `STARTER_TAXONOMY`, `seed_taxonomy`, `_upsert_absent_group`, `_insert_absent_tag` stay byte-unchanged; the `BrowseCategory` import joins the existing `app.core.db.models` import line. |
| `apps/api/scripts/seed_browse_categories.py` | **NEW** | The deliberate admin-run entrypoint (AC-11), mirroring `scripts/seed_taxonomy.py`. |
| `apps/api/tests/test_seed_browse_categories.py` | **NEW** | AC-1 … AC-14, mirroring `tests/test_seed_taxonomy.py`. |

**Explicitly UNCHANGED (assert with `git diff --stat`; any hit is a defect):**

- `apps/api/app/core/db/models/_entities.py`, `models/__init__.py`, `_helpers.py`, `_enums.py`, `_audit.py`, `_auth.py`, `_user.py`, `_recovery.py` — **no schema change**
- `apps/api/migrations/**` — all twenty revisions incl. `0020_browse_categories.py`, `env.py`, `alembic.ini`. **No new migration.**
- `apps/api/app/main.py` — no lifespan wiring (AC-10)
- `apps/api/app/core/db/session.py`
- `apps/api/app/modules/**` — the entire `sot`, `admin`, `share`, `auth`, `invite`, `slicer`, `spools`, `queue`, `runbook` tree. **No API/router/service/schema.**
- `apps/api/scripts/seed_taxonomy.py` and every other existing script
- `apps/api/tests/test_orm_migration_parity.py` — **must pass unmodified**
- `apps/api/tests/test_seed.py`, `test_seed_taxonomy.py`, `test_browse_category_entity.py`, `test_migration_0020.py`, `test_migration_0019.py`, `test_migration_0004.py`, `test_db_entity_tables.py`, `test_sot_*.py`, `test_route_enforcement_gate.py`, `test_openapi_agent_surface.py`
- `apps/web/**` — every source file, `api-types.ts`, `locales/en.json`, `locales/pl.json`, every `tests/visual/**` spec and every `__snapshots__/**/*.png`
- `workers/render/**`, `infra/**`, `docs/**`, `AGENTS.md`, `CLAUDE.md`, `README.md`
- `_bmad-output/planning-artifacts/**` (including the F-10 stale references)
- `pyproject.toml` / `uv.lock` — **no dependency change**

**Workflow files — not application code, and not counted in the "three files" figure:**

| File | When it changes | Why it is not a scope violation |
|---|---|---|
| `_bmad-output/implementation-artifacts/49-2-starter-category-seed.md` (this document) | planning branch: create + validate passes. Implementation branch: §15 Dev Agent Record, §18 review record, §20 disposition | The dev/review record **must** live in the story artifact; there is nowhere else for it |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | planning branch: `ready-for-validation` → `ready-for-dev`. Implementation branch: `ready-for-dev` → `review` → `done` | Canonical workflow tracker |

**Precedent, verified rather than asserted.** Story 49.1's single implementation commit `df922f9` contains **9 paths**: 7 application/test/migration files **plus** its story artifact (+528 lines) **plus** `sprint-status.yaml`. So the honest shape for this story is: **three product files + the two workflow files in the closeout commit**, not "a commit containing only three paths". Claiming the latter while also requiring review→done workflow records inside the commit would be self-contradictory.

## 8. Dev Notes

### 8.1 Files being modified — current state, change, what must be preserved

**`apps/api/app/core/db/seed.py` (236 lines at HEAD).** Today it holds `seed_admin` (`:11-28`), the `STARTER_TAXONOMY` dataset (`:35-157`) with its owner-editable rationale comment, `seed_taxonomy` (`:160-192`), `_upsert_absent_group` (`:195-214`) and `_insert_absent_tag` (`:217-236`). Imports at `:1-8`.
**Change:** append a new section after `_insert_absent_tag`, and add `BrowseCategory` to the `from app.core.db.models import …` line at `:8`.
**Preserve:** every existing symbol byte-identical. `seed_admin` stays the only lifespan-wired seeder. Do **not** refactor `_insert_absent_tag` into a generic helper "since they are similar" — the shapes diverge (tag rows need a parent id and a positional index; category rows do not), and a shared abstraction here buys nothing and risks the 41.3 tests.

**`_insert_absent_tag` is the literal template** (`seed.py:217-236`):

```python
def _insert_absent_tag(session, tag, group_id, group_position) -> None:
    existing = session.exec(select(Tag).where(Tag.slug == tag["slug"])).first()
    if existing is not None:
        return
    row = Tag(...)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
```

`_insert_absent_category` is that, with `BrowseCategory` and the dataset's five content fields.

### 8.2 Why "never update" is the whole story, said once

The seed writes `INSERT` and nothing else. There is no `UPDATE` path, no merge path, no "refresh labels" path, and adding one would break AC-7 and contradict the governance model: after the first run, the database — edited by the admin through Story 49.5's surface — is the source of truth for category content, and this dataset is only a bootstrap. That is exactly the 41.3 contract (`seed.py:35-41`: "edits made after a group/tag already exists in the DB do **not** propagate — admin governance of renames/reorders wins").

### 8.3 Why this is not part of `0020`

Decision AZ made `0020` structural only: *"The starter category set is a **separate** admin-run seed story … keeping content decisions out of the migration — the 41.3 precedent, adopted deliberately"* (`architecture.md:3351`, modulo the F-10 stale story number). Content in a migration is unversionable, un-reorderable and un-deletable without another migration; content in a re-runnable script is governed by the admin. Do not "simplify" by moving rows into a migration.

### 8.4 Project rules that bind this story specifically

- **TDD is mandatory for backend logic** — red → green → refactor, failure output recorded (AGENTS.md).
- **A story branch is not mergeable until `check-all.sh` is green standalone** (AGENTS.md:156-160). 16 stages (F-8).
- **ff-only merge, no squash, no merge commit** (AGENTS.md:87,116-122).
- **Independent Aider review after the native BMAD review** (AGENTS.md:108,218,277) — routine reviewer is Aider (`laura-aider-review-diff`); Codex is fallback/high-stakes only.
- **Minimal diff.** Three files. No opportunistic refactor of `seed.py`, no new abstraction layer, no config surface, no CLI argument parsing (the 41.3 script takes none).

### 8.5 Previous-story intelligence (Story 49.1, `done` at `df922f9`)

- **The table this story fills was created there.** `BrowseCategory` (`_entities.py:130-164`): `slug` is a bare `str` with an explicit `Index("uq_browse_category_slug", "slug", unique=True)` — a **unique** index, so a duplicate-slug `INSERT` raises `IntegrityError` at the DB level. AC-14's tolerance branch is therefore load-bearing, not decorative.
- `name_en` is **NOT NULL**; `name_pl`, both descriptions, `inclusion_criterion` and `parent_id` are nullable; `position` defaults to `0`. All eight approved rows supply a non-null `name_pl` regardless.
- **49.1's hardest-won lesson was ORM↔migration parity.** This story adds no ORM field, so parity is untouched — but `test_orm_migration_parity.py` must still pass **unmodified** (AC-15). If it ever goes red here, the cause is an accidental entity edit, not the seed.
- 49.1 ran a bounded review-fix loop over a latent self-FK `downgrade()` issue. Nothing in this story touches `downgrade()`.
- **49.1 is now pushed and deployed** (§2, live posture): live revision `0020_browse_categories`, both tables present, 132 `model` rows preserved, `browse_category` = 0, `model_browse_category` = 0, integrity ok, 0 FK violations. So this story's table exists live and is empty — but dev and review still run **only** against `tmp_path` scratch databases, and the live seed invocation is a post-merge controller/admin action.
- **The 41.3 `IntegrityError` posture is the exact ceiling, verified at HEAD.** `_insert_absent_tag` (`seed.py:217-236`) catches `IntegrityError`, rolls back, returns — no re-query, no adopt, no update — and `test_seed_taxonomy.py:316-348` proves the racer's row survives with exactly one row for the slug. `_upsert_absent_category` must **not** copy `_upsert_absent_group`'s post-rollback `.one()` re-query (`seed.py:206-214`): that exists only because the group helper must return an id for the tag phase, and this story has no second phase. AC-14 sits exactly on the `_insert_absent_tag` pattern and widens nothing.
- **Honesty posture carried forward:** 49.1's record explicitly refused to tick a commit checkbox for a commit that did not exist. T8.4 keeps that rule.

### 8.6 Git intelligence (last 5 commits)

`df922f9` feat(api): add browse category entities and 0020 migration · `d6299fa` docs(init26): validate story 49.1 · `47fe971` docs(init26): reconcile sprint planning · `48db6bb` docs(init26): add targeted UX and taxonomy · `9c8a9a0` docs: plan Initiative 26 catalog discovery.
Pattern: one implementation commit per story, `docs(init26):` for planning-only passes, planning artifacts committed separately from code. This story's planning branch is `docs/init26-e49-2-create-validate`; implementation goes on its own `feat/` branch. `git status` is clean at `df922f9`.

### 8.7 Library / version notes

No new dependency, no version bump, no `uv.lock` change. The story uses only what `seed.py` already imports: `sqlmodel.Session` / `select`, `sqlalchemy.engine.Engine`, `sqlalchemy.exc.IntegrityError`. Note that declared floors in `pyproject.toml` are floors, not resolved versions (49.1 established: `sqlmodel` resolves to 0.0.38, `pydantic` to 2.13.3) — nothing in this story is version-sensitive.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-1 | `replacement-parts` clears the ≥ 3 gate with **zero margin** (§6 F-3) — one reclassification during real curation takes it below the bar. | Not a blocker: it *passes*, on three named records both analyses agree on. Registered as a priority curation / tiny-category monitoring item for 52.3's curation-QA advisory; remedy is admin governance (49.5), never a re-seed. Nothing in this story depends on its population. |
| R-2 | A dev agent "helpfully" adds an update/refresh path so labels stay in sync with the dataset. | AC-6 and AC-7 fail loudly, including on `updated_at`. §8.2 states the prohibition explicitly. |
| R-3 | A dev agent wires the seed into `lifespan` for convenience. | AC-10 asserts it at source level; §7 lists `main.py` as unchanged. |
| R-4 | The em dash in the `printer-3d` criterion or the Polish diacritics get mangled by an editor. | AC-2 pins the exact strings and the test compares them literally; `ruff format` does not rewrite string contents. |
| R-5 | Someone reorders the dataset "to look nicer". | AC-12 pins the exact `(slug, position)` sequence — a reorder is a failing test, not a style choice. |
| R-6 | The mid-run failure test is written so the fault lands before any row commits, making the "consistent subset" assertion vacuously true. | T5.1 requires a **non-empty strict** subset, mirroring the reasoning at `test_seed_taxonomy.py:200-204`. |
| R-7 | Temptation to seed one or two model assignments "to demo the feature". | AC-9 asserts `model_browse_category` is empty; constraint 5 is binding. |

**Rollback.** This story is trivially reversible in both directions. Code: a whole-commit `git revert` removes three files' worth of change and touches no schema. Data: the seed only inserts eight rows into a table that has no other writer yet, so `DELETE FROM browse_category WHERE slug IN (…)` — an admin action, not part of this story — undoes it as long as no assignments exist (and `category_id` is `RESTRICT`, so a row with assignments cannot be silently removed). No migration to unwind, no downgrade to run, no data loss possible.

## 10. Non-goals (this story ships none of these)

1. Any schema change, new migration, or edit to `0020_browse_categories`.
2. Any model↔category assignment, and any inference of categories from tags.
3. `GET /api/categories`, `GET /api/categories/{slug}`, `?category=` scope — Story 49.3.
4. Admin CRUD, reorder, replace-set assignment, audit rows — Story 49.5.
5. Any frontend work, i18n key, hook, route or visual baseline.
6. Boot-time / lifespan / deploy-script auto-seeding.
7. A second `inclusion_criterion` field, a Polish criterion, category descriptions, or a starter parent→child tree.
8. Refactoring `seed_taxonomy` / `STARTER_TAXONOMY` or generalising the two seeders into one.
9. Correcting the F-10 stale planning references (`bmad-correct-course` territory).
10. Any live-database access, deploy, or production action.

## 11. Branch and commit atomicity

- **Branch:** one story branch off `main` at `df922f9` (e.g. `feat/E49.2-starter-category-seed`). The current branch `docs/init26-e49-2-create-validate` is a **planning** branch: it carries this artifact and the `sprint-status.yaml` transition in **one `docs(init26):` planning commit**, and implementation does **not** happen on it.
- **Commit:** exactly **one** implementation commit. It contains the **three** product files in §7 plus the two workflow files (this story artifact's dev/review record and the `sprint-status.yaml` transition) — the `df922f9` shape. No fourth product file.
- **Gate:** that commit must pass `check-all.sh` 16/16 standalone.
- **Merge:** ff-only into `main`, no squash, no merge commit.
- **Revert shape:** a whole-commit `git revert` cleanly removes the seeder, the script and the tests; no schema or data migration is implicated.

## 12. Traceability

| Item | Source |
|---|---|
| Story identity, scope, "separate from the migration" rationale, the still-owed distribution check | `epics.md:4473-4475` (Story 49.2) |
| Epic goal, additive-only boundary | `epics.md:4455-4461` |
| FR26-CAT-1 (stable slug, bilingual labels, inclusion criterion, explicit `position`, not a `TagGroup`) | `prd.md:2244` |
| FR26-GOV-1 (one-sentence criterion, examples, evidence of usefulness for multiple models) | `prd.md:2255` |
| FR26-CAT-1 / FR26-GOV-1 ↔ story mapping | `epics.md:4399,4410` |
| FR26-CAT-2 (zero categories valid and public) — the reason no assignments are seeded | `prd.md:2245` |
| FR26-CAT-4 (flat MVP; no starter tree) | `prd.md:2247` |
| NFR26-DETERMINISM-1 | `prd.md:2268` |
| The eight approved rows, slugs, labels, `position`, ordering rationale | `EXPERIENCE.md:80-93` |
| Per-category inclusion criteria (AC-2 text source) | `EXPERIENCE.md:101-156` |
| Category↔Tag label-collision resolutions (why labels are widened) | `EXPERIENCE.md:158-171` |
| Rejected candidates incl. the starter-tree rejection (AC-3) | `EXPERIENCE.md:173-186` |
| The open evidence obligation this story discharges | `EXPERIENCE.md:188-194` |
| Real-distribution dataset (controller, read-only, `mode=ro`; 131 active records, name + tags only; SHA-256 `4597db80…8000`) | `.hermes/run-logs/e49-2-live-model-name-tags-20260726.json` *(local, gitignored)* |
| Earlier tag-signal capture (aggregate counts at `0019_drop_category`) | `.hermes/run-logs/e49-2-live-distribution-20260726.json` *(local, gitignored)* |
| Independent analysis 1 — full M:N curation, verdict PASS | `subagent-summary-0-20260726_144201_572028.txt` *(local, gitignored)* |
| Independent analysis 2 — adversarial falsification attempt, verdict PASS | `subagent-summary-1-20260726_144201_572403.txt` *(local, gitignored)* |
| Seed-out-of-migration policy, "separate admin-run seed story" | `architecture.md:3184` (41.3 precedent), `architecture.md:3351` (Decision AZ; F-10 stale story number) |
| G26-CAT-SET closed by `48db6bb` | `epics.md:4475`; `sprint-status.yaml:380` |
| Mergeability rule, ff-only, TDD, Aider review routing | `AGENTS.md:87,108,116-122,156-160,218,277` |
| Renumber history (49.3 → 49.2) | `epics.md:4461`; `sprint-status.yaml:2,378-383` |
| Predecessor story record (entity shape, parity lesson, honesty posture) | `49-1-browse-category-entities-and-0020-migration.md` §4, §7, §15, §18 |
| Code anchors | `seed.py:8,11-28,35-41,160-192,195-214,217-236`; `scripts/seed_taxonomy.py:1-50`; `tests/test_seed_taxonomy.py:32-35,106-133,135-173,176-187,190-240,262-289,292-314,316-348,351-363`; `_entities.py:130-164,167-183`; `models/__init__.py:19,21,44,47`; `session.py:12,31`; `main.py:64-93`; `infra/scripts/check-all.sh:30,54-119` |

## 13. Project structure notes

The story lands entirely inside the established `apps/api` layout: seed data and logic in `app/core/db/seed.py`, the admin entrypoint in `scripts/`, the test in `tests/test_<area>.py`. No new directory, no new module, no new package, no new dependency. **Detected variance:** none. The only convention judgements are the two new filenames, and both follow the 41.3 pair exactly: `scripts/seed_browse_categories.py` mirrors `scripts/seed_taxonomy.py`, and `tests/test_seed_browse_categories.py` mirrors `tests/test_seed_taxonomy.py`. Symbol naming follows the same rule — `seed_browse_categories` matches its script name, `_insert_absent_category` matches `_insert_absent_tag`.

## 14. Testing standards summary

- pytest with `asyncio_mode = "auto"`. These are **plain sync tests** against a throwaway `tmp_path` SQLite database built by `create_engine_for_url` + `init_schema` — no `TestClient`, no async `session` fixture, no `_isolated_db`, no Alembic run. Copy the fixture idiom verbatim from `test_seed_taxonomy.py:32-35`.
- **Determinism (NFR26-DETERMINISM-1):** no wall-clock assertions beyond "`updated_at` is unchanged after a re-run", no ordering dependence on dict iteration, no randomness, no sleeps, no network, no Redis, no live DB. Every test must be re-runnable in any order with an identical summary; T8.2 proves it with three consecutive identical API runs.
- TDD is mandatory: red → green → refactor, with the failure output recorded verbatim in §15. The whole test module is authored **before** any production symbol exists (T2), so every recorded red fails because the behaviour is absent. Tests that pass by construction once create-if-absent exists are proven load-bearing by the **labelled mutation sensitivity check** in T3.3 — never by writing a knowingly-false assertion, and never quietly presented as the original red.
- Frontend `vitest` and `test:visual` run inside `check-all.sh` but must require **no** change — this story adds no UI.

## 15. Dev Agent Record

### Agent Model Used

**Claude Opus 5** (`claude-opus-5`), native BMAD `bmad-dev-story` workflow (menu **DS**), single continuous agent session, 2026-07-26.

**Route.** Started with native `bmad-help`, which read `_bmad/_config/bmad-help.csv` → row `BMad Method,bmad-dev-story,Dev Story,DS,…,4-implementation,preceded-by bmad-create-story:validate,required=true`, and routed here. Skill customization resolved with `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow` → `activation_steps_prepend = []`, `activation_steps_append = []`, `on_complete = ""`, `persistent_facts = ["file:{project-root}/**/project-context.md"]`; **no team or user override** (`_bmad/custom/bmad-dev-story.toml` and `.user.toml` both absent). Config from `_bmad/bmm/config.yaml`: `user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`, `user_skill_level: intermediate`, `implementation_artifacts: {project-root}/_bmad-output/implementation-artifacts`.

**Provisioning note, stated rather than hidden.** The BMAD skill bodies are untracked and exist only in the primary checkout, so the workflow was read from `/home/ezop/repos/3d-portal/.claude/skills/bmad-dev-story/SKILL.md` (read-only) and executed against this worktree. The `persistent_facts` glob `**/project-context.md` matched **no file** in this worktree — recorded as executed-and-empty, not skipped. `apps/api/.venv`, `apps/web/node_modules` and `workers/render/.venv` are local symlinks into the primary checkout's provisioned toolchains; they are locally ignored and **verified absent from `git ls-files`** (see Completion Notes G).

**Environment.** Worktree `/home/ezop/worktrees/3d-portal-e49-2-dev`, branch `feat/E49.2-starter-category-seed`, Python 3.12.3, `pytest` with `asyncio_mode = "auto"`, `ruff` line-length 100.

**Actual implementation baseline: `88a683a51916aa02a57f085471963de4320558e6`** (`docs: create and validate story 49.2`), working tree clean at start (`git status --porcelain` empty). Front matter `baseline_commit` records that commit; the create/validate source baseline `df922f955fea42bbdbc76827406b008d28733718` is preserved as historical provenance in `create_validate_baseline_commit` and throughout §16. `88a683a` is a **docs-only** commit on top of `df922f9`, so all product code under `apps/api/` is byte-identical between the two — the T1.1 baseline measured here is therefore the same code the story was validated against, and the difference is provenance bookkeeping, not a code delta.

### Debug Log References

All logs are teed under the gitignored `.hermes/run-logs/`. Commands were run with cwd `/home/ezop/worktrees/3d-portal-e49-2-dev/apps/api` unless stated otherwise; `.venv/bin/python` is the symlinked API venv.

**T1 — baseline before any edit (`e49-2-*` context, cwd `apps/api`).**

```
$ .venv/bin/python -m pytest tests/test_seed_taxonomy.py tests/test_seed.py \
    tests/test_browse_category_entity.py tests/test_orm_migration_parity.py -q
...............................                                          [100%]
31 passed, 1 warning in 4.49s
```

The single warning is the **pre-existing** `SAWarning: Cannot correctly sort tables; there are unresolvable cycles between tables "model, model_file"` raised by `tests/test_orm_migration_parity.py:66` — present at baseline, unrelated to this story, unchanged afterwards.

```
$ git rev-parse HEAD
88a683a51916aa02a57f085471963de4320558e6
$ git status --porcelain
(empty — clean)
$ git rev-parse --abbrev-ref HEAD
feat/E49.2-starter-category-seed
```

**T2.4 — RED #1, the whole test module authored before any production symbol existed.** Log: `.hermes/run-logs/e49-2-red-1-t2.4.log`.

```
$ .venv/bin/python -m pytest tests/test_seed_browse_categories.py -q
==================================== ERRORS ====================================
____________ ERROR collecting tests/test_seed_browse_categories.py _____________
ImportError while importing test module '/home/ezop/worktrees/3d-portal-e49-2-dev/apps/api/tests/test_seed_browse_categories.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_seed_browse_categories.py:30: in <module>
    from app.core.db.seed import (
E   ImportError: cannot import name 'STARTER_BROWSE_CATEGORIES' from 'app.core.db.seed' (/home/ezop/worktrees/3d-portal-e49-2-dev/apps/api/app/core/db/seed.py)
=========================== short test summary info ============================
ERROR tests/test_seed_browse_categories.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.29s
```

**Zero tests passing at this point** — exactly the state T2 requires, and red because the behaviour is absent, not because any assertion was written false.

**RED #2 — the AC-11 entrypoint, after T3.1 resolved RED #1 and before `scripts/seed_browse_categories.py` existed.** Log: `.hermes/run-logs/e49-2-red-2-t6-script.log`.

```
$ .venv/bin/python -m pytest tests/test_seed_browse_categories.py -q
tests/test_seed_browse_categories.py:36: in <module>
    from scripts.seed_browse_categories import main as seed_categories_script_main
E   ModuleNotFoundError: No module named 'scripts.seed_browse_categories'
=========================== short test summary info ============================
ERROR tests/test_seed_browse_categories.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.23s
```

This is the second predicted collection error, quoted after the first was resolved, exactly as T2.4 / T6 direct. Per F-9 the cause is the missing **module**, not a missing import path (`tests/test_seed_taxonomy.py:23` already imports from `scripts.`).

**GREEN — one genuine defect in my own test code, found and fixed.** Log: `.hermes/run-logs/e49-2-green-1.log`. The first full-module run after T6.2 was `1 failed, 16 passed`: `test_dataset_positions_are_dense_and_strictly_increasing_in_list_order` raised `ValueError: zip() argument 2 is shorter than argument 1` — my adjacent-pair comparison passed `zip(positions, positions[1:], strict=True)` on unequal lengths. This was a **test-code bug, not a production defect**, and it is recorded rather than quietly amended. It was replaced with `itertools.pairwise(positions)` (also what `ruff` RUF007 requires). Logs `e49-2-green-2.log` and the post-mutation re-run:

```
$ .venv/bin/python -m pytest tests/test_seed_browse_categories.py -q
.................                                                        [100%]
17 passed in 1.48s
```

**T3.3 — labelled mutation sensitivity checks. These are NOT the original RED.** Pre-mutation hash of the production file, recorded before touching it:

```
$ sha256sum apps/api/app/core/db/seed.py
3b88dcc220eb732e7d20a4ea6a7532ec371d531df1ddccf7c56d3cf527172350
```

Each mutation changed **production** code only, was run, then reverted. Verbatim summaries:

| # | Mutation applied to `_insert_absent_category` | Observed result | Log |
|---|---|---|---|
| **A** | Replace the `if existing is not None: return` early-out with an **overwrite** of `name_en`, `name_pl`, `position`, `inclusion_criterion` + `commit()` — the "keep labels in sync with the dataset" path R-2 warns about | `2 failed, 15 passed in 1.61s` — `test_admin_edited_row_survives_a_reseed_untouched` (AC-7) and `test_partial_dataset_is_completed_without_disturbing_existing_rows` (AC-8). Failure text: `AssertionError: pre-existing row 'home-decor' was disturbed … At index 6 diff: 'The model is chosen mainly for how it looks in a living space, not for a job it performs.' != None` | `e49-2-mutation-A.log` |
| **B** | Replace the early-out with **delete-then-recreate** (`session.delete(existing); session.commit()`, then fall through to INSERT) | `3 failed, 14 passed in 1.68s` — AC-6 `test_seed_is_idempotent_and_byte_stable` **plus** AC-7 and AC-8. Failure text: `At index 0 diff: UUID('77222faa-…') != UUID('637cbd5d-…')` — the `id` changed, proving the row was recreated | `e49-2-mutation-B.log` |
| **C** | **Remove** the `try/except IntegrityError → rollback` around the insert commit | `1 failed, 16 passed in 1.95s` — `test_insert_absent_category_tolerates_a_real_integrity_error` (AC-14), failing with a genuine `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: browse_category.slug` on the `INSERT INTO browse_category …` statement | `e49-2-mutation-C.log` |

**Honest finding about mutation A, recorded rather than papered over.** The story's T3.3 predicted that the overwrite mutation would fail AC-6, AC-7 **and** AC-8. It failed **only AC-7 and AC-8**. AC-6 is unaffected by a pure field overwrite because on an idempotent re-seed the dataset values written are already identical to the stored ones, and `BrowseCategory.updated_at` has a `default_factory` but **no `onupdate`** (`_entities.py:164`), so no observable field changes. That is real information about the suite's sensitivity, not a defect in the check — and it is precisely why **mutation B** was added: recreating the row changes `id` and `created_at`, which is what proves the AC-6 test load-bearing. Both are reported; neither is presented as the original RED, and no knowingly-false assertion was ever written.

**Restoration proven by hash, not asserted.**

```
$ sha256sum apps/api/app/core/db/seed.py
3b88dcc220eb732e7d20a4ea6a7532ec371d531df1ddccf7c56d3cf527172350   # identical to pre-mutation
$ grep -rn "MUTATION" apps/api/app apps/api/scripts apps/api/tests
(no hits — every temporary mutation removed)
$ .venv/bin/python -m pytest tests/test_seed_browse_categories.py -q
17 passed in 1.45s
```

The shipped helper was re-read after restoration and still contains `if existing is not None: return` followed by the `try/except IntegrityError → session.rollback()` branch with no re-query.

**T7.1 — non-regression sweep (AC-15), with the six named files unmodified.** Log: `.hermes/run-logs/e49-2-regression-t7.1.log`.

```
$ .venv/bin/python -m pytest tests/test_orm_migration_parity.py tests/test_migration_0020.py \
    tests/test_migration_0019.py tests/test_browse_category_entity.py \
    tests/test_seed_taxonomy.py tests/test_seed.py -q
36 passed, 1 warning in 6.57s      # re-run at closeout: 36 passed, 1 warning in 6.66s
```

The one warning is the same pre-existing `model`/`model_file` parity `SAWarning` seen at baseline. `alembic` was **not invoked** by any test this story adds.

**T7.2 — exact product-scope proof.**

```
$ git diff --stat -- apps workers infra docs pyproject.toml uv.lock '*.md'
 apps/api/app/core/db/seed.py | 181 +++++++++++++++++++++++++++++++++++++++-
 1 file changed, 180 insertions(+), 1 deletion(-)
$ git ls-files --others --exclude-standard -- apps workers infra docs
apps/api/scripts/seed_browse_categories.py
apps/api/tests/test_seed_browse_categories.py
$ git diff -U0 -- apps/api/app/core/db/seed.py | grep "^-" | grep -v "^---"
-from app.core.db.models import Tag, TagGroup, User, UserRole
```

Exactly the three execution-critical files in §7, and the **only** deleted line in the whole diff is the import line that gained `BrowseCategory` — so `seed_admin`, `STARTER_TAXONOMY`, `seed_taxonomy`, `_upsert_absent_group` and `_insert_absent_tag` are byte-unchanged and the rest of the change is purely additive (`@@ -233,3 +233,182 @@`). Explicit emptiness check on every AC-15 path:

```
$ git diff --name-only -- apps/api/app/core/db/models/ apps/api/migrations/ \
    apps/api/tests/test_orm_migration_parity.py apps/api/app/main.py \
    apps/api/app/core/db/session.py apps/api/scripts/seed_taxonomy.py \
    apps/web workers infra docs pyproject.toml uv.lock
(empty — all byte-unchanged)
$ git diff --check
(clean — no whitespace errors)
```

**T7.3 — lint/format, cwd `apps/api`.**

```
$ .venv/bin/python -m ruff format --check .
275 files already formatted
$ .venv/bin/python -m ruff check .
All checks passed!
```

`ruff format` did reflow the new test module's long string literals once (recorded, not hidden); `ruff check` initially flagged RUF007 on the same line as the `zip` bug above, and both were resolved before the clean run.

**Preliminary `check-all.sh` — STARTED, INTERRUPTED, never completed. NOT the T8.1 gate and NOT a pass.** A standalone run was launched from the repo root and teed to `.hermes/run-logs/e49-2-dev-check-all.log`. It cleared stages 1–9 of 16 and was **killed mid-way through stage 10/16 (`apps/api pytest`)** when the hosting background task was torn down at `max_turns`; the log therefore has **no `EXIT=` line, no `all green.`, and no 16/16 tally**, and stages 11–16 never ran. The full, exact account is in Completion Notes **H**, where the log is labelled INCOMPLETE / non-gate evidence. **T8.1 stays UNCHECKED**: the frozen final gate is controller-owned, must be re-run from the beginning on the final commit, and no dev-session run — least of all an interrupted one — can discharge it.

### Completion Notes List

**A. What was actually implemented.** `STARTER_BROWSE_CATEGORIES` (the approved eight rows, in order, with bilingual labels and the canonical English `inclusion_criterion`), `seed_browse_categories(engine)` and `_insert_absent_category(session, category)` appended to `apps/api/app/core/db/seed.py` after `_insert_absent_tag`, plus `BrowseCategory` added to the existing `app.core.db.models` import line; the deliberate admin-run entrypoint `apps/api/scripts/seed_browse_categories.py`; and the 17-test module `apps/api/tests/test_seed_browse_categories.py`. Nothing else.

**B. Contract adherence, item by item.** Create-if-absent keyed on `slug` with an early `return` — there is **no `UPDATE` path and no `DELETE` path** anywhere in the new code (AC-4, AC-6, AC-7, AC-8, §8.2). Per-row commit inside a single `Session`, matching `seed_taxonomy`'s boundary (AC-13). The `IntegrityError` branch is **exactly** `_insert_absent_tag`'s: catch → `rollback()` → return, with an explicit comment recording that `_upsert_absent_group`'s post-rollback `.one()` re-query was deliberately **not** copied because this seed has no id-returning second phase (AC-14, §8.5). `description_en`, `description_pl` and `parent_id` are absent from every dataset entry, so the ORM defaults leave them `None` (AC-3). No new dependency, no `pyproject.toml`/`uv.lock` change, no schema change, no migration, no refactor of the 41.3 seeder.

**C. Dataset provenance re-verified at source, not copied from §6.** `EXPERIENCE.md:84-91` and `:101-156` were read directly this session. The AC-1 rows match byte-for-byte, and each AC-2 string matches its source sentence under exactly the two declared normalisations. Independently confirmed: **only** `storage-organization` carries markdown emphasis (`*other*`) in the source, so the transformation set is complete. **No discrepancy between the §4 tables and `EXPERIENCE.md` was found**, so the "table wins, report the defect" clause was never triggered. The em dash in `printer-3d`, the Oxford comma in `toys-games` and all Polish diacritics survived (R-4); the tests compare the strings literally.

**D. AC-12 honesty, restated because it matters.** The dataset tests are a **post-decision drift guard** over the approved `(slug, position)` sequence, labels, criteria, charset and density. They do **not** re-derive, re-execute or corroborate the live-distribution evidence — a unit test on an empty `tmp_path` SQLite file has no access to the real catalogue. That is stated in the test module docstring and in the `seed.py` dataset comment, which carries the §6 F-1 citation including both independent verdicts and the zero-margin `replacement-parts` finding. **Nothing in this pass re-measured the live catalogue.**

**E. AC-10 verified two ways.** `apps/api/app/main.py` is byte-unchanged (T4.3, empty `git diff --name-only`), and two source-level tests enforce it going forward: `seed_browse_categories` does not appear in `main.py`'s source, and a walk of `app/**/*.py` asserts the only file mentioning the symbol is `app/core/db/seed.py`. Both are import-free grep-equivalents, so an accidental lifespan wiring becomes a failing test rather than a silent behaviour change (R-3).

**F. Test-suite scope.** 17 tests: 6 dataset-shape (AC-1, AC-2, AC-3, AC-12), 5 seeding behaviour (AC-5 … AC-9), 2 no-boot-wiring (AC-10), 2 entrypoint (AC-11), 1 mid-run-failure convergence (AC-13), 1 real-`IntegrityError` race (AC-14). Deliberate non-vacuity measures: the AC-13 test injects `RuntimeError` (never `IntegrityError`, which is swallowed by design) on the **4th** commit so the partial state is a **non-empty strict** subset (R-6); the AC-9 test creates a real `ModelTag` row and asserts `model_tags_before` is non-empty before comparing, so "unchanged" is not trivially true; the AC-11 pair includes a case with one extra admin-created row where the DB holds **9** categories, so printing `len(STARTER_BROWSE_CATEGORIES)` would say 8 and be caught. Every test runs against a throwaway `tmp_path` SQLite database via `create_engine_for_url` + `init_schema` — **no live DB, no Docker, no network, no Redis, no `TestClient`, no Alembic, no sleeps, no randomness**.

**G. Toolchain links never entered the diff.** `git ls-files | grep -E "\.venv|node_modules"` returns nothing, and the final `git status --porcelain --untracked-files=all` lists only the five intended paths. The three symlinked toolchains stayed invisible to git throughout.

**H. Preliminary `check-all.sh` — INTERRUPTED, INCOMPLETE, and explicitly NOT a gate result.**

A standalone `bash infra/scripts/check-all.sh` was started from the repo root and teed to the gitignored `.hermes/run-logs/e49-2-dev-check-all.log`. What actually happened, stated exactly:

- It **started cleanly and advanced through stages 1–9** of 16 — `apps/api ruff format`, `apps/api ruff check`, `workers/render ruff format`, `workers/render ruff check`, `apps/web typecheck`, `apps/web production build`, `apps/web lint (eslint + stylelint)`, `apps/web vitest`, and then entered `apps/api pytest`. The script fails fast, so advancing past a stage implies that stage returned 0; the log shows nine `==>` stage banners and no stage failure.
- It **entered stage 10/16 (`apps/api pytest`) and was still progressing when it was killed** — last progress observed live in-session at ~44 %, and the partial log ends mid-stage at the `[ 80%]` progress line.
- **The run was killed, not finished:** the Claude background task hosting it was torn down when that agent run hit `max_turns`. Consequently the log contains **no `EXIT=` line, no `all green.` line, and no 16/16 stage tally** — verified by `grep -n "EXIT=\|all green"` returning **zero matches**.
- **Therefore there is NO exit-0, NO `all green.`, and NO preliminary PASS.** The file `.hermes/run-logs/e49-2-dev-check-all.log` is **INCOMPLETE, non-gate evidence** and must not be read, cited or summarised as a passing gate run. Stages 11–16 (`infra/scripts pytest`, `apps/web visual regression`, `settings-env-compose-diff`, both `uv-lock-check` stages, `local-env-secrets`) **never ran at all**.
- **This is not an implementation blocker.** T8.1 is controller-owned by design and will be re-run **from the beginning** on the final commit as the frozen gate. **T8.1 stays UNCHECKED**, exactly as it would have if this preliminary run had never been attempted. No conclusion about the branch's gate status is drawn here in either direction.

**Side effect of that run, found and cleaned up.** The `apps/web typecheck` stage (`tsc -b`) emitted two declaration byproducts, `apps/web/vitest.config.d.ts` and `apps/web/vitest.setup.d.ts`, as **untracked and non-ignored** files at 15:22:50. They contain no authored content, are absent from the primary checkout, and would have polluted a `git add -A` by the controller, so they were **deleted** and the final `git status` re-verified clean. Flagged for the controller because a fresh `check-all.sh` run in this worktree will regenerate them — this is a pre-existing environmental wrinkle of the typecheck stage, not something this story introduced.

**I. Disclosed deviations from the base workflow.**

1. **`baseline_commit` was overwritten**, against the skill's step-4 rule "if front matter already contains `baseline_commit`, preserve the existing value". The controller directed that front matter record the **actual implementation baseline** `88a683a…`; `df922f9` is preserved losslessly in a new `create_validate_baseline_commit` key and in §16. Recorded rather than silently applied.
2. **`persistent_facts` glob matched no file** in this worktree — executed-and-empty, not skipped.
3. **The skill body was read from the primary checkout** because `.claude/skills/` is untracked and absent here.
4. **No subagents and no research tools were used**; this session's harness forbids launching agents unless the user asks. All analysis was inline against `88a683a`.
5. **§2's G26-DEVGO line was rewritten** from "open" to the granted-by-controller current state. This is a Status/record area correction required by the controller input; §16 still preserves the gate's open-at-validation-time posture.

**J. Limitations, stated plainly.**

- **The seed has never been executed against any real database.** Every run was a scratch `tmp_path` SQLite file. The live invocation is a post-merge controller/admin action and is explicitly **not** done.
- **No live-catalogue claim is made or re-verified here** (see D).
- **T1.1 was run at `88a683a`, not literally at `df922f9`** as the task text says. `88a683a` is docs-only on top of `df922f9`, so `apps/api/` is byte-identical; the substitution is recorded for transparency.
- **One test-code defect of my own** (`zip(..., strict=True)` on unequal lengths) occurred and is recorded above rather than silently amended.
- **Mutation A did not fail AC-6**, contrary to T3.3's prediction; mutation B was added to prove AC-6 load-bearing. Both outcomes are reported.
- **The preliminary `check-all.sh` run was interrupted mid-stage-10 and never produced a verdict** — no exit-0, no `all green.`, stages 11–16 unrun (Note H). It discharges nothing, and **T8.1 remains unchecked**. No determinism triple, native code review or Aider review was performed in this session either.

**K. NOT DONE in this pass — explicitly, so no reader infers otherwise.** Native `bmad-code-review` (§18 stays empty) · independent external Aider review `laura-aider-review-diff` (§19 stays empty) · the controller's frozen final `check-all.sh` gate (T8.1) · the NFR26-DETERMINISM-1 three-identical-run determinism triple (T8.2) · review loop-back (T8.3) · commit, push, ff-only merge (T8.4) · deploy · any live-database access or production seeding · controller final disposition (§20 stays empty). **No Ezop signature, Ezop review, controller sign-off or reviewer verdict is recorded, implied or claimable from this record.** The working tree is left **uncommitted** for a fresh reviewer.

### File List

**Execution-critical product files — exactly 3, as predicted in §7:**

| File | Action |
|---|---|
| `apps/api/app/core/db/seed.py` | **MODIFIED** — +180 / −1 (the −1 is the `BrowseCategory` import line; all pre-existing symbols byte-unchanged) |
| `apps/api/scripts/seed_browse_categories.py` | **NEW** — admin-run entrypoint (AC-11) |
| `apps/api/tests/test_seed_browse_categories.py` | **NEW** — 17 tests covering AC-1 … AC-14 |

**Workflow records — 2, not counted in the three:**

| File | Action |
|---|---|
| `_bmad-output/implementation-artifacts/49-2-starter-category-seed.md` | **MODIFIED** — front matter baselines, `Status: review`, §2 G26-DEVGO current state, T1–T7 checkboxes, this §15, §21 Change Log |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | **MODIFIED** — `49-2-starter-category-seed: ready-for-dev → review`, `last_updated`; `epic-49` untouched at `in-progress` |

**Deleted files:** none. **Other tracked files changed:** none. Local `.hermes/run-logs/*` evidence is gitignored and deliberately not tracked.

## 16. Validation Record

**Create pass (this document).** Native `bmad-create-story` action=`create`, 2026-07-26, Claude Opus 5 agent session, baseline HEAD `df922f955fea42bbdbc76827406b008d28733718`, branch `docs/init26-e49-2-create-validate`, working tree clean. Routed via native `bmad-help` (which read `_bmad/_config/bmad-help.csv` + `resolve_config.py`, found phase `4-implementation` with a sprint plan present, `49-1` `done` and `49-2-starter-category-seed` `backlog`, and routed to the required next step **[CS] Create Story**, `bmad-create-story`, action `create`). Skill customization resolved via `resolve_customization.py --skill .claude/skills/bmad-create-story --key workflow`: **no team or user override** (`_bmad/custom/` contains only `config.toml` and a `.gitignore`), `activation_steps_prepend` / `activation_steps_append` / `on_complete` all empty, `persistent_facts` = `file:{project-root}/**/project-context.md`, satisfied by `_bmad-output/project-context.md` and loaded as foundational context. `checklist.md` executed against the draft before finalising.

Every file:line claim in §6, §8 and §12 was traced this session against HEAD `df922f9` — none is carried from the epic sketch. **No code, no migration, no test and no live database was touched. No commit, push, merge or deploy was performed.**

**Validate pass — VERDICT: `PASS`.**

**Route and provenance.** Native `bmad-create-story`, action `validate` (menu **VS**), 2026-07-26, **fresh independent Claude Opus 5 context** — no create-pass conversation state carried in. Routed via native `bmad-help`, which resolved `_bmad/scripts/resolve_config.py` (`communication_language: Polish`, `document_output_language: English`, `implementation_artifacts: {project-root}/_bmad-output/implementation-artifacts`) and read `_bmad/_config/bmad-help.csv` → row `BMad Method,bmad-create-story,Validate Story,VS,…,validate,…,4-implementation,preceded-by bmad-create-story:create,followed-by bmad-dev-story,required=false`. Skill customization resolved via `resolve_customization.py --skill .claude/skills/bmad-create-story --key workflow`: **no team or user override**, `activation_steps_prepend`/`append` and `on_complete` empty, `persistent_facts = file:{project-root}/**/project-checkout-context.md` glob satisfied by `_bmad-output/project-context.md`, loaded as foundational context. The native `checklist.md` ("Story Context Quality Competition Prompt") was executed end to end: Step 1 target load, Step 2 exhaustive source re-analysis (2.1 epics, 2.2 architecture, 2.3 previous-story intelligence, 2.4 git history, 2.5 library/version check), Step 3 disaster-prevention gap analysis (3.1–3.5), Step 4 LLM-optimisation analysis, Steps 5–7 improvement application. Baseline HEAD `df922f955fea42bbdbc76827406b008d28733718`, branch `docs/init26-e49-2-create-validate`.

**Independent re-trace — every claim re-derived from source, not read back from §6.**

- **Approved content.** `EXPERIENCE.md:80-91` eight-row table and `:101-156` criteria re-read directly: AC-1's `(position, slug, name_pl, name_en)` rows match byte-for-byte, and each AC-2 string matches its source sentence under exactly the two normalisations now spelled out in AC-2. Independently confirmed that **only** `storage-organization` carries markdown emphasis in the source, so the transformation set is complete and deterministic.
- **Live-evidence dataset.** `sha256sum` of `.hermes/run-logs/e49-2-live-model-name-tags-20260726.json` = `4597db802722a069ba2548cbd79e9bf8115489fe69d01f6cae39e9a5071c8800` — **matches the controller's stated digest**. Structure independently inspected: `mode: sqlite-uri-read-only`, `active_model_count: 131`, 131 records, keys exactly `{name, tag_slugs, tag_names_en, tag_names_pl}` — no ids, no paths, no user data. Zero-tag count re-computed independently: **31 of 131 = 23.7 %** (F-1's "~24 %" is correct).
- **The ≥ 3 gate, re-checked rather than accepted.** All 131 records were read and classified against `EXPERIENCE.md:101-186`. Every one of the eight clears ≥ 3 by a wide margin except `replacement-parts`, which yields **exactly three**: `3D Printable Switch Replacement`, `Jura Coffee Machine Parts (for Jarek)`, `Quechua Backpack Buckle 50x55mm` — **the identical three both controller analyses name**. The excluded near-misses were re-tested individually and each exclusion holds under a rule already written in `EXPERIENCE.md:180-186` (notably `VW Crafter USB/Switch Mount` → holders/electronics, `Rosa3D Spool Adapter` + all K1 parts → `printer-3d` under "printer-specific always wins", `Ben's … Dropper Post Seat Bag Adapters` → holders, nothing restored). Both reports were read directly and their verdicts confirmed as literal `PASS`. **The `EXPERIENCE.md:192` obligation is discharged; its remedy clause is not triggered.**
- **41.3 precedent and AC-13/AC-14 ceiling.** `seed.py:160-192,195-214,217-236`, `scripts/seed_taxonomy.py:1-50` and all 364 lines of `tests/test_seed_taxonomy.py` re-read at HEAD. AC-14 is **exactly** `_insert_absent_tag`'s accepted pattern (catch → rollback → return; no re-query, no update), and the shipped `test_insert_absent_tag_tolerates_real_integrity_error` (`:316-348`) already proves *"racer's row exists and is preserved, exactly one row"* — so T5.2 reproduces a proven contract rather than widening `IntegrityError` swallowing. AC-13's per-row commit boundary is confirmed against `seed.py:167-171`. The create-if-absent, never-update contract is preserved verbatim.
- **Entity reality.** `_entities.py:130-164` re-read: `slug` is a bare `str` with an explicit `Index("uq_browse_category_slug", "slug", unique=True)` → duplicate INSERT does raise at DB level, so AC-14 is load-bearing; `updated_at` has a `default_factory` and **no `onupdate`**, so AC-6's "`updated_at` unchanged after re-run" is satisfiable exactly as written; `name_en` NOT NULL, everything else nullable, `position` defaults to 0.
- **No-boot-wiring.** `main.py:64-93` re-read: `lifespan` calls `seed_admin` and nothing else. AC-10 is accurate.
- **`check-all.sh` stage count.** `grep -n run_stage infra/scripts/check-all.sh` → 17 hits: definition at `:30` plus 16 invocations (`:54,57,60,63,66,77,80,83,86,89,95,98,104,110,112,119`). F-8's "16/16" is verified.
- **Baseline test execution (read-only).** `pytest tests/test_seed_taxonomy.py tests/test_seed.py tests/test_browse_category_entity.py tests/test_orm_migration_parity.py tests/test_migration_0020.py -q` → **33 passed, 1 warning in 5.45s** (the pre-existing `model`/`model_file` `SAWarning` in the parity gate, unrelated). This proves the T1.1 baseline is green and any later red is caused by this story. **Provisioning caveat, stated rather than hidden:** this worktree has no provisioned `apps/api/.venv` (`ModuleNotFoundError: No module named 'fakeredis'` on `conftest.py`), and installing one would need network, which this pass is forbidden. The suite was therefore run in the primary checkout `/home/ezop/repos/3d-portal`, verified first to be at the **identical** commit `df922f9` with a clean working tree, so the executed code is byte-identical to this baseline. Only `tmp_path` SQLite databases were touched; no live database, no network, no writes to tracked files.
- **Commit-shape precedent.** `git show --stat df922f9` → **9 paths**: 7 product files **plus** the 49.1 story artifact **plus** `sprint-status.yaml`. This falsified the create pass's "one commit, three paths" framing and drove the §7/§11/T7.2 correction.
- **F-10 re-verified, still reported-not-fixed.** `architecture.md:3351` does still say "separate admin-run seed story (49.3)". Correct disposition (`bmad-correct-course` territory); harmless to execution.

**Amendments applied in this pass** (the story now reads as a single coherent document; each item below is a real correction, not a rephrasing):

1. **§6 F-1 rewritten.** The stale single-capture citation is replaced by the complete two-review proof: the primary dataset with its verified SHA-256, both independent analyses with their verdicts and counts, an explicit statement of *why* the two count sets legitimately differ (full M:N curation vs conservative lower bound), and the conclusion "keep the eight, reorder/merge/remove nothing".
2. **§6 F-3 rewritten.** The false claim that `replacement-parts` has *no affirmative ≥ 3 signal* is removed. It is replaced by the affirmative record: the three named records both analyses agree on, the explicitly re-tested exclusions, and the honest characterisation — **passes with zero margin**, hence a priority curation / tiny-category monitoring item for 52.3, not a shortfall and not a reorder trigger. §2, AC-12, §9 R-1 and the `sprint-status.yaml` narrative were realigned to match.
3. **AC-12 re-titled and re-scoped for honesty.** It no longer claims the live evidence is "made executable". It now states plainly that no unit test in this story can re-derive the live distribution, that the dataset + two reports discharge the live gate, and that the test is a **post-decision drift guard** pinning the approved eight `(slug, position)` rows against silent reorder/rename/drop.
4. **§5 restructured — the manufactured-negative-assertion instruction is removed.** The old T3.1 (*"temporarily assert the negative"*) is gone. The section now opens with a four-point RED→GREEN contract: the complete test module is authored before any production symbol exists (T2, red for the right reason), production code follows (T3), and tests that pass by construction are proven load-bearing by a **labelled mutation sensitivity check** on the production code (T3.3 — mutate, observe failure, revert, prove the revert with `git diff`), explicitly never presented as the original RED. T6 was re-sequenced accordingly.
5. **File/commit accounting corrected (§7, §11, T7.2).** "Three files, one commit" becomes "**three execution-critical product files** + the two workflow files (story artifact, `sprint-status.yaml`) in the closeout commit, the verified `df922f9` shape". T7.2's `git diff --stat` assertion is now scoped to product paths so it cannot contradict the required review→done records. The planning branch is stated as a separate `docs(init26):` commit preceding the implementation branch.
6. **§2 live posture added.** E49.1 pushed and deployed; live revision `0020_browse_categories`; both tables present; 132 `model` rows preserved; `browse_category` = 0; `model_browse_category` = 0; integrity ok; 0 FK violations — with the explicit rider that this pass performed no live access and that dev/review use only scratch databases, the live seed being a post-merge admin action. Mirrored into §8.5.
7. **AC-2 normalisation made explicitly deterministic.** Exactly two transformations, in order (strip `*` emphasis — affecting only `storage-organization`; capitalise the first letter), everything else preserved byte-for-byte including the trailing stop, the `printer-3d` em dash and the `toys-games` comma; the §4 table declared authoritative over any dev-agent re-derivation. Confirms the single-field, English-only, no-schema-change decision without inventing content.
8. **§6 F-6 corrected.** Its `grep` claim under-counted: the pattern also matches `migrations/versions/0020_browse_categories.py`, `tests/test_migration_0020.py` and `tests/test_migration_0004.py`. The conclusion is unchanged (no application write path exists) and the `0019`-era `has_browse_category: false` is now paired with the current live reality.
9. **AC-14 ceiling made explicit (§8.5).** Added the verified instruction not to copy `_upsert_absent_group`'s post-rollback `.one()` re-query, with the reason (it exists only to return an id for the tag phase, which this story does not have) — closing the most likely route to accidentally broadening `IntegrityError` handling.
10. **T4.1 widened to match AC-9's own wording** — `Tag`, `TagGroup` and `ModelTag` row sets are now asserted unchanged alongside `Model` and `ModelBrowseCategory`, so "writes `browse_category` and nothing else" is actually tested.
11. **Minor:** §6 F-4 now states why name+tag classification is honest evidence while "crosses ≥ 2 tag groups" stays design rationale; §12 gains the dataset, both reports and the `:316-348` anchor.

**Real blockers: none.** No finding survived verification as a blocker. Every item the controller flagged was either a genuine defect (items 1–5 above, all fixed) or a claim that verification **confirmed** rather than overturned: AC-13/AC-14 sit exactly on the shipped 41.3 pattern and do not broaden it; the inclusion-criterion decision needed no schema or field change; the hard non-goals in §10 (no assignments, no boot auto-seed, no migration edit or new migration, no API/UI/admin CRUD, no dependency or lock change, no live seed during dev/review) are intact and were re-checked one by one after every amendment.

**Status transition:** `ready-for-validation` → **`ready-for-dev`**, mirrored to `sprint-status.yaml` key `49-2-starter-category-seed`. `epic-49` remains **`in-progress`**, untouched.

**What this pass did NOT do.** No code, no test, no migration, no dependency and **no live database** was touched; the only file writes were this artifact and `sprint-status.yaml`. No commit, push, merge or deploy. **No human review of this document had occurred at validation time: no Ezop and no Laura sign-off is recorded, implied, or claimable.** This verdict is a Claude/native BMAD validation verdict and nothing more. **G26-DEVGO was still controller-owned and open at validation time; the later controller decision is recorded immediately below.**

### Independent pre-development specification review (Aider)

Read-only `laura-aider-review-repo` reviewed this story against the canonical `EXPERIENCE.md` rows/criteria and the real 41.3 seed/entity/script/test precedent. Verdict: **`APPROVE`** — Critical 0, Important 0, Missing tests 0. Two minor notes were controller-audited: the AC-2 marker note is already explicit because the transformation applies to the sentence after the label and names the sole inline `*other*`; the T5.1 note is already satisfied by `N = 4`, three committed rows and the required non-empty strict subset. Evidence: `.hermes/run-logs/e49-2-predev-aider-review-20260726.log` (local, gitignored).

### Controller pre-development gate — G26-DEVGO

**GRANTED for Story 49.2 on 2026-07-26 by Laura/controller.** Basis: the user's standing authorization to continue Initiative 26; native create completed; fresh native validation recorded `PASS`; the 131-model read-only distribution gate passed two independent reviews and the validator's own re-check; controller consistency audit passed; independent Aider specification review returned `APPROVE` with Critical 0, Important 0 and Missing tests 0.

This is a **controller decision**, not an Ezop signature, Ezop review, or claim that Ezop read this artifact. The grant is scoped only to the three execution-critical product files and the workflow records specified here. It does not authorize model assignments, boot auto-seeding, migration edits/new migrations, API/UI/admin CRUD, dependency/lock changes, implementation on this planning branch, live database access, production seeding, push, merge or deploy.

**Next step.** A **fresh native `bmad-dev-story` session** on a separate `feat/E49.2-starter-category-seed` branch/worktree off `main` after this planning branch is controller-committed and integrated ff-only. Implementation must not begin on this planning branch.

## 17. Disclosed deviations from the base workflow

1. **Status set to `ready-for-validation`, not `ready-for-dev`.** The base skill template hard-codes `ready-for-dev` at create and writes that into `sprint-status.yaml` (step 6). This project's repeated precedent is the two-step form — create → `ready-for-validation`, then `:validate` → `ready-for-dev` — recorded in `sprint-status.yaml:2` for Stories 43.1, 43.2, 43.3, 47.5 and 49.1, and matching `bmad-help.csv`'s own sequencing (`create` → `followed-by: bmad-create-story:validate`). Project convention governs; the divergence is recorded rather than silently applied.
2. **`epic-49` is left at `in-progress` and not otherwise touched.** The base workflow's auto-promote branch applies only to the *first* story of an epic; 49.2 is not the first, and `epic-49` was already flipped to `in-progress` at 49.1's dev-story pass. No epic-level change was made.
3. **No research subagents were used.** The workflow invites them; this session's harness forbids launching agents unless the user asks. All analysis was inline against HEAD `df922f9`.
4. **Step 4 (web research) produced nothing to include.** This story adds no dependency and uses only APIs already exercised by `seed_taxonomy` at HEAD, so there is no external version or breaking-change context worth carrying. Recorded as executed-and-empty rather than skipped.

## 18. Native code-review record (`bmad-code-review`)

**VERDICT: `APPROVE`** — Critical 0, Important 0. Minor findings are listed below and are explicitly non-blocking.

### 18.1 Reviewer identity, route and posture

**Claude Opus 5** (`claude-opus-5`), native BMAD `bmad-code-review` workflow (menu **CR**), **fresh independent reviewer context** — no create, validate or dev-story conversation state carried in. 2026-07-26.

**Route.** Started with native `bmad-help` → read `_bmad/_config/bmad-help.csv` → row `BMad Method,bmad-code-review,Code Review,CR,…,4-implementation,preceded-by bmad-dev-story,required=false`, and routed here and nowhere else. Skill customization resolved with `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow` → `activation_steps_prepend = []`, `activation_steps_append = []`, `on_complete = ""`, `persistent_facts = ["file:{project-root}/**/project-context.md"]`; **no team or user override** (`_bmad/custom/bmad-code-review.toml` and `.user.toml` both absent). Unlike the dev-story pass, the `persistent_facts` glob **did** match here: `_bmad-output/project-context.md` was loaded as foundational context. Config from `_bmad/bmm/config.yaml` (`user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`). Step files `step-01-gather-context.md` → `step-02-review.md` → `step-03-triage.md` → `step-04-present.md` were executed in order; the skill bodies were read from the primary checkout `/home/ezop/repos/3d-portal/.claude/skills/` because `.claude/skills/` is untracked and absent from this worktree.

**Posture.** Reviewer only. **No product code, test, dependency file, `.gitignore`, planning artifact or toolchain link was modified.** The only file written by this pass is this §18. §15 and §16 were read but **not** altered. No commit, push, merge, deploy, live-database access or seed-CLI invocation against any non-scratch database occurred.

### 18.2 Exact review target

| Item | Value |
|---|---|
| Worktree | `/home/ezop/worktrees/3d-portal-e49-2-dev` |
| Branch | `feat/E49.2-starter-category-seed` |
| Baseline `HEAD` | `88a683a51916aa02a57f085471963de4320558e6` (verified with `git rev-parse HEAD`) |
| Diff mode | **uncommitted** (tracked `git diff HEAD` + untracked product files) |
| Spec | `_bmad-output/implementation-artifacts/49-2-starter-category-seed.md`, `review_mode = full` |

**Tracked-path audit — exactly the five expected paths, no sixth.** `git diff HEAD --name-only` → `apps/api/app/core/db/seed.py`, `_bmad-output/implementation-artifacts/49-2-starter-category-seed.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml`. `git ls-files --others --exclude-standard` → `apps/api/scripts/seed_browse_categories.py`, `apps/api/tests/test_seed_browse_categories.py` (2 untracked, no more). `git ls-files | grep -cE "\.venv|node_modules"` → **0**. `git diff --check` → clean. `sprint-status.yaml` parses as YAML with `49-2-starter-category-seed: review` and `epic-49: in-progress`. Diff size 181 changed lines in `seed.py` (+180 / −1) plus 45 + 505 new lines — well under the step-01 chunking threshold, so the whole diff was reviewed in one pass.

### 18.3 Review layers executed

The three native layers (**Blind Hunter** / `bmad-review-adversarial-general`, **Edge Case Hunter** / `bmad-review-edge-case-hunter`, **Acceptance Auditor**) were all executed against the full diff and this story. `{failed_layers}` is **empty** — no layer failed, timed out or returned empty.

**Disclosed deviation (same class as §15 Note I.4 and §17.3).** Step 2 directs that the layers run as parallel subagents at equal model capability. This session's harness forbids launching agents unless the user asks, and the controller input did not ask. The skill's stated fallback is to emit prompt files and HALT — which would have produced no verdict at all, defeating the controller's explicit requirement. The three layers were therefore executed **inline in this same fresh context**, each following its own native skill body (read from the primary checkout), at full session capability. This is recorded rather than silently applied. Consequence, stated honestly: the layers did not run blind of one another, so cross-layer independence is weaker than the workflow intends. It was compensated for by deriving the findings from **executed evidence** (§18.4) rather than from reading the diff alone.

### 18.4 Independently verified evidence (executed this pass — not read back from §15)

Every item below was produced by this reviewer in this worktree. Nothing here is quoted from the implementer's record.

1. **Dataset byte fidelity against the canonical spine — PASS.** `EXPERIENCE.md:84-91` (rows) and `:103-153` (the eight `- **Inclusion criterion:**` lines, inside the cited `:101-156` block) were parsed mechanically and compared field-by-field against `STARTER_BROWSE_CATEGORIES` extracted from `seed.py` via `ast.literal_eval`. Result: **8/8 rows byte-identical** in `(position, slug, name_pl, name_en)` and in list order; **8/8 criteria byte-identical** under exactly the two declared normalisations (strip `*`, capitalise first letter) and **nothing else**. The `printer-3d` em dash survives as **U+2014** (the only non-ASCII character in any criterion); the `toys-games` Oxford comma, all Polish diacritics and every trailing full stop survive. Independently confirmed that `storage-organization` is the **only** source sentence carrying markdown emphasis, so the declared transformation set is complete. **AC-1 and AC-2 hold at the byte level; the §4 tables, the test's `_APPROVED_*` copies and `EXPERIENCE.md` all agree.**
2. **Exactly one criterion field, no invented content — PASS.** `_entities.py:157` is `inclusion_criterion: str | None = None` (single field). The extracted dataset carries exactly the keys `{slug, name_en, name_pl, position, inclusion_criterion}` — `description_en`, `description_pl` and `parent_id` appear in **no** entry (AC-3).
3. **Independent mutation sensitivity checks — the preservation and race tests are load-bearing.** Rather than editing tracked files, `_insert_absent_category` was replaced **in memory** by a reviewer-authored pytest plugin (`-p`, `PYTHONPATH=/tmp`), leaving every repository file untouched. Results: **(A) overwrite-instead-of-skip → 3 failed / 14 passed**; **(B) delete-then-recreate → 4 failed / 13 passed** (adds AC-6 `test_seed_is_idempotent_and_byte_stable`, failing on a changed row `id`); **(C) remove the `try/except IntegrityError` → exactly 1 failed / 16 passed**, and the single failure is `test_insert_absent_category_tolerates_a_real_integrity_error`. My A and B mutants also lack the handler, which is why they additionally fail the AC-14 test — that is an artefact of my harness, **not** a discrepancy with §15's 2/15, 3/14 and 1/16. The load-bearing conclusion is identical and independently reproduced: no preservation test is vacuous, and the `IntegrityError` branch is proven by a genuine `UNIQUE constraint failed: browse_category.slug`, not mocked away.
4. **AC-13 convergence is non-vacuous — verified by direct probe, not by trusting the test's own assertion.** With `Session.commit` failing on the 4th call, the run leaves **exactly 3** durably committed rows (`storage-organization`, `home-decor`, `holders-mounts`) — a non-empty **strict** subset with no duplicates — and a clean re-run converges to exactly **8** rows with **zero** duplicates. Per-row commit boundary confirmed.
5. **AC-11 entrypoint exercised against a throwaway scratch SQLite file** (`/tmp`, deleted afterwards): `main(engine=…)` run twice printed `seeded browse categories: 8 categories present` both times — idempotent, and the count is genuinely a post-seed `SELECT` against the database. **No real, live or production database was opened at any point in this review.**
6. **AC-10 no-boot-wiring — verified two ways beyond the tests.** `app/main.py:64-93` `lifespan` calls `seed_admin` and nothing else, and the file is byte-unchanged in `git diff`. A repo-wide grep for `seed_browse_categories|STARTER_BROWSE_CATEGORIES` returns hits in **only** `app/core/db/seed.py`, `scripts/seed_browse_categories.py` and the new test module — plus `grep -rn` over `infra/` and `docs/` returns **nothing**, so no deploy script or runbook auto-invokes it either.
7. **Story 41.3 behaviour untouched — PASS.** The **only** deleted line in the entire product diff is the `from app.core.db.models import …` line that gained `BrowseCategory`; the rest is purely additive after `_insert_absent_tag`. `seed_admin`, `STARTER_TAXONOMY`, `seed_taxonomy`, `_upsert_absent_group` and `_insert_absent_tag` are byte-unchanged.
8. **Targeted regression + lint — PASS, executed by me.** `pytest tests/test_seed_browse_categories.py -q` → **17 passed**. `pytest tests/test_orm_migration_parity.py tests/test_migration_0020.py tests/test_migration_0019.py tests/test_browse_category_entity.py tests/test_seed_taxonomy.py tests/test_seed.py -q` → **36 passed, 1 warning** with all six files unmodified; the one warning is the pre-existing `model`/`model_file` `SAWarning`. `ruff format --check .` → `275 files already formatted`; `ruff check .` → `All checks passed!`. `grep -c alembic` on the new test module → **0**.
9. **No mutation residue.** `sha256sum apps/api/app/core/db/seed.py` = `3b88dcc220eb732e7d20a4ea6a7532ec371d531df1ddccf7c56d3cf527172350`, matching the value §15 records both before and after its mutation checks; a grep for `MUTATION|TODO|FIXME|XXX|HACK` across all three product files returns **no hits**.
10. **Provenance claim in the dataset comment is true.** `git show --stat 48db6bb` confirms that commit added `ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md`, so "G26-CAT-SET closed this content on 2026-07-26 (commit `48db6bb`)" is accurate rather than asserted.

### 18.5 Acceptance Auditor result

**AC-1 … AC-15: all satisfied**, each against executed evidence rather than the implementer's prose — AC-1/AC-2 by §18.4-1, AC-3 by §18.4-2 plus the persisted-state assertions in `test_seed_populates_exactly_the_eight_approved_rows`, AC-4 by code reading at `seed.py:393-414`, AC-5/AC-6/AC-7/AC-8 by §18.4-3 and the green suite, AC-9 by `test_seed_writes_nothing_outside_browse_category` (which guards its own non-vacuity with `assert model_tags_before`), AC-10 by §18.4-6, AC-11 by §18.4-5, AC-12 by the drift-guard tests plus the honest framing carried in both the module docstring and the `seed.py` comment, AC-13 by §18.4-4, AC-14 by §18.4-3(C), AC-15 by the empty `git diff --name-only` over every named path plus §18.4-8.

**AC-16 is NOT claimed by this review and is NOT dischargeable by it.** It is controller-owned; all four T8 boxes remain unchecked and **this reviewer did not tick any of them**.

**Binding constraints §3.1–§3.10: all held.** In particular §3.3 (no `UPDATE`, no `DELETE` path anywhere in the new code — verified by reading `_insert_absent_category` in full), §3.5 (zero `model_browse_category` writes), §3.6 (no migration touched, no new revision), §3.9 (the 41.3 shape extended, not refactored) and §3.10 (strict RED→GREEN, with the load-bearingness independently re-derived rather than accepted).

### 18.6 Findings

**Critical: 0. Important: 0.**

**Minor — non-blocking, listed for the record; none of them gates the merge, and this reviewer applied no patch.**

| # | Finding | Location | Disposition |
|---|---|---|---|
| M-1 | The post-condition prints `COUNT(*)` over the whole table, so "a partial seed is visibly distinguishable from a full one" is strictly true only while the table holds no non-approved rows. A future state with 3 extra admin-created rows and 3 missing approved slugs would also print `8`. | `apps/api/scripts/seed_browse_categories.py:39-41` | **Defer, do not patch.** AC-11 pins both the DB-queried source and the literal output format, so "fixing" this would deviate from the approved AC. It cannot arise on the live first run (§2 records `browse_category` = 0), and the 9-row test already covers the direction that matters. |
| M-2 | The drift guard compares `STARTER_BROWSE_CATEGORIES` against a hand-copied `_APPROVED_ROWS` / `_APPROVED_CRITERIA` in the test; neither is bound to `EXPERIENCE.md` itself, so a *coordinated* transcription error in both copies would pass. | `apps/api/tests/test_seed_browse_categories.py:50-87` | **Defer.** No such error exists — §18.4-1 verified all three transcriptions against the canonical source byte-for-byte. A markdown-parsing test would couple the suite to a planning artifact's formatting; the deliberate second copy is what AC-12 asked for and is the right call. |
| M-3 | The dataset comment runs ~40 lines and embeds session provenance, both subagent verdicts and `.hermes/run-logs/` filenames that are gitignored and therefore unverifiable by any future repository reader. Above the project comment policy's "WHY when non-obvious, skip narrative WHATs". | `apps/api/app/core/db/seed.py:242-281` | **Defer.** Its load-bearing half (why never-update, why single-field English, why not a tree) is genuinely non-obvious and belongs there; only the evidence-history half will rot. Trimming it is taste, and §3 forbids opportunistic edits in this commit. |
| M-4 | `except IntegrityError` catches *any* integrity violation, not only the `uq_browse_category_slug` race, and returns without confirming a row exists for that slug. | `apps/api/app/core/db/seed.py:409-414` | **Dismiss as by-design.** This is exactly the shipped `_insert_absent_tag` contract that §3.9, AC-14 and §8.5 require and explicitly forbid widening; the deliberate comment about not copying `_upsert_absent_group`'s re-query is correct. The table currently carries no other constraint the dataset can violate. |
| M-5 | *(Edge Case Hunter)* A concurrent SQLite writer raises `OperationalError: database is locked`, not `IntegrityError`; that path is unguarded and aborts the run mid-way. | `apps/api/app/core/db/seed.py:407-414` | **Defer, pre-existing class.** Identical exposure to `seed_taxonomy` and to `seed_admin` at boot; recovery is exactly AC-13's converge-on-re-run, which §18.4-4 proved works. Not caused by this change. |

**Deletion check (Edge Case Hunter step 4):** the single removed line is the import statement, re-established in the same hunk with `BrowseCategory` added. No orphaned reference, no dead code, no retired contract. **No deletion finding.**

**Explicitly checked and found clean** (the controller's adversarial list, each negative confirmed rather than assumed): no tautological dataset comparison (the second copy is deliberate and externally validated); no vacuous assertion (AC-9 and AC-13 both carry explicit non-vacuity guards, and I re-derived AC-13's "3 rows" myself); no implementation-coupled mock that bypasses behaviour (the AC-14 test makes the real database raise a real `IntegrityError` — proven by mutation C); no manufactured RED (both recorded REDs are collection errors from genuinely absent symbols, and no knowingly-false assertion exists anywhere in the module); no hidden mutation residue (hash + grep, §18.4-9); no scope drift (exactly three product files, §18.2); no model↔category assignment; no boot wiring; no schema, migration, ORM, API, UI, locale or dependency change.

**Story-record honesty — audited, and it holds.** §15 and the `sprint-status.yaml` narrative both state plainly that the preliminary dev-agent `check-all.sh` was **started and killed mid-stage-10**, with no `EXIT=`, no `all green.` and no 16/16 tally, and that it discharges nothing. Neither presents it as a PASS. All four T8 boxes are unchecked, §19 and §20 are empty, and no Ezop, Laura or Aider sign-off is claimed anywhere. §15 also volunteers two things against its own interest — a defect in its own test code, and the fact that mutation A did **not** fail AC-6 contrary to T3.3's prediction (the cause it gives, `updated_at` having a `default_factory` but no `onupdate`, is correct: I verified it at `_entities.py:164`). The record is truthful.

### 18.7 Triage summary

**0 `decision-needed`, 0 `patch`, 5 `defer`, 0 dismissed as noise** (M-4 is recorded as by-design rather than dropped, so it stays visible). No finding was rated `high` or `medium`; all five are `low`. **No patch was offered or applied, and no product file was touched by this review.**

### 18.8 Verdict

`APPROVE`

Critical 0 and Important 0, so the verdict contract's `APPROVE` condition is met. The implementation does exactly what Story 49.2 specifies, in exactly the three predicted product files, on the verified 41.3 precedent, with a test suite whose load-bearingness I re-derived independently rather than took on trust.

### 18.9 Limitations of this review, stated plainly

- **Cross-layer independence is weaker than the workflow intends** — the three layers ran inline in one context, not as blind parallel subagents (§18.3). Compensated for with executed evidence, not eliminated.
- **No live database was opened and no production catalogue claim was re-derived.** Every execution used throwaway `tmp_path` / `/tmp` SQLite files. The §6 F-1 distribution evidence was **not** re-measured by this pass; I verified only that the dataset matches the approved content and that the story's framing of that evidence is honest.
- **This review did not run `check-all.sh`, the determinism triple, or the full `apps/api` suite to completion.** My targeted runs (§18.4-8) are real and are quoted exactly; the full 16-stage gate is controller-owned and separately evidenced, and **nothing in this section should be read as discharging it**.
- **Static review of an uncommitted working tree.** The reviewed state is the working tree at `88a683a`; any later edit invalidates this record.

### 18.10 Explicitly NOT done by this pass

Independent external **Aider** code review (`laura-aider-review-diff`) — **not run**; §19 stays empty · **NFR26-DETERMINISM-1 determinism proof** (T8.2) — **not run and not claimed** · the controller's frozen final `check-all.sh` gate (T8.1) — **controller-owned, not run here, and not claimed** · review loop-back (T8.3) and **commit / push / ff-only merge** (T8.4) — **not done** · **deploy** — not done · **any live-database access or production seeding**, including running the new seed CLI against any non-scratch database — **not done** · **controller final disposition** (§20) — **not done, and owned by the controller**.

**Status deliberately left at `review`** in this document, at `review` for the `49-2-starter-category-seed` key in `sprint-status.yaml`, and `epic-49` untouched at `in-progress`. **Disclosed deviation from step-04 §6:** the base workflow would set the story to `done` on a clean review and sync that to `sprint-status.yaml`. The controller directed that the story stay at `review` and owns the final `done`, so neither the Status line nor `sprint-status.yaml` was modified by this pass — recorded here rather than silently applied. **No Ezop signature, Ezop review, Laura sign-off or Aider verdict is recorded, implied or claimable from this section.** This is a Claude/native BMAD reviewer verdict and nothing more.

## 19. Independent external review record (Aider)

**VERDICT: `APPROVE`** — Critical 0, Important 0. Final output line was literal `APPROVE`.

**Reviewer and mode.** `laura-aider-review-diff`, Aider v0.86.2, `openrouter/deepseek/deepseek-v3.2`, read-only pasted-diff mode (`--chat-mode ask --no-git --no-auto-commits --map-tokens 0`). The input was the complete product diff only: tracked `apps/api/app/core/db/seed.py` plus full no-index patches for the two new files `apps/api/scripts/seed_browse_categories.py` and `apps/api/tests/test_seed_browse_categories.py`. The prompt carried the validated AC contract and explicitly required scrutiny for transaction/race defects, tautological or vacuous tests, manufactured RED and mutation residue. Durable output: `.hermes/run-logs/e49-2-aider-code-review-20260726.log` (local, gitignored).

**Aider's substantive conclusion.** The implementation correctly satisfies the exact-eight dataset, create-if-absent/no-clobber semantics, per-row commits, `IntegrityError` handling, no boot wiring, zero out-of-scope table writes and truthful admin CLI count. It called the test suite thorough across dataset shape, idempotency, admin edits, partial seeds, transaction boundaries and concurrency.

**Controller adjudication of non-blocking notes (no patch applied):**

1. Aider's sole Minor claimed `test_seed_browse_categories_is_referenced_only_by_its_own_definition` would fail because the admin CLI imports the symbol. **False positive:** the test intentionally scans only `(_API_ROOT / "app").rglob("*.py")`; `scripts/seed_browse_categories.py` is outside `app/` and is the one allowed deliberate invocation path. The body and adjacent comment test the runtime/boot boundary, and the test passed in focused, reviewer and full-controller gates. The name is slightly broader than the body, but renaming a green test is not a correctness fix.
2. Suggested missing test for an unrelated row sharing a `position` is **outside the contract and schema**: `BrowseCategory.position` has no unique constraint; the seed keys solely by slug by design, so such a row cannot produce a position collision in SQLite.
3. Suggested missing test for a future dataset entry with `inclusion_criterion=None` is **already caught**: the literal `_APPROVED_CRITERIA` comparison fails, and the subsequent `text[0]` / `endswith` checks cannot accept `None`. Adding a redundant bespoke test is unnecessary.

**Disposition.** Critical 0 and Important 0 satisfy the external-review gate. The two Missing-test suggestions and one Minor do not identify a real uncovered contractual failure. No product, test or workflow file was modified by Aider; this §19 is the controller-owned record of its read-only output and adjudication. Codex fallback was not used because Aider returned a complete literal verdict.

**Still not claimed by this section.** The controller determinism triple, final status/commit/push/ff-only integration/deploy/live seed and §20 disposition remain separately controller-owned. No Ezop signature or review is recorded or implied.

## 20. Controller final disposition

**Disposition: DONE — Laura/controller, 2026-07-26.** This is a controller decision under Ezop's standing Initiative 26 authorization, not an Ezop signature or a claim that Ezop personally reviewed the code.

- Real-distribution gate: **PASS** against all 131 active model names + tags; two independent read-only analyses agree all eight categories clear the ≥3 threshold. Conservative minima are 19 / 14 / 23 / 16 / 6 / 10 / 11 / 3; `replacement-parts` clears at exactly 3. No assignments were created.
- Native BMAD validation: **PASS**, followed by controller spec audit and independent pre-development Aider **APPROVE**; `G26-DEVGO` was granted by Laura/controller before development.
- Native BMAD code review: **APPROVE**, Critical 0, Important 0; five non-blocking minors are explicitly triaged in §18.
- Independent Aider diff review: **APPROVE**, Critical 0, Important 0. Its one claimed Minor was a verified false positive about the deliberate `app/**/*.py` runtime scan; its two suggested tests were redundant or outside the schema contract (§19).
- Final merge gate: `.hermes/run-logs/e49-2-controller-check-all-20260726.log` → **16/16**, terminal `all green.`, API **1780 passed / 3 skipped**, Web Vitest **785 passed**, visual **536 passed / 32 expected skips**. The tracked `seed.py` diff SHA-256 was identical before and after the gate; the final all-file manifest separately records every current story-file hash.
- Final determinism: `.hermes/run-logs/e49-2-controller-api-determinism-proof-20260726.txt` plus three per-run logs → API **3× 1780 passed / 3 skipped / 2014 warnings**, every exit 0, normalized summaries identical.
- Scope: exactly three execution-critical product files plus this story and `sprint-status.yaml`; no dependency, migration, runtime startup wiring, model assignment, live-DB, production or deployment action occurred during create/validate/development/review/gate.
- The implementation preserves admin edits, tolerates partial seeds and one losing concurrent insert race, commits each newly inserted row independently, exposes a truthful admin-only CLI count, and cannot auto-run from app startup/import paths.
- Deferred native minors remain explicitly recorded in §18 and are forward hardening/observability ideas, not acceptance failures. No deferred item blocks Story 49.2.

The story branch contains one atomic implementation commit; the final status/evidence closeout is folded into that same commit by amend. No live database was accessed during development or review. The ff-only integration, push, deployment and deliberate live admin seed are controller-owned actions executed immediately after this record is committed; their external SHAs and production evidence belong in Git/deploy/run logs rather than in this self-referential artifact.

## 21. Change Log

| Date | Pass | Change |
|---|---|---|
| 2026-07-26 | native `bmad-create-story` (CS, action=create) | Story authored at baseline `df922f9`; `Status: ready-for-validation` |
| 2026-07-26 | native `bmad-create-story` (VS, action=validate) | Fresh independent context, verdict `PASS`, 11 amendments applied; `Status: ready-for-dev`; §16 recorded |
| 2026-07-26 | Laura/controller | G26-DEVGO **granted** for this story under Ezop's standing Initiative 26 authorization (controller decision; not an Ezop signature or review) |
| 2026-07-26 | native `bmad-dev-story` (DS) | Implemented the three product files at actual baseline `88a683a`: `STARTER_BROWSE_CATEGORIES` + `seed_browse_categories` + `_insert_absent_category` in `seed.py`, the admin-run `scripts/seed_browse_categories.py`, and the 17-test `tests/test_seed_browse_categories.py`. Strict RED→GREEN (two recorded REDs, GREEN 17 passed), three labelled mutation sensitivity checks with hash-proven restoration, regression 36 passed, `ruff` clean, product scope proven to exactly three files. Front matter `baseline_commit` → `88a683a` with `df922f9` preserved as `create_validate_baseline_commit`; §2 G26-DEVGO line corrected to its granted current state; T1–T7 checked, **all T8 left unchecked**; §15 Dev Agent Record filled; `Status: review`. No code review, no Aider review, no commit/push/merge/deploy, no live seed. |
| 2026-07-26 | Laura/controller closeout | Real-distribution PASS; native validation/code review PASS/APPROVE; Aider pre-dev and code review APPROVE; controller `check-all` 16/16; API determinism 3× identical at 1780 passed / 3 skipped / 2014 warnings. T8.1–T8.3 closed, §20 disposition DONE, story/sprint status → `done`; T8.4 intentionally left open until the atomic commit exists. No live DB, push, merge, deploy or live seed in this record. |
| 2026-07-26 | Laura/controller atomic-commit closeout | Initial atomic commit created; T8.4 then truthfully closed and folded into the same commit by amend. Final SHA and ff-only integration are external Git evidence, deliberately not self-embedded. |
