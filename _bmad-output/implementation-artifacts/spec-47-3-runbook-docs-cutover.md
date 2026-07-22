---
title: 'Story 47.3 — Agent add-model runbook + docs cutover (drop category pre-flight)'
type: 'chore'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '03fd6d1b54ea6763a05fdfc1049ddbf171a98169'
---

<intent-contract>

## Intent

**Problem:** `docs/agents-add-model-runbook.md` still frames Category as a mandatory, elaborately-resolved pre-flight ceremony (a full slug→UUID `jq` lookup with ambiguity handling, one of "five" gating checklist items) even though the facet-tag rebuild (E41-E46) replaced category-based organization with tags; `apps/api/scripts/hydrate_local_tree.py` still calls the soon-to-be-retired `GET /api/categories` and builds its local directory layout from `category_id`, which is the one remaining real consumer blocking 47.4's API-surface retirement per `epic-47-context.md`; and `docs/operations.md` / `docs/design/HANDOFF-tagi-fasetowe.md` carry stale references to the already-deleted `CategoryTreeSidebar` component (flagged for 47.3 in `deferred-work.md`).

**Approach:** Simplify the runbook's category ceremony to a one-line placeholder-value fetch (verified: `Model.category_id` is still DB `NOT NULL` + Pydantic-required today — 47.4/47.5 haven't landed — so the field can't be dropped from the payload, only the multi-step *resolution ceremony* around it, since category no longer needs a specific slug once tags own classification); flatten `hydrate_local_tree.py`'s directory layout to `<model-slug>-<suffix>` so it stops consuming `GET /api/categories`/`category_id`, satisfying 47.4's hard precondition; and correct the stale `CategoryTreeSidebar` references in `docs/operations.md` and `docs/design/HANDOFF-tagi-fasetowe.md`.

## Boundaries & Constraints

**Always:** Keep `category_id` in every runbook example payload that hits a real endpoint (backend genuinely still requires it — confirmed via `apps/api/app/modules/sot/admin_schemas.py:32` `category_id: uuid.UUID` no default, and DB column `nullable=False` since migration `0004_entity_tables.py`); never produce a runbook example that would 422 if run verbatim. Preserve the runbook's H1 heading and its first non-blank line (`docs/agents-add-model-runbook.md:3`) byte-for-byte — `infra/scripts/deploy.sh`'s post-deploy fingerprint hashes only that line, and none of this story's edits target it, so `infra/.runbook-fingerprint` needs no regen.

**Block If:** none — this story is a pure ordering-safe subtraction/simplification with no destructive backend, DB, or FE change and no ambiguity left unresolved by the investigation above.

**Never:** Do not touch `apps/api/app/modules/sot/admin_schemas.py`, `admin_router.py`, `Category`/`Model.category_id` ORM, or any Alembic migration — the destructive backend/DB cutover is 47.4 (API-surface retirement) and 47.5 (ORM+migration `0019`), not this story. Do not edit `docs/architecture.md`, `docs/project-overview.md`, or `docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md` — all three are historical/still-accurate-today category mentions (category API and column are still live), matching this repo's convention of leaving dated/historical docs alone (`deferred-work.md`'s own note treats the latter as an archived proposal, not live documentation). Do not touch `AGENTS.md` — verified zero category references, nothing to cut over. Do not add a tag-based or any other replacement hierarchy to the hydrate layout — tags are multi-valued/optional with no natural single-path analogue to category, so flat is the correct target, not a speculative new grouping scheme.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hydrate layout (post-change) | Model with slug `foo`, uuid hex prefix `abc12345` | Local path is `<target>/foo-abc12345/<original_name>` (no category prefix) | N/A |
| Hydrate script run | Live portal API | Script no longer calls `GET /api/categories`; `run_hydrate` never reads `model["category_id"]` | N/A |
| Runbook worked flow | Agent follows step-by-step to create a model | `POST /api/admin/models` payload still includes a valid `category_id`, obtained out of band (operator ask / cached prior value) rather than a live `/api/categories` fetch | 4xx `detail` strings unchanged (`category not found`, `slug already exists`) |
| Pre-existing local tree (operator re-hydrates after this story deploys) | Old nested `<cat-slug>/<sub-slug>/<model-slug>-<suffix>/` tree on disk | New run downloads into new flat paths (state cache keys differ, so no false "in sync" skip); old nested tree is left in place unless `--prune-deleted` is passed | Documented in `docs/operations.md` Reverse-sync section, not a script failure |

</intent-contract>

## Code Map

- `docs/agents-add-model-runbook.md` -- primary target: § "Reusing the cookie" read example (line ~55), § "Pre-flight Checklist" item 1 + item count (lines ~280-302), § "Putting It Together — Worked Flow" steps 6-9 (lines ~387-401).
- `apps/api/scripts/hydrate_local_tree.py` -- `_build_category_path_map` (lines ~175-191) and its call site + `cat_id`/`cat_path` usage inside `run_hydrate` (lines ~303-304, ~346-360) are the real "consumer" of `GET /api/categories`/`category_id` that 47.4 is blocked on.
- `apps/api/tests/test_hydrate_local_tree.py` -- `test_hydrate_layout_uses_category_subcategory_slug` (lines ~310-330) asserts the old nested layout; `_seed_category`/`_seed_model` helpers (lines ~35-64) stay unchanged (still needed to satisfy `Model.category_id`'s `NOT NULL` FK in test fixtures — unrelated to the script's own consumption of the endpoint).
- `docs/operations.md` -- line ~450 (`CategoryTreeSidebar` in the "3B — List view rebuild" historical entry), lines ~482-491 (Reverse-sync "Layout:" description, must match the new flat layout), line ~509 ("Category picker" UI-deferral bullet).
- `docs/design/HANDOFF-tagi-fasetowe.md` -- line ~55 table row for `CategoryTreeSidebar.tsx`, stale since the component's actual deletion in story 47.1.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append a resolution note discharging the "Deferred from: story 47.1 dev review" `CategoryTreeSidebar`-stale-doc entry, and record `docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md` as confirmed out of scope (historical/archived, per that entry's own evidence note).

## Tasks & Acceptance

**Execution:**
- [x] `docs/agents-add-model-runbook.md` -- swap the § "Reusing the cookie" generic read-example endpoint from `/api/categories` to `/api/models` -- removes an unnecessary example dependency on the endpoint being retired in 47.4
- [x] `docs/agents-add-model-runbook.md` -- delete Pre-flight Checklist item 1 ("Category slug exists" + the guarded slug→UUID `jq` recipe), renumber items 2-5 to 1-4, and change "Verify all five items" to "Verify all four items" -- drops the mandatory category pre-flight ceremony per the story's requirement
- [x] `docs/agents-add-model-runbook.md` -- in § "Putting It Together — Worked Flow": change step 6 to "Walk all 4 items"; delete step 7 ("Pick category"); fold an inline note into the (renumbered) create-model step stating `category_id` remains a required legacy field until 47.4/47.5 land, its value no longer affects catalog organization (tags own that now), and the agent must obtain a valid UUID **out of band** — ask the operator once for any existing category UUID, or reuse a `$CATEGORY_ID` cached from a prior session — rather than resolving one via a live `GET /api/categories` call (this runbook must not remain a consumer of that endpoint, per `epic-47-context.md`'s 47.4 ordering precondition); renumber the remaining steps 8-11 down to 7-10 -- keeps the worked example runnable against the live API (still requires `category_id`) while dropping both the ambiguity-guarded resolution ceremony AND the runbook's own live dependency on the endpoint being retired next
- [x] `apps/api/scripts/hydrate_local_tree.py` -- delete `_build_category_path_map` and its section comment; remove the `category_paths = _build_category_path_map(...)` call and the `cat_id = model["category_id"]` / `cat_path = category_paths.get(...)` lines inside `run_hydrate`; change `model_dir_rel = f"{cat_path}/{slug}-{suffix}"` to `model_dir_rel = f"{slug}-{suffix}"` -- stops the script consuming `GET /api/categories`/`category_id`, satisfying 47.4's hard precondition
- [x] `apps/api/tests/test_hydrate_local_tree.py` -- replace `test_hydrate_layout_uses_category_subcategory_slug` with a test asserting the new flat layout (`tmp_path / f"{slug}-{suffix}" / "layout.stl"` exists, no category-slug prefix); keep using `_seed_category`/`_seed_model` unchanged for FK setup -- proves the flattening without touching the still-required DB fixture path
- [x] `docs/operations.md` -- append "(later replaced by `FacetSidebar` in the E41-E46 facet-tag catalog rebuild — see Initiative 25)" to the `CategoryTreeSidebar` mention in the "3B — List view rebuild" entry (line ~450); rewrite the Reverse-sync "Layout:" paragraph to describe the flat `<model-slug>-<8-char-uuid>/<original_name>` layout and add a short migration note (pre-47.3 nested trees are left in place after the first post-cutover re-hydrate; run with `--prune-deleted` to clean them up); drop "Category picker" from the UI-deferrals Side-sheets bullet (line ~509) -- discharges the `deferred-work.md`-flagged stale reference and keeps the reverse-sync doc accurate against the script change above
- [x] `docs/design/HANDOFF-tagi-fasetowe.md` -- annotate the `CategoryTreeSidebar.tsx` table row (line ~55) as done/deleted (replaced by `FacetSidebar`, shipped in story 47.1) -- second stale reference named by the same `deferred-work.md` entry
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append a resolution note closing the "Deferred from: story 47.1 dev review" `CategoryTreeSidebar` entry: confirm `docs/operations.md` and `docs/design/HANDOFF-tagi-fasetowe.md` updated by this story, and record `docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md` as confirmed out of scope (historical/archived proposal) -- keeps the ledger truthful, matching the precedent set by 47.1/47.2's own resolution notes

**Acceptance Criteria:**
- Given `docs/agents-add-model-runbook.md`, when read top to bottom, then no pre-flight checklist item names `GET /api/categories` as a mandatory resolution step, the checklist count reads "four", and the worked flow's create-model step still sends a valid `category_id` obtained out of band (operator ask / cached prior value), never via a live `/api/categories` fetch.
- Given `docs/agents-add-model-runbook.md`, when grepped for `/api/categories`, then zero matches remain anywhere in the file — the runbook must not remain a live consumer of that endpoint.
- Given `apps/api/scripts/hydrate_local_tree.py`, when grepped for `categor`, then zero matches remain (no `GET /api/categories` call, no `category_id` read).
- Given `apps/api/tests/test_hydrate_local_tree.py` run via `cd apps/api && python -m pytest tests/test_hydrate_local_tree.py -v`, when executed, then all tests pass, including a new/updated test asserting the flat `<slug>-<suffix>` layout.
- Given `docs/operations.md` and `docs/design/HANDOFF-tagi-fasetowe.md` (the two files this story edits), when grepped for `CategoryTreeSidebar`, then every match in those two files is annotated as replaced/deleted, not described as current or pending — no claim is made about any other file in the repo.
- Given `infra/.runbook-fingerprint`, when compared against a fresh fingerprint computed the same way `infra/scripts/deploy.sh` does (H1 line + first non-blank line after it), then it still matches — this story does not touch `docs/agents-add-model-runbook.md`'s first three lines.

## Spec Change Log

### 2026-07-22 — bad_spec repair (review pass 1)
- Trigger: Blind Hunter found Task 3's category-id placeholder fetch — `CATEGORY_ID=$(curl ... /api/categories | jq -r '.roots[0].id')` folded into the create-model worked-flow step — reintroduces a live `GET /api/categories` call in the runbook, contradicting `epic-47-context.md`'s explicit ordering constraint that "the 47.3 runbook/hydrate-script updates" must stop being consumers of that endpoint before 47.4 can retire it. Edge Case Hunter independently found the same construct has no error handling for an empty `roots` array (silently embeds `"category_id":"null"`, violating this spec's own "never 422 if run verbatim" boundary).
- Amended: Task 3 (below) now sources `CATEGORY_ID` from the operator/a cached prior value instead of a live API call — the runbook no longer issues any `/api/categories` request anywhere. Added a matching runbook-side AC (no live `/api/categories` call remains) to close the AC-asymmetry Blind Hunter also flagged. Tightened the `CategoryTreeSidebar` grep AC to name the two files this story actually edits (Blind Hunter noted it read as a repo-wide claim).
- Known-bad state avoided: a runbook that still made this story's own designated "consumer to eliminate" call, silently invalidating 47.3's discharge of 47.4's hard precondition, plus a construct that could 422 an agent's first real write with no diagnostic.
- KEEP: pre-flight-checklist item removal + renumbering (Tasks 1-2), hydrate script flattening (Task 4), rewritten flat-layout test (Task 5), `docs/operations.md` / `HANDOFF-tagi-fasetowe.md` annotations (Tasks 6-7), and the `deferred-work.md` resolution note (Task 8) — all independently confirmed correct by both reviewers; unaffected by this amendment.

## Review Triage Log

### 2026-07-22 — Review pass 1
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 3: (high 0, medium 0, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[bad_spec]` Blind Hunter found Task 3's category-id fetch reintroduces a live `GET /api/categories` call in the runbook, contradicting `epic-47-context.md`'s ordering constraint that 47.3's runbook update must stop being a consumer of that endpoint before 47.4 retires it (confirmed: grep showed it was the only remaining `/api/categories` reference in the runbook). Edge Case Hunter independently found the same construct has no error handling for an empty `roots` array (silently embeds `"category_id":"null"`, would 422). Both subsumed by the same fix — see Spec Change Log above — rather than patched separately, since the flawed construct is replaced, not hardened. Also folded in the related AC-asymmetry gap (grep AC only covered the hydrate script, not the runbook) via a new AC below.
- Deferred to `deferred-work.md` (1, not this story's problem to fix now): `[low]` no test asserts the *absence* of the `/api/categories` HTTP call from `run_hydrate` (only a positive path-shape assertion exists) — a legitimate future test-hardening idea (e.g. a client-call-spy), not blocking for a docs/hydrate chore story.
- Rejected as noise (3, with reasoning): the Design Notes' "functionally inert" category-value claim only checked the FE, not backend audit/reporting consumers — irrelevant to whether the runbook example is safe to run, since this story doesn't remove or repurpose the field; `epic-47-context.md` not being updated to record this story's resolved contradiction — this repo's own step-01 "previous story continuity" mechanism already surfaces a done spec's Design Notes to the next same-epic story's create-story session, so the concern is already structurally handled; `docs/agents-add-model-runbook.md:318`'s "category" mention among admin-write mutation groups being left unannotated — an explicit, deliberate scoping decision from this spec's own investigation (still-accurate description of today's live surface, out of the epic's named scope), not a defect.

### 2026-07-22 — Review pass 2 (post bad_spec repair)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 0, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[low]` `[patch]` Both reviewers (independently) found `docs/agents-add-model-runbook.md:9`'s Principles § Idempotence bullet still said "Pre-flight check #4 (duplicate-check)" after this story's checklist renumbering made duplicate-check item #3 — the one cross-reference the original implementation pass missed (correctly updated everywhere else). Fixed: "#4" → "#3".
  - `[low]` `[patch]` Both reviewers found `docs/operations.md`'s new "Migration note (story 47.3)" claimed `--prune-deleted` would "clean up the old nested directories," but `hydrate_local_tree.py`'s prune logic only `unlink()`s stale files (confirmed via grep: no `rmdir`/`rmtree` anywhere in the script) — empty parent directories are left behind. Fixed wording to state the flag removes files only, with a one-line manual `find -type d -empty -delete` pointer for the harmless leftover directories.
  - `[low]` `[patch]` Blind Hunter found the `CategoryTreeSidebar` historical annotation spliced into `docs/operations.md:450`'s existing parenthetical read as an awkward run-on mixing two unrelated facts. Moved the "later replaced by `FacetSidebar`" note to a trailing italicized sentence instead of nesting it inside the original "(recursive expandable tree)" parenthetical.
  - `[low]` `[patch]` Both reviewers found `_seed_category`'s `parent_id` kwarg in `test_hydrate_local_tree.py` is now dead — the only test that passed it (the old category/subcategory layout test) was replaced by this story's flat-layout test, and all 11 remaining call sites omit it. Removed the unused parameter.
- Deferred to `deferred-work.md` (1): `[low]` no test exercises the exact "old nested category tree + `--prune-deleted`" migration scenario end-to-end (only the pre-existing generic prune test and the new flat-layout test exist independently) — reasonable future test-hardening idea, not blocking since the state-cache-key-mismatch behavior is a direct, obvious consequence of the key composition, not subtle logic.
- Rejected as noise (3, with reasoning): the spec's "never produce a runbook example that would 422 if run verbatim" boundary being "unfalsifiable" because angle-bracket placeholders like `CATEGORY_ID="<uuid-from-operator-or-cached-prior-session>"` would technically fail if pasted literally — over-literal reading; the runbook already establishes the placeholder-token convention throughout (`<agent-email>`, `<uuid>`, etc.) and any reasonable reader distinguishes a placeholder from a broken real value; Blind Hunter's claim that the "step-01 previous story continuity" mechanism cited in pass 1's rejection couldn't be verified in the worktree — re-checked directly: `.claude/skills/bmad-dev-auto/step-01-clarify-and-route.md:47` states the mechanism verbatim (the reviewer's own grep used unescaped `|` in a non-`-E` invocation, which searches for a literal pipe character, not alternation — a tooling false-negative, not a real gap); `docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md`'s out-of-scope classification having no mechanical enforcement — true of every historical doc in this repo, a repo-wide convention question far outside this story's boundary, not a defect introduced by this diff.

## Design Notes

`category_id` cannot be dropped from the runbook's live examples today: `ModelCreate.category_id` (`apps/api/app/modules/sot/admin_schemas.py:32`) has no default and the `model.category_id` DB column is `nullable=False` since `0004_entity_tables.py` (unchanged through the current head `0018_facet_tags.py`) — no compatibility default or "uncategorized" fallback exists anywhere in the codebase. `epic-47-context.md`'s Requirements bullet ("drop... the requirement that model create supply a category_id") describes the post-47.4/47.5 end state; 47.3 explicitly precedes those stories in the epic's own dependency chain. This spec resolves the apparent contradiction the same way this repo's create-story sessions have repeatedly self-corrected stale/premature epic-sketch wording (see epic-43-retro-2026-07-19.md Challenge #1/#2 and the E42→E43 SCP precedent): keep the payload field, drop the ceremony around it. Since nothing in the current FE reads or renders `Model.category` post-`CategoryTreeSidebar`-deletion (confirmed: it was the only category-rendering component and is now dead code), any existing category UUID is functionally inert — no slug-matching recipe with ambiguity handling is needed. Review pass 1 (see Spec Change Log) further established that the runbook must not itself issue the `GET /api/categories` call either — `epic-47-context.md` names "the 47.3 runbook... updates" as a consumer that must be gone before 47.4, a stricter bar than "simplify the ceremony." The runbook therefore sources the placeholder UUID out of band (ask the operator once, or reuse a cached value) rather than resolving it live.

## Verification

**Commands:**
- `cd apps/api && python -m pytest tests/test_hydrate_local_tree.py -v` -- expected: all tests pass (including the rewritten flat-layout test)
- `cd apps/api && python -m pytest` -- expected: full backend suite green, no regressions from the hydrate-script edit
- `cd apps/api && ruff check --fix scripts/hydrate_local_tree.py tests/test_hydrate_local_tree.py && ruff format scripts/hydrate_local_tree.py tests/test_hydrate_local_tree.py` -- expected: clean, no findings
- `grep -in categor apps/api/scripts/hydrate_local_tree.py` -- expected: no output
- `grep -n "/api/categories" docs/agents-add-model-runbook.md` -- expected: no output (the runbook must not remain a live consumer of the endpoint)
- `awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' docs/agents-add-model-runbook.md | sha256sum` -- expected: matches the value in `infra/.runbook-fingerprint` (confirms the fingerprinted line is untouched)

**Manual checks (if no CLI):**
- Read `docs/agents-add-model-runbook.md` end to end once more after editing to confirm the worked flow still reads coherently with the renumbered steps (no dangling references to the deleted step 7 or the old "five items" checklist count anywhere else in the file, e.g. the Behavioral Notes section).

## Auto Run Result

Status: done

**Summary:** Dropped the mandatory `GET /api/categories` pre-flight ceremony from `docs/agents-add-model-runbook.md` (a full ambiguity-guarded slug→UUID resolution recipe, one of "five" gating checklist items) since the facet-tag rebuild (E41-E46) replaced category-based organization with tags; simplified the checklist to four items and the worked flow's create-model step to source a placeholder `category_id` out of band (operator ask / cached prior value) rather than resolving one live — `category_id` is still a genuinely required legacy field today (`Model.category_id` is DB `NOT NULL` and `ModelCreate.category_id` has no Pydantic default; 47.4/47.5 haven't landed), so it stays in the payload, but the runbook itself no longer calls the endpoint that 47.4 is scheduled to retire next. Flattened `apps/api/scripts/hydrate_local_tree.py`'s reverse-sync directory layout from `<category-slug>/<subcategory-slug>/<model-slug>-<suffix>` to `<model-slug>-<suffix>`, removing its `_build_category_path_map` call and all `category_id` reads — this discharges the hard precondition `epic-47-context.md` names for 47.4 (every consumer of `GET /api/categories`/`category_id` gone). Corrected two stale `CategoryTreeSidebar` references (`docs/operations.md`, `docs/design/HANDOFF-tagi-fasetowe.md`) that `deferred-work.md` had flagged as 47.3's to fix, and confirmed a third reference (`docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md`) as out of scope (dated/historical, matching this repo's convention for archived docs).

**Files changed:**
- `docs/agents-add-model-runbook.md` -- dropped the category pre-flight checklist item + its slug-resolution recipe (5→4 items); swapped a generic read-example endpoint from `/api/categories` to `/api/models`; reworked the worked-flow create-model step to source `category_id` out of band instead of via a live API call; renumbered all downstream checklist/worked-flow cross-references
- `apps/api/scripts/hydrate_local_tree.py` -- removed `_build_category_path_map` and all `category_id`/`GET /api/categories` consumption; flattened the local directory layout; renumbered the remaining section comments
- `apps/api/tests/test_hydrate_local_tree.py` -- replaced the category/subcategory layout test with a flat-layout test; removed the now-unused `parent_id` kwarg from `_seed_category`
- `docs/operations.md` -- annotated the stale `CategoryTreeSidebar` mention; rewrote the Reverse-sync layout description + added an accurate migration note about `--prune-deleted`'s actual (file-only) effect
- `docs/design/HANDOFF-tagi-fasetowe.md` -- annotated the stale `CategoryTreeSidebar.tsx` table row as done/deleted
- `_bmad-output/implementation-artifacts/deferred-work.md` -- resolved the 47.1-dev-review `CategoryTreeSidebar`-stale-doc entry; appended one new deferred item from this story's own review (missing end-to-end migration test)
- `_bmad-output/implementation-artifacts/spec-47-3-runbook-docs-cutover.md` (new) -- this spec

**Review findings breakdown:** Review pass 1 found 1 high-severity `bad_spec` (Task 3's category-id fetch reintroduced a live `GET /api/categories` call, contradicting the epic's ordering constraint that this story's runbook update must stop being a consumer of that endpoint before 47.4 — repaired by sourcing the value out of band instead) plus 3 low patches, 1 low defer, and 3 rejects held pending re-derivation. Review pass 2 (post-repair) found 4 low patches (a stale "pre-flight check #4" cross-reference, an overstated `--prune-deleted` doc claim, an awkward annotation splice, a dead test-helper kwarg — all fixed), 1 low defer (appended to `deferred-work.md`), and 3 rejects (a placeholder-wording pedantry, a mis-verified claim about the step-01 continuity mechanism — confirmed real on direct re-check, the reviewer's grep methodology was flawed — and an out-of-scope archived-doc enforcement question).

**Verification performed:** `pytest tests/test_hydrate_local_tree.py -v` (11 passed) and the full backend suite `pytest` (1761 passed, 3 skipped, 0 failed) both green after every patch round; `ruff check` + `ruff format` clean on both touched Python files; `grep -in categor apps/api/scripts/hydrate_local_tree.py` and `grep -n "/api/categories" docs/agents-add-model-runbook.md` both empty; the runbook's post-deploy fingerprint (`infra/scripts/deploy.sh`'s H1+first-line hash) re-verified against `infra/.runbook-fingerprint` after every edit round — unchanged throughout, since no edit touched the runbook's first three lines. Two independent adversarial review passes (Blind Hunter + Edge Case Hunter, run twice — before and after the bad_spec repair) with no unresolved high/medium findings remaining.

**Residual risks:** None blocking. The one deferred item (no end-to-end test for the old-nested-tree + `--prune-deleted` migration transition) is low-priority and self-evident from the state-cache-key composition, not subtle logic. `docs/agents-add-model-runbook.md:318`'s "category" mention among admin-write mutation groups and `docs/architecture.md`/`docs/project-overview.md`'s category mentions were deliberately left untouched — all remain factually accurate until 47.4/47.5 retire the underlying API/DB surface.
