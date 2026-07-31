---
baseline_commit: c3db4aaf355b6511abde3fa908be6c644bab5d99
---

# Story 54.1 — Cross-surface i18n parity audit + remediation (NFR26-I18N-1)

Status: done

<!-- 2026-07-31 — Status `in-progress` → `done` by the SECOND native `bmad-code-review` (verdict APPROVE, § 8 "Review Findings — second native code review"). `done` here means: native BMAD review closed and the story's own AC set discharged. Independent Aider review then returned APPROVE (`.hermes/run-logs/aider-review-54-1-final-20260731_072419.log`). It does NOT mean committed, merged, pushed or deployed — all four remain the controller's. NOT an Ezop signature, NOT human review, and no physical Android Chrome evidence was collected. `G26-LIB` remains OPEN. -->


<!-- Created 2026-07-31 by native `bmad-create-story` (Create action), repo-local Claude Opus 5, at `main` @ `c3db4aa`. Routing: session-start `bmad-help` → `bmad-create-story:create`. NOT an Ezop signature and NOT human review. -->
<!-- VALIDATED 2026-07-31 by native `bmad-create-story` Validate (VS), repo-local Claude Opus 5, fresh context, at `main` @ `c3db4aa` with shell access. Verdict CONDITIONAL→PASS: 4 critical gaps found and fixed in place (V-2 ordering claim, V-5/AC-7 second spec file + line refs, D-6 ownership, AC-9 painted-pixel evidence); see § 18. NOT an Ezop signature and NOT human review. -->

- **Epic:** E54 — Cross-surface i18n/a11y/visual audit + rollout and docs (Initiative 26 — Catalog Discovery). Depends on E51–E53 surfaces landed (`epics.md:4585`); they are landed.
- **Author:** Claude Opus 5, native `bmad-create-story`, repo-local. **NOT** an Ezop signature and **NOT** human review of anything.
- **Created:** 2026-07-31, at the controller-supplied baseline `c3db4aa` (see § 2 V-10 for the provenance caveat on that SHA).
- **Authorization posture:** planning artifact only. Zero product code, zero tests, zero locale content changed by the run that produced this file. `ready-for-dev` is the BMAD artifact status, **not** a green light — `G26-DEVGO` (`architecture.md:3386`) requires controller confirmation of *this specific story* before dev starts.

---

## 0. ⛔ ENTRY GATE — read before `bmad-dev-story`

> **This is an AUDIT-AND-REMEDIATE story, and the audit is the deliverable. The remediation may legitimately be very small.**

**The precedent that sets the expectation.** `epics.md:4591` names it explicitly: *"the epic:46 I18N SCOPE NOTE recorded a whole planned i18n scope that had already shipped inside earlier epics, and 47.1's real scope collapsed to two keys once traced."* Read `spec-47-1-i18n.md:18` before starting. Initiative 25's terminal i18n story went in expecting to add `facets.*`, `matchAll`, `matchAny`, `untagged`, `noTags`, `tags.groupless` and admin keys, and came out deleting two dead keys, because everything else had already shipped correctly inside the stories that owned the surfaces.

**Expect the same shape here.** The most likely honest outcome of this story is: a complete, evidence-backed audit table, a mechanical check that did not exist before, and a *handful* of copy corrections. **A large remediation diff is a signal to stop and re-read § 5, not a sign of thoroughness.**

**The three clauses are not equally open.**

| Clause of `NFR26-I18N-1` / `epics.md:4591` | State entering this story |
|---|---|
| *"full `en.json`/`pl.json` key-set parity"* | **ALREADY MECHANICALLY ENFORCED AND GREEN.** `apps/web/tests/i18n.test.ts:15-22` asserts set-equality in both directions, repo-wide, on every `npm run test`. Story 53.3 recorded 1048/1048 with an empty set-difference both ways. **Do not author a parity test — one exists.** See § 2 V-1. |
| *"no placeholder or English-identical Polish left behind"* | **UNCHECKED — and the naive check is wrong.** Legitimately identical en/pl pairs already ship (§ 2 V-4). A bare "pl must differ from en" assertion is a false-positive generator. D-2. |
| *"consistent terminology … across browse nav, scope chip, suggestions, Filters drawer, admin screens and viewer controls"* | **UNCHECKED, and not mechanisable.** This is a judgement pass with a recorded verdict per divergence. Four candidate divergences are already measured in § 2 V-6, plus the pre-routed viewer collision in § 2 V-5. |

**A finding here is a defect in the story that shipped the surface, not new end-of-initiative scope** (`prd.md:2264`, `epics.md:4591`). Record which story shipped each defect. Do not invent a surface, a key, or a feature.

**What this story does NOT do — every one of these is named elsewhere and is not 54.1's:**

- ⛔ **Not** the focus-trap defect (DN-1) — `apps/web/src/ui/dialog.tsx` is **Ask First** (`architecture.md:3375`) and the remediation is **Story 54.2**'s (`deferred-work.md`, "Deferred from: dev of 53-3", `status: OPEN`).
- ⛔ **Not** contrast, dark mode, baselines, axe, or the `toHaveScreenshot` colour-gate gap — **54.2** (`epics.md:4595`).
- ⛔ **Not** DN-4's `/share` in-viewer-navigation readiness stall, nor the mounted-and-hung `/catalog` stall — both `status: OPEN` in `deferred-work.md`, both routed to a follow-up story the controller assigns. **Not 54.1.**
- ⛔ **Does not close `G26-LIB`**, does not collect or fabricate physical Android Chrome evidence, and does not touch `epic-53`.
- ⛔ Does not sweep orphaned keys **outside** the Initiative 26 key space (§ 3). The repo-wide liveness gap is a ledgered systemic item (`deferred-work.md`, "Deferred from: story 47.1 dev review"), not this story's remit.

---

## 1. Story statement

**As** a Polish-speaking member moving across the catalog — browse rail → category scope → search suggestions → Filters drawer → model detail → fullscreen viewer — and as the admin curating categories behind it,

**I want** the same concept to be named the same way on every one of those surfaces, and every Polish string to be real Polish rather than an English string that was never translated,

**so that** `NFR26-I18N-1` (`prd.md:2264`) holds *across* Initiative 26 and not merely *within* each story that shipped a piece of it — and so the residue that per-story gates structurally cannot see is found and fixed once, by the story chartered to look for it.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped content at `c3db4aa`

Every row below was read directly this run. Line numbers are as read at this baseline. **Rows V-1, V-4, V-5 and V-8 correct assumptions a naive reading of the epic sketch would produce.**

| # | Fact | Evidence at `c3db4aa` | Consequence for 54.1 |
|---|---|---|---|
| **V-1** | 🛑 **The key-set parity gate ALREADY EXISTS and is green. Do not re-author it.** | `apps/web/tests/i18n.test.ts` — 22 lines, one `describe`, one `it` (`"en and pl have identical key sets"`), asserting `enKeys \ plKeys === []` **and** `plKeys \ enKeys === []` (`:19-20`). Runs on every `npm run test`. Story 53.3 recorded `1048/1048`, empty set-difference both ways. | The epic's first clause is discharged by a shipped test. 54.1 **extends** this file with the checks it cannot make (D-1). Authoring a second parity test would be textbook wheel-reinvention. |
| **V-2** | **Both locale files are FLAT single-level JSON, not nested. 1048 keys each. Their key ORDER is *almost* identical — one transposed pair, measured.** | Both files are 1050 lines — `{` at `:1`, first key `"app.name"` at `:2`, last key `"modules.admin.categories.errors.generic"` at `:1049`, `}` at `:1050`. `python3` over both: **1048 / 1048 keys, sets equal, no nested values in either file.** Order diverges at exactly **one** adjacent transposition: `en.json:430` = `errors.not_found` / `:431` = `errors.audit_log`, **swapped** in `pl.json`. Everywhere else the two files line up line-for-line. | `i18n.test.ts`'s `flat()` recursion has nothing to recurse into. A new check can be a plain `Object.entries(en)` walk with a direct `pl[key]` lookup — no traversal helper needed. ⚠️ **Do not assume `en.json:N` and `pl.json:N` are the same key** — they are, for every line except `:430`/`:431`. Key by NAME, never by line index. The transposition is outside the § 3 scope and is **not** this story's to fix. |
| **V-3** | **The Initiative 26 key space, enumerated and COUNTED with `python3`.** | Counted by prefix over `en.json`: `catalog.emptyCategory` + `catalog.emptyInCategory` `:274-275` (**2**); `catalog.browse.*` `:291-303` (**13**); `catalog.image_viewer.*` `:389-402` (**14**); `catalog.suggestions.*` `:406-409` (**4**); `admin.tabs.categories` `:927` (**1**); `modules.admin.categories.*` `:928-1049` (**122**) = **156**, plus the one in-scope Filters key from V-11 = **157**. | This is the audit's scope (§ 3) — **not** all 1048. `catalog.filters.matchMode` (`:280`), `matchAll` (`:281`), `matchAny` (`:282`), `ungrouped` (`:289`), `untagged` (`:290`) are **Initiative 25** (the epic:46 I18N SCOPE NOTE) and are out of scope. The three drawer keys at `:286-288` are settled in **V-11** — the ownership question is closed, not left to dev. |
| **V-11** | 🛑 **D-6 IS CLOSED. The three `catalog.filters.*` drawer keys split 1-in / 2-out, resolved with `git log -S`, not guessed.** | `git log -S … -- apps/web/src/locales/en.json` returns two commits for all three keys: **`47e8407` (2026-05-10, `feat(web): mobile filter sheet + image polish`)** and **`3202b7c` (`feat(web): consolidate catalog filters panel` — its body reads *"Story 52.1"*). `git show` on each resolves who INTRODUCED what: `47e8407` adds `+ "catalog.filters.openFilters"` and `+ "catalog.filters.title"` (2 insertions, nothing else); `3202b7c` adds `+ "catalog.filters.openFiltersWithCount"` only, and merely carries the other two as context lines. | **`openFilters` (`:286`) and `title` (`:288`) PREDATE Initiative 26 by two months → OUT of § 3 scope.** They are read as comparison anchors, never edited. **`openFiltersWithCount` (`:287`) was shipped by Story 52.1 → IN scope, owning story 52.1.** Dev re-verifies with the two commands in § 9 but does **not** re-litigate the answer. |
| **V-12** | **`catalog.image_viewer.trigger_label` is an `aria-label` at every one of its four call sites, and no spec matches on its value — so D-5's fix paints ZERO pixels.** | Repo-wide grep: `apps/web/src/modules/catalog/components/ModelGallery.tsx:130` and `:151`, `apps/web/src/routes/share/$token.tsx:308` and `:321` — all four are `aria-label={t("catalog.image_viewer.trigger_label")}`, no text node. Both viewer specs open the viewer with `page.getByTestId("gallery-fullscreen-trigger").click()` (`image-viewer-zoom.spec.ts:49`), **not** by accessible name; the only `getByRole(… name: "Powiększ")` matchers are toolbar-scoped and resolve `zoom_in`, not `trigger_label`. | This is AC-9's "prove it paints nothing before regenerating" — **already proven, here, with citations.** Changing `trigger_label`'s Polish value cannot move a pixel and cannot break a matcher. Do **not** regenerate a baseline for it. ⚠️ Note the **fourth** consumer surface: `/share/$token.tsx`. The § 1 journey does not name `/share`, but the key ships there too — a wording choice must read correctly on the public share page as well. |
| **V-13** | **`catalog.filters.tags` (`:278`) is a KNOWN, ALREADY-LEDGERED orphan — and it is OUT of scope.** | `grep -rn "catalog.filters.tags" apps/web/src` returns **zero** consumers. `deferred-work.md`, *"Deferred from: story 47.1 dev review"*, names it verbatim: *"the pre-existing `catalog.filters.tags` orphan noted but left alone"*. | Recorded here so AC-8's sweep does not "discover" it and absorb it. It is `catalog.filters.*`, outside § 3, and § 5 forbids touching it. If dev wants it gone, that is a routing decision under AC-11, **not** an edit. |
| **V-4** | 🛑 **A bare "Polish must differ from English" assertion is WRONG and will produce false positives. Legitimately identical pairs already ship.** | `catalog.image_viewer.counter` = `"{{current}} / {{total}}"` in **both** files (`:394`); `modules.admin.categories.model_count_one` = `"{{count}} model"` in **both** (`:932`); `modules.admin.tagGroups.model_count_one` = `"{{count}} model"` in **both** (`:838`); `catalog.filters.status` = `"Status"` in both (`:277`); `catalog.sort.status` likewise (`:308`). | The identical-string check needs an **explicit allowlist with a per-entry reason** (interpolation-only, correct-by-coincidence Polish inflection, loanword, symbol). D-2 and AC-3. Shipping the naive version would flag correct translations as defects and teach the next reader to ignore the gate. |
| **V-5** | 🛑 **The viewer-control Polish collision is a REAL, ALREADY-ROUTED 54.1 input — not a fresh discovery, and the fix shape is constrained.** | `pl.json:389` `catalog.image_viewer.trigger_label` = **`"Powiększ"`** and `pl.json:399` `catalog.image_viewer.zoom_in` = **`"Powiększ"`** — one Polish accessible name for two distinct controls, while `en.json:389/:399` distinguishes `"Open fullscreen"` / `"Zoom in"`. Story 53.2 recorded it as **D-8** and raised it *for Story 54.1*; `53-3-lightbox-test-contract.md` § 2 **V-17** states the Playwright specs work around it by scoping every control lookup inside `image-viewer-toolbar` and instructs: *"Do **not** rename `trigger_label` here — it is 53.2 § 5 Ask First and 54.1's finding."* 🛑 **The workaround rationale is written down in TWO spec files, not one** (verified by `grep -rn "trigger_label" apps/web/tests`): `image-viewer-zoom.spec.ts` — rationale comment `:67-73`, toolbar-scoped locators `:74-77`, plus a related matcher note `:21`; **and `image-viewer-containment.spec.ts` — rationale comment `:352-356`, locators `:357-360`.** | 54.1 is the chartered owner. **Fix the VALUE, not the key name** (D-5). Then re-check **both** rationale comments — each claims a collision that will no longer exist, and a comment that lies is a defect. The *rationale prose* is at `zoom:67-73` and `containment:352-357`; `:74-77` / `:357-360` are the locator constants and stay as they are (V-12: no matcher resolves `trigger_label`). AC-7. |
| **V-6** | **Four measured candidate terminology divergences — audit INPUT, not pre-decided verdicts.** | **(a)** EN `"Browse categories"` renders as PL `"Przeglądaj kategorie"` on the browse rail (`catalog.browse.railLabel`, `:292`) and as PL `"Kategorie przeglądania"` on the admin screen (`modules.admin.categories.title`, `:928`) — same English source string, two Polish renderings, two surfaces. **(b)** EN *"needs curation"* renders as PL `"do uzupełnienia"` in the catalog (`catalog.browse.noCategoriesAdmin`, `:303`) and as PL `"Do sprawdzenia"` in admin (`modules.admin.categories.queue.title_pending`, `:971`). **(c)** `catalog.browse.categoryWithCount` PL uses **two different sentence shapes inside its own plural family** — `:294` base `"{{name}}, modeli: {{count}}"` and `:295` `_one` `"{{name}}, model: {{count}}"` vs `:296-298` `_few/_many/_other` `"{{name}}, {{count}} modele/modeli/modelu"` — and diverges from the shape both admin counters use (`modules.admin.categories.model_count_*` `:932-935` and `modules.admin.tagGroups.model_count_*` `:838-841`, which are **byte-identical to each other**). **(d)** EN register drift between sibling admin screens: `"Couldn't load the tag groups"` (`:842`) vs `"Could not load browse categories"` (`:931`). | Each gets **one recorded verdict** — `remediate` (with the chosen wording and why) or `keep, justified` (with why). AC-6. **(a)** is arguably fine — a verb phrase as an `aria-label` vs a noun phrase as a page title — and "arguably fine, recorded" is a valid outcome. **(c)** is the strongest candidate: two counters of the same noun, one of which contradicts itself across its own plural forms. |
| **V-7** | **There is NO orphaned-key (liveness) check anywhere in the repo, and this is a known systemic gap.** | `deferred-work.md`, *"Deferred from: story 47.1 dev review (2026-07-22)"*: *"No automated check detects i18n keys with zero remaining code consumers (orphaned keys); the repo's only i18n test (`apps/web/tests/i18n.test.ts`) checks en/pl parity, not liveness … relied on manual grepping."* Entry is unresolved. | Orphan detection over the **§ 3 key space only** is in scope (AC-8) and is cheap at ~156 keys. A repo-wide orphan sweep, or a general-purpose liveness script, is **not** — it is the ledgered systemic item and would be new scope invented at the end, which `epics.md:4591` forbids. |
| **V-8** | 🛑 **No i18n-class finding is currently ledgered OPEN. 54.1's findings must come from the audit itself.** | Every `status: OPEN` entry in `deferred-work.md` from E49–E53 is a11y, visual, behavioural or backend: DN-1 focus trap (→ 54.2), DN-4 `/share` navigation stall (→ follow-up), mounted-and-hung `/catalog` stall (→ follow-up), `toHaveScreenshot` `threshold: 0.2` colour-gate blindness (→ 54.2), duplicated error copy in the a11y tree (→ 54.2), image-failure dead end (→ open), `error → error` silent announcement (→ open), diagonal double-tap slop gap (→ open), `sources`-swap probe gap (→ open). **Not one is i18n.** | Do **not** open the ledger looking for this story's task list — there is nothing there. The task list is § 3 plus § 2 V-4/V-5/V-6. Conversely, do not *absorb* any of the above: each is someone else's and § 5 forbids touching them. |
| **V-9** | **The NFR ownership matrix names who shipped what — attribution is required, not optional.** | `epics.md:4417`: `NFR26-I18N-1` owned per story by **50.3, 51.1–51.4, 52.1–52.3, 53.2**, final audit **54.1**; *"54.1 proves cross-surface parity and remediates residue; it is not where a story's keys first appear."* Story 53.3 additionally added exactly one key (`catalog.image_viewer.error`, `:397`), transcribed verbatim from the UX spine's mockup state E rather than translated. | Every defect row in the audit table carries the **owning story**, per `prd.md:2264` (*"a defect in the story that shipped the surface"*). AC-1. |
| **V-10** | ✅ **Baseline-SHA provenance caveat — RAISED at create, CLOSED by Validate.** | At create time `baseline_commit: c3db4aa…` was controller-supplied and un-re-derived, because every `Bash` invocation in the authoring session was refused by the permission layer. **The Validate pass had shell access and re-derived it:** `git rev-parse HEAD` → `c3db4aaf355b6511abde3fa908be6c644bab5d99` (exact match), `git status --short --branch` → `main...origin/main`, only `sprint-status.yaml` modified, this story untracked, **zero** product/test/locale/snapshot diff. Every file-and-line citation in § 2 and § 3 was additionally re-read and re-measured with `sed`/`grep`/`python3` at that same SHA. | The frontmatter is trustworthy. Dev still re-runs `git rev-parse HEAD` and `git status` before branching — line numbers cited here are stable only against this exact tree — but treats a mismatch as *the tree moved*, not as an unverified claim. |

---

## 3. Scope — the Initiative 26 key space

**In scope (audit every key; **157** at this baseline, counted with `python3`, not estimated):**

| Key family | `en.json` lines | Surface | Shipped by |
|---|---|---|---|
| `catalog.emptyCategory`, `catalog.emptyInCategory` | `:274-275` | Category-scoped catalog empty states | E51 |
| `catalog.browse.*` (13) | `:291-303` | Browse rail, scope chip, "Search entire catalog", model-detail categories | 51.1–51.4 |
| `catalog.suggestions.*` (4) | `:406-409` | Inline search suggestions | 50.3 |
| `catalog.image_viewer.*` (14) | `:389-402` | Lightbox controls, counter, states | 53.2, 53.3 |
| `admin.tabs.categories` | `:927` | Admin nav | 52.2 |
| `modules.admin.categories.*` (122) | `:928-1049` | Admin category CRUD, curation queue, curation QA, model-category editor | 52.2, 52.3 |
| `catalog.filters.openFiltersWithCount` (1) | `:287` | Filters drawer trigger, count variant | **52.1** (`3202b7c`, § 2 V-11) |

**Total in scope: 2 + 13 + 4 + 14 + 1 + 122 + 1 = 157.**

**Explicitly out of scope:** every other key in the two files, specifically —

- `catalog.filters.openFilters` (`:286`) and `catalog.filters.title` (`:288`) — introduced 2026-05-10 by `47e8407`, two months before Initiative 26 (§ 2 V-11). Comparison anchors only.
- `catalog.filters.matchMode` (`:280`), `matchAll` (`:281`), `matchAny` (`:282`), `ungrouped` (`:289`), `untagged` (`:290`), and `modules.admin.tagGroups.*` — Initiative 25, already audited by 47.1 and by the epic:46 I18N SCOPE NOTE.
- `catalog.filters.tags` (`:278`) — a known, already-ledgered orphan (§ 2 V-13). Not swept, not deleted.
- The `errors.not_found` / `errors.audit_log` line transposition at `:430`/`:431` (§ 2 V-2). Both keys exist in both files; parity is intact; this is cosmetic file ordering and not 54.1's.

Every out-of-scope key named above appears in § 2 V-4/V-6/V-11/V-13 **only as a comparison anchor** — read, never edited.

---

## 4. Acceptance Criteria

1. **AC-1 — the audit record is the deliverable.** § 12 of this file carries a completed audit table covering every key in the § 3 scope (one row per key, or per plural family where the family shares one verdict), with columns: *key · surface · en value · pl value · verdict (`ok` / `identical-justified` / `defect`) · owning story*. No row is blank. No row's verdict is inferred from a sibling row. The final key count in scope is recorded as a number, re-measured, not copied from § 2 V-3.
2. **AC-2 — key-set parity is preserved, not re-implemented.** `apps/web/tests/i18n.test.ts`'s existing `"en and pl have identical key sets"` assertion still passes and its substance is unmodified. The en and pl key counts are recorded before and after and are equal in both directions at both points. Any key deleted as an orphan is deleted from **both** files in the same edit.
3. **AC-3 — English-identical Polish is mechanically detected, with a justified allowlist.** A new automated check fails when an in-scope key's `pl` value is byte-identical to its `en` value **and** the key is not in an explicit allowlist. Every allowlist entry carries a one-line reason in the source. The allowlist is seeded from the pairs named in § 2 V-4 and extended only by pairs this story's audit judges legitimately identical.
4. **AC-4 — no placeholder Polish.** No in-scope `pl` value is empty, is `TODO`/`TBD`/`FIXME`/`XXX` (any case), or is interpolation-and-punctuation-only where its `en` counterpart carries prose.
5. **AC-5 — interpolation parity.** For every in-scope key, the multiset of `{{…}}` placeholder names in `pl` equals the multiset in `en`. Mechanically checked, in the same place as AC-3.
6. **AC-6 — every terminology divergence is ruled.** Each of § 2 V-6 (a), (b), (c), (d) — and anything else the audit surfaces — carries exactly one recorded verdict: `remediate` (with the chosen wording and the rationale for choosing it) or `keep, justified` (with the rationale). **No item is left unruled**, and "keep, justified" is a legitimate outcome that must not be avoided by making a cosmetic change instead.
7. **AC-7 — the viewer-control collision is closed and BOTH workaround comments are made truthful.** `catalog.image_viewer.trigger_label` and `catalog.image_viewer.zoom_in` no longer carry the same Polish value. The change is to a **value**, not a key name (D-5). Two spec files write down the collision as their scoping rationale and **both** must be corrected against the new state or explicitly confirmed as still load-bearing for another reason — neither may be left asserting a collision that no longer exists:
   - `apps/web/tests/visual/image-viewer-zoom.spec.ts:67-73` (and the related matcher note at `:21`);
   - `apps/web/tests/visual/image-viewer-containment.spec.ts:352-356`.

   ⚠️ **`image-viewer-containment.spec.ts` is a STANDING suite** (`architecture.md:3376`) and `image-viewer-zoom.spec.ts:16-18` says 53.3 did not touch it. That instruction was 53.3's, not a permanent freeze: 54.1 is chartered to correct the comment it authored. **Comment prose only** — zero change to any locator, helper, assertion or `toHaveScreenshot` call in either file, and the suite must stay green unmodified in substance. If dev judges a substantive change is needed in either spec, that is the § 5 **Ask First** trigger.
8. **AC-8 — bounded orphan sweep.** Every in-scope key has at least one live consumer under `apps/web/src`, verified by grep and recorded. Any orphan is either deleted from both locale files or kept with a written justification. **Keys outside § 3 are not swept and not deleted.**
9. **AC-9 — no behaviour, no colour, no blanket baseline churn.** The diff is confined to the § 7 file set. No component logic, no `--color-*` token, no a11y attribute, no dialog wiring, and no `_test.ts`/config change. A visual baseline changes **only** where a changed rendered string demonstrably alters painted pixels — verified per PNG, never blanket-regenerated — and each changed PNG carries a `baseline-reviewed: <basename>, <the agent or human that actually inspected it>, YYYY-MM-DD` line on the commit. **An `aria-label`-only change paints nothing; prove that before regenerating anything.**
10. **AC-10 — gates.** `infra/scripts/check-all.sh` runs standalone and reports `all green.` with exit 0 and 16/16 stages, log captured under `.hermes/run-logs/`. `NFR26-DETERMINISM-1`: 3× consecutive identical vitest and pytest counts.
11. **AC-11 — honest routing of anything that does not fit.** Any finding this story surfaces but § 5 forbids fixing is appended to `deferred-work.md` with `status: OPEN`, a named owner, and its evidence. It is **not** silently absorbed into this story, and **not** recorded as closed. Conversely, nothing already ledgered against 54.2 or a follow-up is fixed here.

---

## 5. Boundaries & Constraints

**Always:**
- Read `spec-47-1-i18n.md` first (§ 0). Expect a small remediation.
- Edit `en.json` and `pl.json` as a pair — a key added, removed or re-keyed in one is the same operation in the other, in the same edit.
- Attribute every defect to the story that shipped the surface (`prd.md:2264`).
- Keep committed content English (AGENTS.md § Conventions) — including this file, the check's comments, and any allowlist reason. The *values* in `pl.json` are the sole Polish content.
- Visual tests render `pl-PL` (`playwright.config.ts:9`; project memory). Any Playwright matcher touching a changed string must use the literal new Polish string.

**Never:**
- ⛔ `apps/web/src/ui/dialog.tsx` — **Ask First** per `architecture.md:3375`, and the focus-trap remediation is **54.2**'s (`deferred-work.md`, DN-1, `status: OPEN`). Zero diff.
- ⛔ Contrast, `--color-*` tokens, dark-mode treatment, axe page-sets, `toHaveScreenshot` thresholds, or the `/api/*` route-mock consolidation — all **54.2** (`epics.md:4595`).
- ⛔ The DN-4 `/share` in-viewer-navigation readiness stall and the mounted-and-hung `/catalog` stall — both `status: OPEN` in `deferred-work.md`, both awaiting a controller-assigned follow-up. Not 54.1's, in either direction.
- ⛔ Do not close `G26-LIB`; do not collect, simulate or infer physical Android Chrome evidence; do not touch `epic-53` or any 53.x record.
- ⛔ Do not add a new user-visible surface, a new feature, or a key that no shipped component consumes.
- ⛔ Do not sweep, rename or delete keys outside the § 3 scope.
- ⛔ Do not blanket-regenerate visual baselines (`--update-snapshots` without a `-g` scope and per-PNG inspection). Project memory: classify each failure `stale-baseline` / `deterministic-fail` / `flake-candidate` before regenerating.

**Ask First (halt and escalate to the controller):**
- Renaming any i18n **key** rather than changing its value — key renames ripple into components, vitest and Playwright specs, and turn a copy fix into a refactor.
- Any change that alters a **painted** string on a surface that already has a baseline.
- Any finding that appears to require a component behaviour change to fix properly.

**Block If:** the audit finds an in-scope key present in one locale file and absent from the other. That would mean `apps/web/tests/i18n.test.ts` is green while parity is broken — a gate failure, not a copy defect. HALT and report; do not paper over it by adding the missing key.

---

## 6. Decisions

- **D-1 — Extend `apps/web/tests/i18n.test.ts`; do not create a parallel i18n test file.** The parity assertion lives there and is green (§ 2 V-1). AC-3/AC-4/AC-5 are new `it` blocks in the same `describe` (or a sibling `describe` in the same file), reading the same two imports. Rationale: one file is where a future reader will look, and a second file guarantees the two drift.
- **D-2 — The identical-string check ships with an explicit, reasoned allowlist, and is scoped to Initiative 26 keys only.** Two reasons, both load-bearing. (a) Legitimately identical pairs already ship (§ 2 V-4), so an unallowlisted check is a false-positive generator that will be disabled by the next person who hits it. (b) Scoping to § 3 keeps the check honest about what this story audited — extending it repo-wide would silently assert an audit of 1048 keys that nobody performed. The scope is expressed as an explicit key-prefix list in the test source, with a comment pointing at § 3.
- **D-3 — Terminology consistency is a recorded judgement, not an assertion.** No mechanical check can decide whether "Przeglądaj kategorie" and "Kategorie przeglądania" are the same concept. The deliverable is § 12's verdict column plus the § 13 terminology ruling, and `keep, justified` is a first-class outcome.
- **D-4 — Remediation is copy-only.** A finding is fixed here if and only if the fix is a locale value (or a locale key deletion, plus the mechanical consequences in tests/specs). Anything needing a component change, an a11y attribute, a token, or a baseline redesign is ledgered under AC-11 and routed. This is what keeps 54.1 from absorbing 54.2.
- **D-5 — Fix the collision by changing `catalog.image_viewer.trigger_label`'s Polish VALUE, not its key.** The key is consumed by the component and referenced by the Playwright scoping idiom (`image-viewer-zoom.spec.ts:74-77`); a rename is a refactor across three files for zero user-visible gain, and 53.3 § 2 V-17 explicitly parked the rename. Changing the value is the minimum honest fix. **Which value is the audit's call** — but it must distinguish "open the fullscreen viewer" from "zoom in one step" to a screen-reader user hearing only the accessible name (`NFR26-A11Y-1`, `prd.md:2265`: *"distinguishable by accessible name, not by appearance alone"*).
- **D-6 — RESOLVED. Ownership of the three `catalog.filters.*` drawer keys was settled with `git log -S` + `git show`, not assumed.** `openFilters` and `title` were introduced by `47e8407` (2026-05-10) and **leave** the scope; `openFiltersWithCount` was introduced by `3202b7c` (Story 52.1) and **stays**, attributed to 52.1. Full evidence in § 2 V-11; the § 3 table reflects the split. Dev re-runs the two § 9 commands as a baseline check and records the result — but does **not** re-open the question.

---

## 7. Predicted file set

One branch, `docs/`-or-`fix/`-prefixed per AGENTS.md § Branching, one commit. Dev **must** re-verify this set rather than trust it.

| File | Change |
|---|---|
| `apps/web/src/locales/pl.json` | Value corrections only (expected: few). Key deletions only if AC-8 finds an orphan. |
| `apps/web/src/locales/en.json` | Same, mirrored. Possibly untouched if every defect is Polish-side. |
| `apps/web/tests/i18n.test.ts` | **Extend** with AC-3 / AC-4 / AC-5 checks + the D-2 allowlist. Existing test body unchanged. |
| `apps/web/tests/visual/image-viewer-zoom.spec.ts` | AC-7 — **comment prose only**, at `:67-73` (and `:21` if it goes stale). No locator, helper or assertion change: V-12 proves no matcher resolves `trigger_label`. |
| `apps/web/tests/visual/image-viewer-containment.spec.ts` | AC-7 — **comment prose only**, at `:352-356`. Standing suite (`architecture.md:3376`); substance stays byte-identical and green. |
| `_bmad-output/implementation-artifacts/54-1-i18n-parity-audit.md` | This file — § 12 audit table, § 13 rulings, § 14 Dev Agent Record. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Status transitions + annotation. |
| `_bmad-output/implementation-artifacts/deferred-work.md` | Only if AC-11 routes something out. |

**Asserted unchanged (verify zero-diff before commit):** `apps/web/src/ui/dialog.tsx`, `apps/web/src/styles/theme.css`, every file under `apps/web/src/modules/` (incl. `catalog/components/ModelGallery.tsx`), `apps/web/src/routes/share/$token.tsx`, `apps/web/tests/visual/playwright.config.ts`, `apps/web/tests/visual/api-stubs.ts`, `apps/web/tests/visual/_test.ts`, every **executable** line of the two viewer specs, every `__snapshots__/**/*.png` (unless AC-9's painted-pixel test is met and each PNG is individually signed off), every file under `apps/api/` and `workers/`, and every file under `_bmad-output/planning-artifacts/`.

---

## 8. Tasks / Subtasks

- [x] **T1 — Re-establish the baseline (AC-1, § 2 V-10).**
  - [x] `git rev-parse HEAD` and `git status` — confirm `c3db4aa`, clean, `main` == `origin/main`. Report any mismatch instead of proceeding. → `c3db4aa…`, matches frontmatter. **Deviation from the literal wording, disclosed:** the branch `feat/E54.1-i18n-parity-audit` already existed and was checked out (controller-created), so the check ran as `HEAD == c3db4aa` on that branch rather than on `main`; tree otherwise as the Validate pass left it (only `sprint-status.yaml` modified, this story untracked, zero product/test/locale/snapshot diff).
  - [x] Re-measure the en/pl key counts and record both numbers. → **1048 / 1048**, sets equal, both files flat.
  - [x] `cd apps/web && npx vitest run tests/i18n.test.ts` — record the pre-change green. → `PASS (1) FAIL (0)`.
- [x] **T2 — Confirm scope ownership (AC-1, D-6 — already RESOLVED, this is a re-verification, not a decision).**
  - [x] Re-run the two § 9 ownership commands; confirm `47e8407` introduced `openFilters` + `title` (out of scope) and `3202b7c`/52.1 introduced `openFiltersWithCount` (in scope). Record the commits. A mismatch is a real discrepancy — report it, do not silently re-scope. → **Confirmed exactly**; not re-litigated. (Note: `git log` needed `--no-pager` in this environment; the pagerless form is in § 9's spirit.)
  - [x] Re-enumerate the § 3 key space against the current files; confirm the exact count is **157** and record it. → **157**, and now pinned by an assertion in `tests/i18n.test.ts`.
- [x] **T3 — Author the mechanical checks (AC-3, AC-4, AC-5, D-1, D-2).**
  - [x] Extend `apps/web/tests/i18n.test.ts`: in-scope prefix list, allowlist with per-entry reasons, identical-value check, placeholder check, interpolation-multiset check.
  - [x] **Observe RED first** — each new check must fail against at least one real pre-fix condition, or be demonstrated non-vacuous by a deliberate temporary mutation. A check that is green on first run against unfixed content is proving nothing; record which. → **2 of 5 went RED on real unfixed content** (identical-value; viewer accessible-name, on the D-8 defect). The other 3 were green on first run and were each proved by a deliberate temporary mutation, reverted — see § 14 Debug Log #6 and #8 and Completion Note 3.
- [x] **T4 — Run the audit (AC-1, AC-6, AC-8).**
  - [x] Fill § 12's table row by row, reading both values for every in-scope key. → 127 rows / 157 keys; 122 `ok`, 2 `identical-justified`, 3 `defect`.
  - [x] For each key, grep `apps/web/src` for a live consumer; record it (AC-8). → **157 live, 0 orphans**, with `*.test.*` excluded as non-consumers.
  - [x] Collect every terminology divergence, including § 2 V-6 (a)-(d). → all four plus V-5's collision; no sixth surfaced.
- [x] **T5 — Rule the terminology findings (AC-6, D-3).**
  - [x] One verdict per divergence into § 13, with rationale. `keep, justified` where that is the honest answer. → 2 × `remediate` (c, e), 3 × `keep, justified` (a, b, d).
- [x] **T6 — Remediate, copy-only (AC-7, AC-9, D-4, D-5).**
  - [x] Apply the ruled value changes to `pl.json` / `en.json`. → 3 lines in `pl.json`; `en.json` unchanged.
  - [x] Close the `trigger_label` / `zoom_in` collision by value (AC-7). → `trigger_label` → `"Otwórz na pełnym ekranie"`; key not renamed.
  - [x] For every changed string, determine whether it is painted. If it is, run the affected visual spec `-g`-scoped, inspect each PNG individually, and prepare a `baseline-reviewed:` line per changed PNG. If it is not painted, record that finding — do not regenerate. For `trigger_label` specifically this is already settled by § 2 V-12 (`aria-label` at all four call sites): **no baseline may be regenerated for it.** → **Neither changed string is painted** — both are `aria-label`-only (`categoryWithCount` likewise, `BrowseCategoryList.tsx:123`). Proved beyond the grep: 172 visual assertions across 9 specs green, **zero** snapshot churn. Nothing regenerated; **no `baseline-reviewed:` line is owed.**
  - [x] Correct **both** rationale comments — `image-viewer-zoom.spec.ts:67-73` (+ `:21`) and `image-viewer-containment.spec.ts:352-356`. Comment prose only; `git diff` must show zero executable-line change in either file. → both corrected; § 9 prose-only proof **empty**; `:21` checked and **not stale** (its three matchers all resolve unchanged `zoom_*` keys).
- [x] **T7 — Route what does not fit (AC-11).**
  - [x] Append any unfixable finding to `deferred-work.md` with `status: OPEN`, owner and evidence. Add nothing else to that file. → 2 entries under "Deferred from: story 54.1 dev (2026-07-31)".
- [x] **T8 — Gates (AC-2, AC-10).** *(completed by dev pass + controller-owned closeout gates)*
  - [x] `cd apps/web && npm run typecheck && npm run lint && npx vitest run`. → `tsc -b` clean; `ESLint: No issues found`; **154 files / 1135 tests passed, 0 failed**.
  - [x] `infra/scripts/check-all.sh` standalone, `tee` into `.hermes/run-logs/`; require `all green.` / exit 0 / 16/16. → **DONE by Laura/controller after dev/review P-4 fix**: `.hermes/run-logs/check-all-54-1-20260731_045810.log`, exit 0, **16/16**, `all green.`
  - [x] Determinism triple: 3× identical vitest and pytest counts, logged. → **vitest DONE**: 3× `154 passed (154)` / `1135 passed (1135)`, log `.hermes/run-logs/vitest-determinism-54-1-counts-20260731_042606.log`. **apps/api pytest DONE**: check-all plus two extra controller runs all reported **1961 passed, 3 skipped**; extra-run log `.hermes/run-logs/pytest-determinism-54-1-20260731_051124.log`.
  - [x] Re-record the en/pl key counts; assert equal to T1's unless an orphan was deleted from both. → **1048 / 1048**, sets equal, both diffs empty. No orphan deleted (none found).
- [ ] **T9 — Close out (controller-owned; do not self-check).** *(deliberately left unchecked — the task says so)*
  - [x] Native `bmad-code-review` — **DONE, twice.** First pass → `REQUEST_CHANGES` (5 patch, all applied; P-5 by Laura/controller). Second pass 2026-07-31 → **APPROVE** (0 decision-needed, 6 patch all applied in-pass, 7 defer, 8 dismissed; no product-code, behaviour or baseline finding). Independent Aider review via `laura-aider-review-diff` — **DONE**, final pass APPROVE at `.hermes/run-logs/aider-review-54-1-final-20260731_072419.log`; earlier two REQUEST_CHANGES verdicts were superseded by this final review and controller arbitration. Codex was not used; Gemini is not a default reviewer.
  - [ ] Commit / ff-merge / push / deploy are the controller's, not this story's.

### Review Findings

Written 2026-07-31 by native `bmad-code-review` (`review_mode=full`) on the dirty working tree at
`feat/E54.1-i18n-parity-audit`, baseline `c3db4aa`. All three adversarial layers returned; no layer failed.
Triage: **0 decision-needed, 5 patch (4 applied in-pass, 1 left as an action item), 3 defer, 11 dismissed.**
Verdict **REQUEST_CHANGES** — no product-code finding, no behaviour finding, no baseline finding; every open
item is record/comment accuracy or an AC-11 routing gap. **NOT** an Ezop signature and **NOT** human review.

Reviewer-verified independently (not taken from the record): `vitest` 1135 passed / 0 failed; `tsc -b` clean;
`ESLint: No issues found`; `en.json` byte-unchanged; zero `__snapshots__/**/*.png` touched; § 9's prose-only
proof on both viewer specs **empty**; 1048/1048 keys with equal sets; § 3 scope re-derived at **exactly 157**;
in-scope en==pl pairs are exactly the three `IDENTICAL_BY_DESIGN` entries (no stale, no missing); zero
interpolation-multiset divergence. **§ 5 Ask First did NOT fire** — no key renamed, no component behaviour
changed, and both changed strings are `aria-label`-only (`ModelGallery.tsx:130,151`,
`routes/share/$token.tsx:308,321`, `BrowseCategoryList.tsx:123` with visible label+count in separate `<span>`s
at `:133-147`). No 54.2 absorption, no out-of-§3 key edited, no baseline churn.

- [x] [Review][Patch] `sprint-status.yaml` story line contradicted its own value — value was flipped to `review` while the inline annotation still read `Status UNCHANGED (ready-for-dev)` and described only the create/validate pass [`_bmad-output/implementation-artifacts/sprint-status.yaml:407`] — **APPLIED in-pass**
- [x] [Review][Patch] `deferred-work.md` entry 1 sent a future fixer to a file with no literal assertion — `apps/web/src/modules/admin/tag-groups-i18n.test.ts` carries only key-set/parity/allowlist blocks; the literal that would actually break is `apps/web/src/modules/admin/TagGroupsPage.test.tsx:259` and `:274` [`deferred-work.md`, "Deferred from: story 54.1 dev"] — **APPLIED in-pass**
- [x] [Review][Patch] `deferred-work.md` entry 1's premise was backwards — across the seven `*.error_title` keys the contracted form is the 5:2 **majority** (`share.view`, `admin.profiles`, `profileLibrary`, `profileOffers`, `queues`, `tagGroups` vs the in-scope `modules.admin.categories`), so `tagGroups` is not "the divergent half" and the suggested one-word fix would push the repo away from its own dominant `error_title` register. § 13 ruling (d)'s `keep, justified` verdict is unaffected — nothing in scope needed changing either way [`deferred-work.md`] — **APPLIED in-pass**
- [x] [Review][Patch] `deferred-work.md` entry 2's stated deferral reason was contradicted by this same diff — it says consolidating "means editing story-level test files 54.1 has no mandate over", and this change edits one (`browse-i18n.test.ts`) [`deferred-work.md`] — **APPLIED in-pass**
- [x] [Review][Patch] Both rewritten spec rationales stated a future-conditional that was already true today — "would silently widen the moment any other surface ever ships a control with the same accessible name", while `viewer3d.tooltip.expand` = `"Powiększ"` already ships as visible `<Button>` text on the same model-detail route. AC-7 required these comments be *made truthful*; the fix was one clause in each, comment prose only, zero executable change [`apps/web/tests/visual/image-viewer-zoom.spec.ts:75-77`, `apps/web/tests/visual/image-viewer-containment.spec.ts:358-360`] — **APPLIED after review by Laura/controller** because the repo-local Claude path hit a hard subscription-window guard before it could run the bounded fix prompt. This is explicitly controller-authored comment hygiene, not BMAD-authored implementation.
- [x] [Review][Defer] `catalog.image_viewer.trigger_label` is the accessible name of TWO sibling buttons rendered simultaneously, so the fix renamed a duplicate rather than removing it [`apps/web/src/modules/catalog/components/ModelGallery.tsx:130` and `:151`; `apps/web/src/routes/share/$token.tsx:308` and `:321`] — deferred, pre-existing (Story 22.3) and needs a component change (D-4 / § 5 Ask First), so unfixable here; AC-11 required routing it and did not
- [x] [Review][Defer] `viewer3d.tooltip.expand` = `"Powiększ"` collides with the surviving `catalog.image_viewer.zoom_in` = `"Powiększ"` — one Polish word for two English concepts ("Expand" / "Zoom in") on one journey [`apps/web/src/locales/pl.json:459` vs `:399`; rendered at `apps/web/src/modules/catalog/components/viewer3d/Viewer3DInline.tsx:243-245`] — deferred, pre-existing and outside the § 3 key space, so correctly unfixable here; routing was still owed under AC-11
- [x] [Review][Defer] After this diff no test can catch `catalog.browse.categoryWithCount_one` reverting to literal English, and no fixture renders it [`apps/web/tests/i18n.test.ts:96`, `apps/web/src/modules/catalog/browse-i18n.test.ts:44`, `apps/web/tests/visual/api-stubs.ts:186,197,208`] — deferred, an accepted consequence of the ruling (c) allowlist

**Acknowledgement, not a finding — AC-9's file-set clause.** `apps/web/src/modules/catalog/browse-i18n.test.ts` is edited while § 7 lists *"every file under `apps/web/src/modules/`"* as asserted-unchanged and AC-9 says the diff is confined to the § 7 set. The review rules it a **justified mechanical consequence**: ruling (c) makes `pl.…categoryWithCount_one` byte-identical to `en`, which turns Story 51.1's unallowlisted `not.toBe` at `:48` red; D-4 explicitly permits "the mechanical consequences in tests/specs"; the shape mirrors `categories-i18n.test.ts:50` verbatim; exactly one key is exempted, by name, with the reason in the source; and § 14 Completion Note 8 disclosed it before review. **Laura/controller explicitly acknowledged and accepted this narrow deviation on 2026-07-31**; it does not authorize any broader `apps/web/src/modules/` edits.

### Review Findings — second native code review (re-review after the P-4/P-5 fix)

Written 2026-07-31 by native `bmad-code-review` (`review_mode=full`) on the dirty working tree at
`feat/E54.1-i18n-parity-audit`, baseline `c3db4aa`, routed from a session-start `bmad-help` call
(`_bmad/_config/bmad-help.csv:29` — CR, `preceded-by: bmad-dev-story`). All three adversarial layers
returned; **no layer failed**; no skill protested. Triage: **0 decision-needed, 6 patch (ALL APPLIED
in-pass), 7 defer, 8 dismissed.** Verdict **APPROVE**. **NOT** an Ezop signature and **NOT** human review.

**No product-code, behaviour, locale-content or baseline finding.** Every patch was record or ledger
accuracy. Zero executable lines changed in this pass — `apps/web/tests/i18n.test.ts` is byte-identical
(sha256 `90f67a42…` before and after the T3 probe below), so the AC-10 gate evidence still covers the
exact tree.

**All five first-review findings verified genuinely closed** (re-derived, not taken from the record):
P-1 `sprint-status.yaml:407` carries `in-progress` with an annotation that matches the value; P-2 the
ledger pointer names `TagGroupsPage.test.tsx:259`/`:274` and both lines do carry the literal; P-3 the
5:2 `*.error_title` majority is mechanically correct; P-4 the "no mandate" clause is replaced by the
scale rationale and names the edited file; **P-5 (the controller-authored comment fix) is present in
both specs and is comment-prose only** — `git diff -U0 … | grep -vE '^[+-]\s*//'` prints **nothing**
for either viewer spec, so **zero executable viewer-spec lines changed**.

Reviewer-verified independently this run: 1048/1048 keys with equal sets; § 3 re-derives to exactly
157; in-scope en==pl pairs are exactly the three `IDENTICAL_BY_DESIGN` entries; zero interpolation
divergence; `en.json` byte-unchanged; zero `__snapshots__/**/*.png` touched; AC-8's 99 direct / 48
plural-base / 10 template-literal / **0 orphans** split reproduces exactly; `npx vitest run
tests/i18n.test.ts` → **7 passed** (1 shipped parity + 6 new).

- [x] [Review][Patch] § 12 row named `modules.admin.categories.editor.last_write` — a key that exists in **neither** locale file. Its `en`/`pl` values and cited consumer are `last_write_other`'s (`en.json:1037`, `ModelCategoriesDialog.tsx:116`), so the audit did cover the key; only the row's name cell was wrong, which made the table read as 156/157 against AC-1 [`54-1-i18n-parity-audit.md:475`] — **APPLIED in-pass**
- [x] [Review][Patch] § 14 File List claimed `sprint-status.yaml` → `review` and *"Nothing else in the ledger touched"* — both were the DEV pass's snapshot, left un-restated after the first review edited the same two files (tree carried `in-progress` plus a three-entry review section) [`:567`, `:569`] — **APPLIED in-pass**
- [x] [Review][Patch] § 14 said *"five new `it` blocks"* and then listed **six**; § 8 T3's non-vacuity accounting likewise covered five of the six. **The sixth check was proved non-vacuous by this review, by the deliberate temporary mutation T3 prescribes**: adding `catalog.browse.allCatalog` (pl `"Cały katalog"` ≠ en `"All catalog"`) to `IDENTICAL_BY_DESIGN` turned `keeps the identical-by-design allowlist honest` **RED** — *"catalog.browse.allCatalog is allowlisted but no longer identical"* at `i18n.test.ts:122` — and the probe was reverted, sha256-verified identical, suite green 7/7 [`:563`, `apps/web/tests/i18n.test.ts:116-124`] — **APPLIED in-pass**
- [x] [Review][Patch] § 13 ruling (a) cited `browse-i18n.test.ts:51-55` for the vocabulary guard; this story's own +8-line `COINCIDENTAL_MATCHES` edit to that file shifted it to `:55-63`. Recorded in the same edit: ruling (a)'s grammatical-role premise is weaker than it reads, because `railLabel` is also a visible `<SheetTitle>` (`BrowseSheet.tsx:62`). **Verdict `keep, justified` is unaffected** — it changes nothing in the tree either way [`:496`] — **APPLIED in-pass**
- [x] [Review][Patch] Two `BrowseCategoryList.tsx` span citations were off by one to three lines (`:134-145` and `:134-147`); the actual spans are label `:133-144` + count `:145-147` [`:238`, `:547`] — **APPLIED in-pass**
- [x] [Review][Patch] The first review's own ledger entry sent a future fixer to `image-viewer-containment.spec.ts:362` as a `"Powiększ"` matcher; the P-5 comment rewrite shifted it to `:363` (`:362` is the `toolbar` helper). The `zoom` citation `:78` was correct [`deferred-work.md`] — **APPLIED in-pass**
- [x] [Review][Defer] **NEW AC-11 routing gap, and the only substantive finding of this pass.** `catalog.gallery.*` says *obraz*/*image* while `catalog.image_viewer.*` says *zdjęcie*/*photo* — two nouns for one object, in **both** languages, rendered by the **same component** one click apart (`ModelGallery.tsx:161,170,191` vs the lightbox it opens from `:130,151`). Strictly stronger than the `viewer3d.tooltip.expand` item the first review routed. Correctly unfixable here (`catalog.gallery.*` is not a § 3 prefix; § 5 forbids editing outside it) — **routing was owed and is now written** to `deferred-work.md`, new section "Deferred from: second code review of 54-1-i18n-parity-audit", `status: OPEN`. The entry also records the scope-definition weakness it exposes: § 3 is a prefix list, but V-11 evicted two keys on a *date* argument that nine kept `catalog.image_viewer.*` keys fail equally
- [x] [Review][Defer] Seven hardening gaps in the new checks, **none of which is a defect at this baseline** — every one requires a future state that does not exist: no flatness assertion before the `Record<string, string>` cast (a nested in-scope value would make the identical-string check pass vacuously and throw in `placeholders()`; V-2 proved both files flat today); the 157 guard is count-only, so a one-out-one-in swap holds the length; `INITIATIVE_26_KEYS` exact-match would miss a plural sibling of an exact-listed key; the viewer-name uniqueness check tests equality, not substring overlap; nothing asserts an in-scope `{{count}}` key ships the full pl `one/few/many/other` family; the allowlist-honesty guard pins `pl` **to** `en`, so a genuinely *better* future Polish translation goes red with a message pointing at reverting rather than at deleting the exemption (correct invariant: identical **or** absent from the allowlist); and AC-4's empty-value check reports an in-scope key missing from `pl.json` as *"is empty"* rather than as the § 5 `Block If` parity break. Raised by the Edge Case Hunter and Blind Hunter layers. Deferred as a natural bundle with the already-ledgered test-consolidation entry — applying them now would mean new executable lines in a file the AC-10 gate has already certified, for zero change in current behaviour

**Dismissed with reason (8), the two that matter:** (1) Blind Hunter argued **both** P-5 comment clauses are false, because `viewer3d.tooltip.expand` only mounts behind an expanded Files-tab row (`FilesTab.tsx:401`, gated `isExpanded && stlFile !== undefined`) that neither spec ever opens, and because the lightbox is a modal `@base-ui/react` dialog that inerts outside content. **Rejected**: the clause's factual half — that a same-name surface ships today — is verifiably true (`pl.json:459` = `"Powiększ"`, visible `<Button>` text at `Viewer3DInline.tsx:243-245`), and *"would silently widen the assertion"* continues the sentence *"these assertions are about the TOOLBAR's controls"*, so it reads as loss of **specificity**, which holds regardless of what is mounted. AC-7's actual requirement — that neither comment be left asserting a collision that no longer exists — is discharged explicitly in both files. (2) § 12's tally *"2 `identical-justified`"* against a three-entry allowlist is **coherent, not contradictory**: the table records **pre**-remediation verdicts, so `categoryWithCount_one` is correctly `defect`, and the third allowlist entry is post-remediation and documented as such in the test source (`i18n.test.ts:92-95`). Also dismissed: single-call-site `Live consumer` cells (AC-8 requires *at least one*); the suffix-less `categoryWithCount` base form being unreachable under i18next v4 plural resolution (harmless family-shape consistency; reverting would re-split the family); and the 24 in-scope English `_few`/`_many` values that can never render (forced by the repo-wide parity gate's design, pre-existing, out of scope).

**AC-10 was NOT MET at the first review moment, then CLOSED by Laura/controller after P-4.** `infra/scripts/check-all.sh` ran standalone in `.hermes/run-logs/check-all-54-1-20260731_045810.log` and returned exit 0 with **16/16** stages and `all green.` The pytest determinism evidence was completed with two extra `apps/api` runs in `.hermes/run-logs/pytest-determinism-54-1-20260731_051124.log`; together with the check-all run, all three reported **1961 passed, 3 skipped**. This closes the controller-owned AC-10 gate evidence; it does not replace the still-needed final review verdict.

---

## 9. Verification commands

```bash
# baseline + key counts (T1, T8)
git rev-parse HEAD && git status --short
python3 -c "import json;a=set(json.load(open('apps/web/src/locales/en.json')));b=set(json.load(open('apps/web/src/locales/pl.json')));print(len(a),len(b),a==b)"

# the shipped parity gate, plus the new checks (AC-2, AC-3, AC-4, AC-5)
cd apps/web && npx vitest run tests/i18n.test.ts

# per-key liveness (AC-8) — one grep per in-scope key, or a scripted loop
grep -rn "catalog\.browse\." apps/web/src --include=*.ts --include=*.tsx

# ownership re-verification of the drawer keys (T2, D-6 — expect 47e8407 + 3202b7c)
git log -S 'catalog.filters.openFilters' --oneline -- apps/web/src/locales/en.json
git show 3202b7c -- apps/web/src/locales/en.json | grep -E '^\+.*catalog\.filters\.(openFilters|title)'

# AC-7 comment-prose-only proof: must print nothing but comment lines
git diff -U0 apps/web/tests/visual/image-viewer-zoom.spec.ts \
            apps/web/tests/visual/image-viewer-containment.spec.ts \
  | grep -E '^[+-]' | grep -vE '^[+-]{3}' | grep -vE '^[+-]\s*//'

# viewer suites stay green (AC-7) — both files, containment is the standing suite
cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts \
  image-viewer-zoom.spec.ts image-viewer-containment.spec.ts

# full gate (AC-10)
mkdir -p .hermes/run-logs && infra/scripts/check-all.sh 2>&1 | tee .hermes/run-logs/check-all-54-1-$(date +%Y%m%d_%H%M%S).log
```

---

## 10. Dev Notes

**Relevant architecture patterns and constraints.**
- i18n is mandatory for user-visible strings; `useTranslation()` + `t("namespace.key")`; both locale files keep the same key set (`project-context.md` § Framework-Specific Rules, § Frontend folder layout). i18next 24 / react-i18next 15 — v13/14 examples do not apply.
- Polish plural categories in i18next are `one` / `few` / `many` / `other`, where `other` covers fractional values. `"{{count}} modelu"` as the `_other` form (`pl.json:298`, `:935`, `:841`) is **correct**, not a bug — do not "fix" it.
- Visual regression matrix is fixed at four projects, locale `pl-PL`, timezone `Europe/Warsaw` (`project-context.md:110`). A string change is visible on all four or on none.
- Baseline Acceptance Gate: any commit touching `apps/web/tests/visual/__snapshots__/**/*.png` needs one `baseline-reviewed:` line per changed PNG, enforced by `apps/web/.husky/pre-commit` + `commit-msg`. **The named reviewer must be whoever actually inspected the PNG** — this repo has two ledgered recurrences of forged sign-offs (`sprint-status.yaml` action items, epic:45 and epic:46, both still `open`).

**Source tree components to touch.** Only `apps/web/src/locales/` and `apps/web/tests/` (see § 7). No `apps/web/src/modules/`, no `apps/api/`, no `workers/`, no `infra/`.

**Testing standards summary.** Vitest with `globals: false` → any *new* test file needs `afterEach(cleanup)`; extending the existing `tests/i18n.test.ts` (which renders nothing) avoids that trap entirely — another reason for D-1. No real network in any test. `npm run lint` must pass with `--max-warnings=0`.

### Project Structure Notes

- The audit's target files sit at `apps/web/src/locales/{en,pl}.json` and the gate at `apps/web/tests/i18n.test.ts` — both exactly where `AGENTS.md` § Repository layout and `project-context.md` place them. No structural variance.
- This story adds **no** new file to `apps/web/src`, so the Visual Coverage Contract (`apps/web/src/ui/*.tsx` additions require a matching visual spec) does not trigger.
- Story-branch discipline per `AGENTS.md`: branch from `main`, one commit, ff-only merge, no squash. `check-all.sh` is the closeout/merge gate, not the lean pre-push hook.

### References

- `_bmad-output/planning-artifacts/prd.md:2262` — the binding per-story ownership rule ("Epic 54 is the final cross-surface parity/a11y/visual audit and remediation pass — it is never the first place proof appears").
- `_bmad-output/planning-artifacts/prd.md:2264` — `NFR26-I18N-1` verbatim.
- `_bmad-output/planning-artifacts/prd.md:2265` — `NFR26-A11Y-1`, incl. "distinguishable by accessible name, not by appearance alone" (grounds D-5).
- `_bmad-output/planning-artifacts/epics.md:4417` — NFR ↔ story ownership matrix row for `NFR26-I18N-1`.
- `_bmad-output/planning-artifacts/epics.md:4581-4591` — Epic E54 goal, the 2026-07-26 recast, and the Story 54.1 sketch incl. the `VERIFY-AT-CREATE-STORY` instruction.
- `_bmad-output/planning-artifacts/epics.md:4593-4595` — Story 54.2's remit (the boundary § 5 enforces).
- `_bmad-output/planning-artifacts/architecture.md:3375` — `ui/dialog.tsx` is Ask First.
- `_bmad-output/planning-artifacts/architecture.md:3386` — `G26-DEVGO`, `G26-LIB` gate states.
- `_bmad-output/implementation-artifacts/spec-47-1-i18n.md:18,24,50,85` — the Initiative 25 precedent: scope collapse, parity-preservation constraint, and the key-set diff command.
- `_bmad-output/implementation-artifacts/53-3-lightbox-test-contract.md` § 2 V-15, V-17 — the 1047→1048 key-set record and the `trigger_label` collision routed to 54.1.
- `_bmad-output/implementation-artifacts/deferred-work.md` — "Deferred from: story 47.1 dev review" (no liveness check); all `status: OPEN` E50–E53 entries (none i18n).
- `apps/web/tests/i18n.test.ts:15-22` — the shipped parity gate.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — all line citations in § 2 and § 3.
- `AGENTS.md` § Branching and workflow, § Execution discipline; `_bmad-output/project-context.md` § Framework-Specific Rules, § Testing Rules, § UI quality gates.

---

## 11. Story Creation Questions

**None open. Both items raised at create time were closed by the Validate pass (§ 18):**

1. ~~**§ 2 V-10's provenance caveat.**~~ **CLOSED.** VS re-derived the baseline with shell access: `git rev-parse HEAD` = `c3db4aaf355b6511abde3fa908be6c644bab5d99`, matching the frontmatter exactly; `git status --short --branch` = `main...origin/main`, only `sprint-status.yaml` modified and this story untracked. No product, test, locale or snapshot file differs. **The frontmatter SHA is now verified, not inherited.**
2. ~~**D-6's ownership question.**~~ **CLOSED** by `git log -S` + `git show` — see § 2 V-11 and the rewritten D-6. Two keys leave the scope, one stays with 52.1.

Nothing here is left for `bmad-dev-story` to decide.

---

## 12. Audit table — AC-1

**Scope re-measured this run, not copied from § 2 V-3:** `python3` prefix count over `en.json` at `c3db4aa` →
`catalog.empty*` 2 + `catalog.browse.*` 13 + `catalog.suggestions.*` 4 + `catalog.image_viewer.*` 14 +
`admin.tabs.categories` 1 + `modules.admin.categories.*` 122 + `catalog.filters.openFiltersWithCount` 1 = **157**.
Confirmed by the new `covers exactly the 157 keys the audit enumerated` assertion in `apps/web/tests/i18n.test.ts`.

**In-scope key count (re-measured):** **157**.
**en / pl key counts before → after:** **1048 / 1048 → 1048 / 1048**, set-difference empty in both directions at both
points (`python3` over both files; the shipped `"en and pl have identical key sets"` assertion green at both points).
No key was added, deleted or re-keyed — every remediation was a value change on the Polish side. `en.json` is
byte-unchanged.

**Rows below: 127, covering all 157 keys.** A plural family is one row *only* where every form shares one verdict;
`catalog.browse.categoryWithCount_*` and `modules.admin.categories.model_count_*` are therefore listed per form.
The `en`/`pl` columns show the family's first form. **Verdict tally: 122 `ok`, 2 `identical-justified`, 3 `defect`.**

**Owning story was derived mechanically, not assumed** — one pass over `git log --reverse -- apps/web/src/locales/en.json`
attributing each key to the first commit that added it. All 157 attributed, zero unattributed. ⚠️ **This corrects § 3 and
§ 2 V-9 on one point:** nine of the fourteen `catalog.image_viewer.*` keys — including `trigger_label` — were introduced
by **Story 22.3** (`812c7bd`, 2026-05-24), not by 53.2. 53.2 (`933013e`) added the four `zoom_*` keys and 53.3
(`c3db4aa`) added `error`. See § 13 ruling (e) for what that changes about the collision's ownership, and § 14 for why
it does not change the scope.

**Liveness (AC-8): zero orphans.** Every one of the 157 keys has a live consumer under `apps/web/src`, excluding
`*.test.ts`/`*.test.tsx` (a test is not a consumer). Evidence classes: **99** matched a quoted literal directly,
**48** are CLDR plural forms resolved through their base key, **10** are built by template literal in
`CurationQaPanel.tsx` (`` `…qa.${key}.action_label` `` `:91`, `` `…qa.${key}.action` `` `:93`,
`` `…qa.${finding.kind}.sub` `` `:211`). Nothing was deleted. The known `catalog.filters.tags` orphan (§ 2 V-13) was
**not** swept — it is outside § 3 and already ledgered.

| Key | Surface | `en` (first form) | `pl` (first form) | Verdict | Owning story | Live consumer (`apps/web/src/`) |
|---|---|---|---|---|---|---|
| `catalog.emptyCategory` | Category-scoped empty state | Nothing in this category yet. | W tej kategorii nie ma jeszcze nic. | `ok` | 51.2 | `modules/catalog/routes/CatalogList.tsx:459` |
| `catalog.emptyInCategory` | Category-scoped empty state | No matches in {{name}}. | Brak wyników w kategorii {{name}}. | `ok` | 51.2 | `modules/catalog/routes/CatalogList.tsx:443` |
| `catalog.browse.openBrowse` | Browse rail / scope chip / model detail | Browse | Przeglądaj | `ok` | 51.3 | `modules/catalog/components/BrowseSheet.tsx:53` |
| `catalog.browse.railLabel` | Browse rail / scope chip / model detail | Browse categories | Przeglądaj kategorie | `ok` | 51.1 | `modules/catalog/components/BrowseSheet.tsx:62` |
| `catalog.browse.allCatalog` | Browse rail / scope chip / model detail | All catalog | Cały katalog | `ok` | 51.1 | `modules/catalog/routes/CatalogList.tsx:309` |
| `catalog.browse.categoryWithCount` | Browse rail / scope chip / model detail | {{name}}, {{count}} models | {{name}}, {{count}} modeli | `defect` | 51.1 | `modules/catalog/components/BrowseCategoryList.tsx:123` |
| `catalog.browse.categoryWithCount_one` | Browse rail / scope chip / model detail | {{name}}, {{count}} model | {{name}}, {{count}} model | `defect` | 51.1 | `modules/catalog/components/BrowseCategoryList.tsx:123` |
| `catalog.browse.categoryWithCount_few` | Browse rail / scope chip / model detail | {{name}}, {{count}} models | {{name}}, {{count}} modele | `ok` | 51.1 | `modules/catalog/components/BrowseCategoryList.tsx:123` |
| `catalog.browse.categoryWithCount_many` | Browse rail / scope chip / model detail | {{name}}, {{count}} models | {{name}}, {{count}} modeli | `ok` | 51.1 | `modules/catalog/components/BrowseCategoryList.tsx:123` |
| `catalog.browse.categoryWithCount_other` | Browse rail / scope chip / model detail | {{name}}, {{count}} models | {{name}}, {{count}} modelu | `ok` | 51.1 | `modules/catalog/components/BrowseCategoryList.tsx:123` |
| `catalog.browse.activeScope` | Browse rail / scope chip / model detail | Active category: {{name}} | Aktywna kategoria: {{name}} | `ok` | 51.2 | `modules/catalog/components/ScopeChip.tsx:52` |
| `catalog.browse.searchEntireCatalog` | Browse rail / scope chip / model detail | Search entire catalog | Szukaj w całym katalogu | `ok` | 51.2 | `modules/catalog/routes/CatalogList.tsx:447` |
| `catalog.browse.clearCategory` | Browse rail / scope chip / model detail | Clear category | Wyczyść kategorię | `ok` | 51.2 | `modules/catalog/components/ScopeChip.tsx:43` |
| `catalog.browse.modelCategoriesLabel` | Browse rail / scope chip / model detail | Categories | Kategorie | `ok` | 51.4 | `modules/catalog/components/ModelCategoriesSection.tsx:76` |
| `catalog.browse.noCategoriesAdmin` | Browse rail / scope chip / model detail | No categories — needs curation | Bez kategorii — do uzupełnienia | `ok` | 51.4 | `modules/catalog/components/ModelCategoriesSection.tsx:67` |
| `catalog.suggestions.queryOption` | Inline search suggestions | Search: {{query}} | Szukaj: {{query}} | `ok` | 50.3 | `modules/catalog/components/SearchSuggest.tsx:162` |
| `catalog.suggestions.tagOption` | Inline search suggestions | Add filter: {{name}}, group {{group}} | Dodaj filtr: {{name}}, grupa {{group}} | `ok` | 50.3 | `modules/catalog/components/SearchSuggest.tsx:181` |
| `catalog.suggestions.tagOptionNoGroup` | Inline search suggestions | Add filter: {{name}} | Dodaj filtr: {{name}} | `ok` | 50.3 | `modules/catalog/components/SearchSuggest.tsx:182` |
| `catalog.suggestions.overflowNote` | Inline search suggestions | More matches — open Filters to browse all | Więcej wyników — otwórz Filtry, aby przejrzeć wszystkie | `ok` | 50.3 | `modules/catalog/components/SearchSuggest.tsx:218` |
| `catalog.image_viewer.trigger_label` | Lightbox controls (catalog + /share) | Open fullscreen | Otwórz na pełnym ekranie | `defect` | 22.3 | `modules/catalog/components/ModelGallery.tsx:130` |
| `catalog.image_viewer.trigger_tooltip` | Lightbox controls (catalog + /share) | View full quality | Pełna jakość | `ok` | 22.3 | `modules/catalog/components/ModelGallery.tsx:152` |
| `catalog.image_viewer.close` | Lightbox controls (catalog + /share) | Close | Zamknij | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:995` |
| `catalog.image_viewer.prev` | Lightbox controls (catalog + /share) | Previous photo | Poprzednie zdjęcie | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1020` |
| `catalog.image_viewer.next` | Lightbox controls (catalog + /share) | Next photo | Następne zdjęcie | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1029` |
| `catalog.image_viewer.counter` | Lightbox controls (catalog + /share) | {{current}} / {{total}} | {{current}} / {{total}} | `identical-justified` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:984` |
| `catalog.image_viewer.thumb_label` | Lightbox controls (catalog + /share) | Photo {{index}} | Zdjęcie {{index}} | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1148` |
| `catalog.image_viewer.loading` | Lightbox controls (catalog + /share) | Loading full image… | Wczytywanie pełnego obrazu… | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:493` |
| `catalog.image_viewer.error` | Lightbox controls (catalog + /share) | The photo could not be loaded. | Nie udało się wczytać zdjęcia. | `ok` | 53.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:502` |
| `catalog.image_viewer.dialog_title` | Lightbox controls (catalog + /share) | Photo gallery | Galeria zdjęć | `ok` | 22.3 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:874` |
| `catalog.image_viewer.zoom_in` | Lightbox controls (catalog + /share) | Zoom in | Powiększ | `ok` | 53.2 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1089` |
| `catalog.image_viewer.zoom_out` | Lightbox controls (catalog + /share) | Zoom out | Pomniejsz | `ok` | 53.2 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1099` |
| `catalog.image_viewer.zoom_reset` | Lightbox controls (catalog + /share) | Fit | Dopasuj | `ok` | 53.2 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:1109` |
| `catalog.image_viewer.zoom_level` | Lightbox controls (catalog + /share) | Zoom {{percent}}% | Powiększenie {{percent}}% | `ok` | 53.2 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:507` |
| `admin.tabs.categories` | Admin nav | Categories | Kategorie | `ok` | 52.2 | `modules/admin/AdminTabs.tsx:121` |
| `modules.admin.categories.title` | Admin — category CRUD | Browse categories | Kategorie przeglądania | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:297` |
| `modules.admin.categories.description` | Admin — category CRUD | Curated browse entry points. Each carries an inclusion criterion — the admission test for what belongs. | Kuratorowane punkty wejścia do katalogu. Każda ma kryterium przynależności — test tego, co do niej należy. | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:300` |
| `modules.admin.categories.empty` | Admin — category CRUD | No browse categories yet. | Brak kategorii przeglądania. | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:330` |
| `modules.admin.categories.error_title` | Admin — category CRUD | Could not load browse categories | Nie udało się wczytać kategorii przeglądania | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:355` |
| `modules.admin.categories.model_count_one` | Admin — category CRUD | {{count}} model | {{count}} model | `identical-justified` | 52.2 | `modules/admin/CategoriesPage.tsx:96` |
| `modules.admin.categories.model_count_few` | Admin — category CRUD | {{count}} models | {{count}} modele | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:96` |
| `modules.admin.categories.model_count_many` | Admin — category CRUD | {{count}} models | {{count}} modeli | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:96` |
| `modules.admin.categories.model_count_other` | Admin — category CRUD | {{count}} models | {{count}} modelu | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:96` |
| `modules.admin.categories.actions.create` | Admin — category CRUD | New category | Nowa kategoria | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:306` |
| `modules.admin.categories.actions.category_menu` | Admin — category CRUD | Actions for category {{name}} | Akcje dla kategorii {{name}} | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:104` |
| `modules.admin.categories.actions.edit` | Admin — category CRUD | Edit | Edytuj | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:112` |
| `modules.admin.categories.actions.move_up` | Admin — category CRUD | Move up | Przesuń w górę | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:119` |
| `modules.admin.categories.actions.move_down` | Admin — category CRUD | Move down | Przesuń w dół | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:126` |
| `modules.admin.categories.actions.delete` | Admin — category CRUD | Delete | Usuń | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:129` |
| `modules.admin.categories.fields.slug` | Admin — category form | Slug | Identyfikator | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:110` |
| `modules.admin.categories.fields.name_en` | Admin — category form | English name | Nazwa angielska | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:115` |
| `modules.admin.categories.fields.name_pl` | Admin — category form | Polish name | Nazwa polska | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:119` |
| `modules.admin.categories.fields.name_pl_placeholder` | Admin — category form | Leave empty to use the English name | Zostaw puste, aby użyć nazwy angielskiej | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:124` |
| `modules.admin.categories.fields.criterion` | Admin — category form | Inclusion criterion | Kryterium przynależności | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:128` |
| `modules.admin.categories.fields.criterion_placeholder` | Admin — category form | One sentence: what belongs in this category? | Jedno zdanie: co należy do tej kategorii? | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:137` |
| `modules.admin.categories.fields.criterion_hint` | Admin — category form | Shown in this list so two categories can be compared side by side. | Widoczne na liście, aby dało się porównać dwie kategorie obok siebie. | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:141` |
| `modules.admin.categories.form.title_create` | Admin — category form | New category | Nowa kategoria | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:94` |
| `modules.admin.categories.form.title_edit` | Admin — category form | Edit category | Edytuj kategorię | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:95` |
| `modules.admin.categories.form.description` | Admin — category form | Name the category in both languages and state the criterion for including a model. | Nazwij kategorię w obu językach i podaj kryterium przypisania modelu. | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:98` |
| `modules.admin.categories.form.submit_create` | Admin — category form | Create category | Utwórz kategorię | `ok` | 52.2 | `modules/admin/dialogs/CategoryFormDialog.tsx:160` |
| `modules.admin.categories.delete.title` | Admin — delete dialog | Delete “{{name}}”? | Usunąć „{{name}}”? | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:54` |
| `modules.admin.categories.delete.description` | Admin — delete dialog | Deleting a category removes it from browse navigation. Models are never deleted. | Usunięcie kategorii zdejmuje ją z nawigacji. Modele nigdy nie są usuwane. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:57` |
| `modules.admin.categories.delete.confirm_clean` | Admin — delete dialog | This category has no assigned models. Deleting it removes it from browse navigation. | Ta kategoria nie ma przypisanych modeli. Usunięcie zdejmie ją z nawigacji. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:71` |
| `modules.admin.categories.delete.confirm_assigned_*` (4 forms) | Admin — delete dialog | This category has {{count}} assigned models. Deleting it will be refused until the assignments are detached. | Ta kategoria ma przypisane {{count}} modele. Usunięcie zostanie odrzucone, dopóki przypisania nie zostaną odpięte. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:70` |
| `modules.admin.categories.delete.in_use_title_*` (4 forms) | Admin — delete dialog | Cannot delete — {{count}} models are assigned | Nie można usunąć — przypisane są {{count}} modele | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:88` |
| `modules.admin.categories.delete.in_use_title_hidden` | Admin — delete dialog | Cannot delete — this category still has assignments | Nie można usunąć — kategoria wciąż ma przypisania | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:89` |
| `modules.admin.categories.delete.in_use_body` | Admin — delete dialog | Detaching removes the assignments and deletes the category in one audited operation. The models themselves stay untouched and public. | Odpięcie usuwa przypisania i kategorię w jednej operacji zapisanej w audycie. Same modele pozostają nietknięte i publiczne. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:93` |
| `modules.admin.categories.delete.in_use_body_hidden` | Admin — delete dialog | The remaining assignments belong to models in the trash, so they are not counted above. Detaching removes them and deletes the category in one audited operation — a restored model will no longer carry this category. | Pozostałe przypisania należą do modeli w koszu, więc nie są liczone powyżej. Odpięcie usuwa je i kasuje kategorię w jednej operacji zapisanej w audycie — przywrócony model nie będzie już należał do tej kategorii. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:94` |
| `modules.admin.categories.delete.has_children_title` | Admin — delete dialog | Cannot delete — this category has child categories | Nie można usunąć — ta kategoria ma podkategorie | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:105` |
| `modules.admin.categories.delete.has_children_body` | Admin — delete dialog | Clear or delete the child categories first. Detaching models does not resolve this. | Najpierw wyczyść lub usuń podkategorie. Odpięcie modeli tego nie rozwiązuje. | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:110` |
| `modules.admin.categories.delete.submit` | Admin — delete dialog | Delete | Usuń | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:133` |
| `modules.admin.categories.delete.submit_detach` | Admin — delete dialog | Detach and delete | Odepnij i usuń | `ok` | 52.2 | `modules/admin/dialogs/DeleteCategoryDialog.tsx:138` |
| `modules.admin.categories.queue.title_pending` | Admin — curation queue | Needs curation | Do sprawdzenia | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:389` |
| `modules.admin.categories.queue.title_*` (4 forms) | Admin — curation queue | Needs curation ({{count}}) | Do sprawdzenia ({{count}}) | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:388` |
| `modules.admin.categories.queue.description` | Admin — curation queue | Models with no category. This is a valid state — they stay public and visible everywhere. | Modele bez kategorii. To poprawny stan — pozostają publiczne i widoczne wszędzie. | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:394` |
| `modules.admin.categories.queue.empty` | Admin — curation queue | Nothing needs attention. | Nic nie wymaga uwagi. | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:420` |
| `modules.admin.categories.queue.error` | Admin — curation queue | Could not load the curation queue | Nie udało się wczytać kolejki kuratorskiej | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:399` |
| `modules.admin.categories.queue.assign` | Admin — curation queue | Assign categories | Przypisz kategorie | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:445` |
| `modules.admin.categories.qa.title_pending` | Admin — curation QA | Curation QA | Kontrola kuratorska | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:245` |
| `modules.admin.categories.qa.title_*` (4 forms) | Admin — curation QA | Curation QA ({{count}}) | Kontrola kuratorska ({{count}}) | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:246` |
| `modules.admin.categories.qa.description` | Admin — curation QA | Advisory only. No finding is ever applied for you, and a category is never inferred from a model's tags. | Wyłącznie doradczo. Żadne ustalenie nie jest stosowane za Ciebie, a przynależność do kategorii nigdy nie wynika z tagów modelu. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:249` |
| `modules.admin.categories.qa.empty` | Admin — curation QA | Nothing needs attention. | Nic nie wymaga uwagi. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:288` |
| `modules.admin.categories.qa.partial` | Admin — curation QA | Some checks could not run — one of the reads did not complete. | Części kontroli nie dało się wykonać — jeden z odczytów się nie powiódł. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:272` |
| `modules.admin.categories.qa.overflow_*` (4 forms) | Admin — curation QA | {{count}} more findings in this check. | Jeszcze {{count}} ustalenia w tej kontroli. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:225` |
| `modules.admin.categories.qa.empty_category.finding` | Admin — curation QA | Category “{{name}}” is empty | Kategoria „{{name}}” jest pusta | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:156` |
| `modules.admin.categories.qa.empty_category.sub` | Admin — curation QA | An empty category stays visible in navigation, dimmed. | Pusta kategoria zostaje widoczna w nawigacji, wyszarzona. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.empty_category.action` | Admin — curation QA | Open category | Otwórz kategorię | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:93` |
| `modules.admin.categories.qa.empty_category.action_label` | Admin — curation QA | Go to category {{name}} in the list | Przejdź do kategorii {{name}} na liście | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:91` |
| `modules.admin.categories.qa.tiny_category.finding_*` (4 forms) | Admin — curation QA | Category “{{name}}” has {{count}} models | Kategoria „{{name}}” ma {{count}} modele | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:160` |
| `modules.admin.categories.qa.tiny_category.sub` | Admin — curation QA | A very small category — it is behaving like a narrow tag. | Bardzo mała kategoria — zachowuje się jak wąski tag. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.tiny_category.action` | Admin — curation QA | Open category | Otwórz kategorię | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:93` |
| `modules.admin.categories.qa.tiny_category.action_label` | Admin — curation QA | Go to category {{name}} in the list | Przejdź do kategorii {{name}} na liście | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:91` |
| `modules.admin.categories.qa.label_collision.finding` | Admin — curation QA | Label collision: category “{{category}}” / tag “{{tag}}” ({{group}}) | Kolizja etykiet: kategoria „{{category}}” / tag „{{tag}}” ({{group}}) | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:175` |
| `modules.admin.categories.qa.label_collision.finding_groupless` | Admin — curation QA | Label collision: category “{{category}}” / tag “{{tag}}” | Kolizja etykiet: kategoria „{{category}}” / tag „{{tag}}” | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:170` |
| `modules.admin.categories.qa.label_collision.sub` | Admin — curation QA | Similar labels are permitted only with an explicitly recorded semantic distinction. | Podobne etykiety są dozwolone tylko z zapisanym rozróżnieniem semantycznym. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.label_collision.action` | Admin — curation QA | Resolve | Rozstrzygnij | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:109` |
| `modules.admin.categories.qa.label_collision.action_label` | Admin — curation QA | Resolve the label collision between category {{category}} and tag {{tag}} in tag groups | Rozstrzygnij kolizję etykiet kategorii {{category}} i tagu {{tag}} w grupach tagów | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:104` |
| `modules.admin.categories.qa.over_categorized.finding_*` (4 forms) | Admin — curation QA | Model “{{name}}” has {{count}} categories | Model „{{name}}” ma {{count}} kategorie | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:182` |
| `modules.admin.categories.qa.over_categorized.sub` | Admin — curation QA | The suggested norm is 1–3. This is a warning, not an error. | Sugerowana norma to 1–3. To ostrzeżenie, nie błąd. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.over_categorized.action` | Admin — curation QA | Edit categories | Edytuj kategorie | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:126` |
| `modules.admin.categories.qa.over_categorized.action_label` | Admin — curation QA | Edit categories for model {{name}} | Edytuj kategorie modelu {{name}} | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:123` |
| `modules.admin.categories.qa.uncategorized_models.finding_*` (4 forms) | Admin — curation QA | {{count}} models with no category | {{count}} modele bez kategorii | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:187` |
| `modules.admin.categories.qa.uncategorized_models.sub` | Admin — curation QA | A valid state — these models stay public. Curation work, listed below. | To poprawny stan — modele pozostają publiczne. Praca kuratorska, lista poniżej. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.uncategorized_models.action` | Admin — curation QA | Show list | Pokaż listę | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:137` |
| `modules.admin.categories.qa.uncategorized_models.action_label` | Admin — curation QA | Go to the list of models with no category | Przejdź do listy modeli bez kategorii | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:135` |
| `modules.admin.categories.qa.ungrouped_tags.finding_*` (4 forms) | Admin — curation QA | {{count}} user-facing tags with no group | {{count}} tagi użytkowe bez grupy | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:191` |
| `modules.admin.categories.qa.ungrouped_tags.sub` | Admin — curation QA | Grouping keeps the filter surface readable. | Grupowanie utrzymuje czytelność panelu filtrów. | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:211` |
| `modules.admin.categories.qa.ungrouped_tags.action` | Admin — curation QA | Tag groups | Grupy tagów | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:147` |
| `modules.admin.categories.qa.ungrouped_tags.action_label` | Admin — curation QA | Go to tag groups to place the tags with no group | Przejdź do grup tagów, aby przypisać tagi bez grupy | `ok` | 52.3 | `modules/admin/CurationQaPanel.tsx:145` |
| `modules.admin.categories.editor.title` | Admin — model-category editor | Model categories | Kategorie modelu | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:129` |
| `modules.admin.categories.editor.submit` | Admin — model-category editor | Replace categories | Zastąp kategorie | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:226` |
| `modules.admin.categories.editor.load_error` | Admin — model-category editor | Could not load this model's categories | Nie udało się wczytać kategorii tego modelu | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:154` |
| `modules.admin.categories.editor.advisory_*` (4 forms) | Admin — model-category editor | {{count}} categories — the suggested norm is 1–3. Saving is not blocked. | {{count}} kategorie — sugerowana norma to 1–3. Zapis nie jest blokowany. | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:198` |
| `modules.admin.categories.editor.last_write_you` | Admin — model-category editor | Last changed by you, {{at}} | Ostatnia zmiana: Ty, {{at}} | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:112` |
| `modules.admin.categories.editor.last_write_other` | Admin — model-category editor | Last changed by another admin, {{at}} | Ostatnia zmiana: inny administrator, {{at}} | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:116` |
| `modules.admin.categories.editor.last_write_unknown_actor` | Admin — model-category editor | Last changed {{at}} | Ostatnia zmiana: {{at}} | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:119` |
| `modules.admin.categories.editor.toast.replaced` | Admin — model-category editor | Categories replaced | Kategorie zastąpione | `ok` | 52.2 | `modules/admin/ModelCategoriesDialog.tsx:97` |
| `modules.admin.categories.toast.created` | Admin — category CRUD | Category created | Kategoria utworzona | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:226` |
| `modules.admin.categories.toast.updated` | Admin — category CRUD | Category updated | Kategoria zaktualizowana | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:251` |
| `modules.admin.categories.toast.deleted` | Admin — category CRUD | Category deleted | Kategoria usunięta | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:269` |
| `modules.admin.categories.toast.reordered` | Admin — category CRUD | Order updated | Kolejność zaktualizowana | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:207` |
| `modules.admin.categories.toast.reorder_failed` | Admin — category CRUD | Could not change the order | Nie udało się zmienić kolejności | `ok` | 52.2 | `modules/admin/CategoriesPage.tsx:209` |
| `modules.admin.categories.errors.slug_conflict` | Admin — category CRUD | That slug is already taken by another category. | Ten identyfikator jest już zajęty przez inną kategorię. | `ok` | 52.2 | `modules/admin/dialogs/apiErrorMessage.ts:25` |
| `modules.admin.categories.errors.invalid` | Admin — category CRUD | The category could not be saved with these values. | Nie udało się zapisać kategorii z tymi wartościami. | `ok` | 52.2 | `modules/admin/dialogs/apiErrorMessage.ts:26` |
| `modules.admin.categories.errors.not_found` | Admin — category CRUD | That category no longer exists. | Ta kategoria już nie istnieje. | `ok` | 52.2 | `modules/admin/dialogs/apiErrorMessage.ts:27` |
| `modules.admin.categories.errors.bad_request` | Admin — category CRUD | The request could not be processed. | Nie udało się przetworzyć żądania. | `ok` | 52.2 | `modules/admin/dialogs/apiErrorMessage.ts:28` |
| `modules.admin.categories.errors.generic` | Admin — category CRUD | Something went wrong. Try again. | Coś poszło nie tak. Spróbuj ponownie. | `ok` | 52.2 | `modules/admin/dialogs/apiErrorMessage.ts:30` |
| `catalog.filters.openFiltersWithCount` | Filters drawer trigger | Filters ({{count}}) | Filtry ({{count}}) | `ok` | 52.1 | `modules/catalog/components/FiltersPanel.tsx:138` |

---

## 13. Terminology rulings — AC-6

| # | Divergence | Surfaces | Verdict | Chosen wording / rationale |
|---|---|---|---|---|
| a | "Browse categories" → `Przeglądaj kategorie` vs `Kategorie przeglądania` | browse rail (`catalog.browse.railLabel`) / admin (`modules.admin.categories.title`) | **`keep, justified`** | The two strings occupy different grammatical roles for the same entity, and Polish will not carry one form through both. `railLabel` is the `aria-label` of a navigation region — a verb phrase is what a screen-reader user needs to hear ("Przeglądaj kategorie" = *do this*). `modules.admin.categories.title` is an H1 naming a managed entity type — a noun phrase ("Kategorie przeglądania" = *these things*). The **entity noun is already consistent** where it matters: `admin.tabs.categories` and `catalog.browse.modelCategoriesLabel` are both plain `Kategorie`. Forcing "Przeglądaj kategorie" onto a page title would read as a command on a management screen; forcing "Kategorie przeglądania" onto the rail would announce a noun where an action is expected. Also guarded from the other side: `browse-i18n.test.ts:55-63` already pins `Przeglądaj` on the rail and rejects the storefront synonyms. *(Citation corrected 2026-07-31 by the second native code review — this story's own +8-line `COINCIDENTAL_MATCHES` edit to the same file shifted the guard down from `:51-55`.)* No change. **Rationale caveat, recorded not resolved:** the grammatical-role argument above is weaker than it reads — `catalog.browse.railLabel` is *also* rendered as a visible `<SheetTitle>` at `BrowseSheet.tsx:62` (asserted as a dialog accessible name at `tests/visual/browse-sheet.spec.ts:19`), so the key is simultaneously a nav `aria-label` and a sheet title. Raised by the second review's Blind Hunter layer. The **verdict is unaffected** — `keep, justified` changes nothing in the tree either way — but a future fixer re-opening (a) should know the premise is not clean. |
| b | "needs curation" → `do uzupełnienia` vs `Do sprawdzenia` | catalog model detail (`catalog.browse.noCategoriesAdmin`) / admin queue (`modules.admin.categories.queue.title_pending`) | **`keep, justified`** | The **shared anchor term already matches**: the catalog badge reads `Bez kategorii — …` and the admin surface names the same state `bez kategorii` (`qa.uncategorized_models.finding_*`, `queue.description`). What differs is the trailing clause, and it differs because the roles differ — a per-model call-to-action that links to `/admin/categories` (`ModelCategoriesSection.tsx:67`, it is a `<Link>`, not a label) versus a queue heading over N models. `do uzupełnienia` tells one admin what to do about one model; `Do sprawdzenia` names a triage bucket. Each is idiomatic in its place and neither is wrong. **Disclosure, recorded as a consequence and not as the reason:** this string is *painted* and its Polish literal is asserted in two places (`tests/visual/catalog-detail-categories.spec.ts:15`, `ModelCategoriesSection.test.tsx:276`) with four visual baselines behind it, so remediating it would have tripped the § 5 **Ask First** gate. That cost is real, but the ruling above stands on the wording, not on the cost — had the audit judged the divergence harmful, the honest move would have been to halt and escalate, not to keep it for convenience. |
| c | `categoryWithCount` plural-family shape vs the two admin `model_count_*` families | browse rail / admin ×2 | **`remediate`** | **The strongest finding of the audit, and the only one internal to a single family.** `catalog.browse.categoryWithCount` contradicted *itself*: base `"{{name}}, modeli: {{count}}"` and `_one` `"{{name}}, model: {{count}}"` put the noun before the count with a colon, while `_few`/`_many`/`_other` put the count before the noun (`"{{name}}, {{count}} modele"`). English is uniform (`"{{name}}, {{count}} models"`) so the split is Polish-only, and it diverges from **both** admin counters (`modules.admin.categories.model_count_*` and `modules.admin.tagGroups.model_count_*`, which are byte-identical to each other). This is an `aria-label` (`BrowseCategoryList.tsx:123`, label and count deliberately folded into one accessible name per EXPERIENCE.md:220), so a screen-reader user moving down the rail heard *"Figurki, model: 1"* then *"Pudełka, 3 modele"* — two sentence shapes for one list. **Chosen wording:** align the two odd forms onto the shape the other three and both admin counters already use — base → `"{{name}}, {{count}} modeli"`, `_one` → `"{{name}}, {{count}} model"`. Chosen over the alternative (converting `_few`/`_many`/`_other` to the colon shape) because the `"{{count}} <noun>"` form is the repo's established counter idiom in three other places and matches the English source order. **Consequence, disclosed:** `_one` now reads `"{{name}}, {{count}} model"` in both locales — the same `model` loanword coincidence `modules.admin.categories.model_count_one` already ships and already documents. It is allowlisted in `tests/i18n.test.ts` and in `browse-i18n.test.ts` with that reason. Paints nothing: `aria-label` only, no visible-text consumer, confirmed by 60 green visual assertions across six browse/detail specs with zero snapshot churn. |
| d | "Couldn't load …" vs "Could not load …" (EN register) | admin tag groups / admin categories | **`keep, justified`** (in-scope side; out-of-scope half **routed**) | The in-scope family is **already internally consistent** on the full form: `modules.admin.categories.error_title` *"Could not load browse categories"*, `queue.error` *"Could not load the curation queue"*, `editor.load_error` *"Could not load this model's categories"*, `toast.reorder_failed` *"Could not change the order"*. The single divergent string is `modules.admin.tagGroups.error_title` *"Couldn't load the tag groups"* (`en.json:842`) — **Initiative 25 content, outside the § 3 key space**, which § 5 forbids editing ("Do not sweep, rename or delete keys outside the § 3 scope"). Nothing in scope needs changing, so nothing in scope was changed. It is also an English *register* choice, not a Polish translation defect — the `pl` side of both keys is correct and identical in form (`Nie udało się wczytać…`). Routed under AC-11 to `deferred-work.md` (§ "Deferred from: story 54.1 dev", `status: OPEN`) with a named owner and the one-word fix, rather than silently absorbed or silently dropped. |
| e | `trigger_label` == `zoom_in` == `Powiększ` (AC-7) | viewer controls, `/catalog` **and** `/share` | **`remediate`** | Two distinct controls carried one Polish accessible name while English distinguished them (*"Open fullscreen"* / *"Zoom in"*), so a screen-reader user hearing only the accessible name could not tell "open the fullscreen viewer" from "zoom in one step" — a direct `NFR26-A11Y-1` miss (`prd.md:2265`: *"distinguishable by accessible name, not by appearance alone"*). **Chosen wording:** `catalog.image_viewer.trigger_label` → **`"Otwórz na pełnym ekranie"`**. Chosen because it names the action rather than the result (the control is a button, not a state), it is unambiguous against `zoom_in`'s `Powiększ` and `zoom_level`'s `Powiększenie`, it tracks the English source exactly, and it reads correctly on the fourth consumer surface the § 1 journey does not name — the public `/share/$token` page (§ 2 V-12). The **key was not renamed** (D-5): the change is to the value only. `zoom_in` was left alone — it is correct, and it is the string three toolbar matchers in two specs resolve. **Ownership correction:** the story routed this as "53.2's defect". Mechanically, `trigger_label` and its `Powiększ` value were shipped by **Story 22.3** (`812c7bd`, 2026-05-24) and `zoom_in` by **Story 53.2** (`933013e`, 2026-07-29) — so 53.2 is the story that *created* the collision, by giving a new control a Polish name a two-month-old control already held, and 22.3 owns the string it collided with. 53.2 also *recorded* it (D-8) and routed it here, which is the process working. |

**Nothing is left unruled.** Four candidates entered from § 2 V-6 plus the pre-routed V-5 collision; the audit surfaced no sixth terminology divergence inside the 157-key scope.

---

## 14. Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5[1m]`), repo-local Claude Code, native `bmad-dev-story`. Routing this session:
mandatory session-start `bmad-help` → `_bmad/_config/bmad-help.csv` row `[DS] bmad-dev-story`
(`preceded-by: bmad-create-story:validate`). Executed on branch `feat/E54.1-i18n-parity-audit` under the controller's
per-story **G26-DEVGO for Story 54.1 only**. **NOT** an Ezop/human signature; does **not** close `G26-LIB`; does **not**
authorize 54.2 or the DN-4 residuals.

### Debug Log References

| # | Command | Result |
|---|---|---|
| 1 | `git rev-parse HEAD` / `git status --short --branch` | `c3db4aaf355b6511abde3fa908be6c644bab5d99`, matches frontmatter; on `feat/E54.1-i18n-parity-audit`; only `sprint-status.yaml` modified, this story untracked. No product/test/locale/snapshot diff at entry. |
| 2 | `python3` key-count over both locale files (T1, pre-change) | `en 1048 · pl 1048 · sets equal True · no nested values` |
| 3 | `npx vitest run tests/i18n.test.ts` (T1, pre-change) | `PASS (1) FAIL (0)` — the shipped parity gate green before any edit. |
| 4 | `git log -S 'catalog.filters.openFilters' --oneline -- …/en.json` (T2, D-6) | `3202b7c` + `47e8407`. `git show 47e8407` adds `+ "catalog.filters.openFilters"` and `+ "catalog.filters.title"` (2026-05-10); `git show 3202b7c` adds `+ "catalog.filters.openFiltersWithCount"` only and removes `catalog.filters.openTags`, body reads *"Story 52.1"* (2026-07-29). **D-6 re-verified exactly as recorded; not re-litigated.** |
| 5 | `python3` § 3 prefix enumeration (T2) | 2 + 13 + 4 + 14 + 1 + 122 + 1 = **157**, no overlap between groups. |
| 6 | **RED** — `npx vitest run tests/i18n.test.ts` with the new checks, allowlist deliberately absent | `PASS (4) FAIL (2)`. (i) identical-value check failed on real shipped content: `pl.catalog.image_viewer.counter is byte-identical to en.…`; (ii) viewer-name check failed on the actual defect: `pl.catalog.image_viewer.zoom_in and pl.catalog.image_viewer.trigger_label are both "Powiększ"`. |
| 7 | **GREEN** — after allowlist + the two value fixes | `PASS (6) FAIL (1)` → the check caught that aligning the plural shape made `categoryWithCount_one` en-identical; allowlisted with the loanword reason → `PASS (7) FAIL (0)`. |
| 8 | Non-vacuity mutations M1–M6 (T3; AC-4/AC-5/AC-1 were green on first run against unfixed content, so each was proved by a deliberate temporary mutation, applied and reverted one at a time) | M1 empty value → `pl.catalog.browse.allCatalog is empty`. M2 `TODO: translate` → `carries an untranslated marker`. M3 `{{name}}` only → `is interpolation-only while en.… carries prose`. M4 dropped `{{name}}` → `placeholders diverge … expected [] to deeply equal [ '{{name}}' ]`. M5 extra pl-only key → repo-wide parity assertion fires. M6 key added to **both** files → parity stays green and the scope check fires: `expected [ … ] to have a length of 157 but got 158`. Locale files restored byte-exact after each (`git diff` showed only the three intended lines). |
| 9 | `npm run typecheck` / `npm run lint` | `tsc -b` clean; `ESLint: No issues found` (`--max-warnings=0`). |
| 10 | `npx vitest run` (full) | **154 files / 1135 tests passed, 0 failed.** |
| 11 | `npx playwright test … image-viewer-zoom.spec.ts image-viewer-containment.spec.ts` (AC-7) | **PASS 100 · FAIL 0 · skipped 12**, 53.1 s. Standing suite green with the comment-only change. |
| 12 | `npx playwright test … browse-rail browse-sheet category-browse catalog-detail catalog-detail-categories catalog-card-carousel` (AC-9) | **PASS 60 · FAIL 0 · skipped 16.** |
| 13 | `npx playwright test … share-anonymous-with-signin share-member-enriched share-member-enriched-dismissed` (AC-9, the `/share` consumer surface) | **PASS 12 · FAIL 0.** |
| 14 | `git status --short -- apps/web/tests/visual/__snapshots__` | **Empty.** Zero PNG touched across all 172 visual assertions. No `baseline-reviewed:` line is owed. |
| 15 | AC-7 comment-prose proof (§ 9 command) | `git diff -U0` on both viewer specs, filtered to non-`//` lines → **empty**. Zero executable-line change in either file. |
| 16 | Determinism triple, `npx vitest run` ×3 | `154 passed (154)` / `1135 passed (1135)` — **identical all three runs**. Log: `.hermes/run-logs/vitest-determinism-54-1-counts-20260731_042606.log`. |
| 17 | `python3` key-count (T8, post-change) | `en 1048 · pl 1048 · sets equal True · both diffs empty` — equal to run 2, as AC-2 requires. |
| 18 | Ownership derivation (`git log --reverse` over `en.json`, added-key extraction per commit) | All **157** keys attributed, **0 unattributed**. Surfaced the § 3/V-9 correction recorded in § 12. |
| 19 | Liveness sweep excluding `*.test.*` (AC-8) | 99 quoted-direct + 48 plural-base + 10 template-literal = **157 live, 0 orphans**. |

### Completion Notes List

1. **The § 0 prediction held.** The audit is the deliverable; the remediation is **two Polish values on three lines**, `en.json` byte-unchanged. That is the `spec-47-1-i18n.md` shape the entry gate told me to expect, and a large diff here would have been the warning sign.
2. **AC-2 — the shipped parity gate was extended, never re-authored.** `apps/web/tests/i18n.test.ts:15-22` is byte-identical; the `flat()` helper and the `describe`/`it` it feeds are untouched. Everything new is a sibling `describe` below it, per D-1.
3. **RED was observed on real content, not manufactured.** Two of the five new checks failed against the unfixed tree on first run — the identical-value check and the viewer accessible-name check, the latter on the exact D-8 defect this story was chartered to close. The other three (AC-4 placeholder, AC-5 interpolation, and the 157-scope guard) were green on first run because the content was genuinely clean, so each was proved non-vacuous by a deliberate temporary mutation and reverted (debug log #8). Recording *which* were which is the point: three of these checks are regression guards, not defect finders, and saying so keeps the audit honest.
4. **The AC-3 check found a defect the audit did not anticipate — in my own fix.** Aligning the `categoryWithCount` plural shape (§ 13 ruling c) made `_one` byte-identical to English. That is the same `model` loanword coincidence `modules.admin.categories.model_count_one` already ships, so it was allowlisted with that reason rather than reverted. The gate working against the story's own remediation, on the first run after it, is the strongest evidence I have that it is not vacuous.
5. **⚠️ Attribution correction to § 3 and § 2 V-9 — recorded, not acted on.** Ownership was derived mechanically (debug log #18) rather than read off the story, and nine of the fourteen `catalog.image_viewer.*` keys — `trigger_label` among them — were introduced by **Story 22.3** (`812c7bd`, 2026-05-24), two months before Initiative 26, not by 53.2. **I did not narrow the scope on that basis.** V-11 removed `catalog.filters.openFilters`/`title` for predating Initiative 26, and the same date logic would remove these nine — but § 3 lists the family as in scope and V-5/D-5/AC-7 charter this story *by name* to close the `trigger_label` collision. An explicit charter outranks a date heuristic, and re-scoping a validated story mid-dev would be exactly the silent scope change § 5 forbids. Flagged here for the controller; the audited count stands at 157.
6. **AC-9 — the aria-label claim was proved empirically, not just cited.** V-12 argued from grep that `trigger_label` paints nothing; `categoryWithCount` turned out to be the same shape (`BrowseCategoryList.tsx:123`, `aria-label` only, visible text rendered by separate spans at `:133-147` — label `:133-144`, count `:145-147`; citation corrected 2026-07-31 by the second native code review). Both were then *tested*: 172 visual assertions across nine specs — the two viewer suites, six browse/detail suites and three `/share` suites — all green with **zero** snapshot churn. No baseline was regenerated and **no `baseline-reviewed:` line is owed on this commit.**
7. **AC-7 — both comments corrected, both suites green, zero executable change.** Each rationale block now states what was true (the collision), what changed (the value fix, quoted), and why the toolbar scoping *stays* (these specs assert on the toolbar's controls; an unscoped accessible-name lookup would widen if another surface ever shipped a same-named control). Neither is left asserting a collision that no longer exists. The § 9 prose-only proof is empty (debug log #15). **`image-viewer-zoom.spec.ts:21` was checked and is NOT stale** — it says the matchers below are the literal pl.json strings `Powiększ`/`Pomniejsz`/`Dopasuj`, and all three resolve `zoom_*` keys, none of which changed. **Judgement call, disclosed:** `image-viewer-zoom.spec.ts:16-18` still says containment "is not touched by this story"; its subject is 53.3, the story that wrote it, so it remains true and I left it rather than rewrite prose AC-7 did not scope.
8. **One file outside § 7's predicted set: `apps/web/src/modules/catalog/browse-i18n.test.ts`.** Its Story 51.1 check asserts every `catalog.browse.*` pl value differs from en, with no allowlist, so ruling (c) turned it red. Adding a `COINCIDENTAL_MATCHES` set — mirroring exactly what `categories-i18n.test.ts:50` already does for the identical coincidence — is the mechanical consequence D-4 explicitly permits ("plus the mechanical consequences in tests/specs"). No assertion was weakened: one key is exempted, by name, with the reason in the source. § 7 told dev to re-verify its list rather than trust it; this is the one addition.
9. **AC-8 — zero orphans, and the first sweep was wrong.** My initial pass searched all of `apps/web/src` and reported ten orphans; both errors were mine and both were corrected before any conclusion. It counted colocated `*.test.ts` files as consumers (a test is not a consumer), and it missed the ten keys `CurationQaPanel.tsx` builds by template literal. Re-run with tests excluded and template-literal patterns matched exactly: **157 live, 0 orphans, nothing deleted.** `catalog.filters.tags` (§ 2 V-13) was left untouched as instructed.
10. **AC-11 — two findings routed, neither absorbed.** (i) The out-of-scope half of ruling (d), `modules.admin.tagGroups.error_title`'s English contraction. (ii) A new one this story is the evidence for: the "pl must not equal en" rule now lives in **three** test files with three independent allowlists, and one legitimate value change in this story required updating **two** of them. Both are in `deferred-work.md` under "Deferred from: story 54.1 dev (2026-07-31)" with `status: OPEN`, evidence and a named owner. Neither is recorded as closed, and nothing already ledgered against 54.2 or the DN-4 follow-up was touched.
11. **Scope boundaries held.** Zero diff to `apps/web/src/ui/dialog.tsx`, `theme.css`, any `--color-*` token, any file under `apps/web/src/modules/**` *except* the `browse-i18n.test.ts` note above, `routes/share/$token.tsx`, `playwright.config.ts`, `api-stubs.ts`, `tests/visual/_test.ts`, every `__snapshots__/**/*.png`, and everything under `apps/api/`, `workers/` and `planning-artifacts/`. No focus trap, no contrast, no axe, no `toHaveScreenshot` threshold, no DN-4 work. `epic-53` untouched.
12. **`Block If` did not trigger.** No in-scope key was present in one locale file and absent from the other, at entry or at exit.
13. **Owed gates, controller-owned (T9 deliberately left unchecked — the story says "do not self-check").** `infra/scripts/check-all.sh` standalone with `tee` into `.hermes/run-logs/` (AC-10's 16/16 + `all green.` + exit 0); the **pytest** third of the `NFR26-DETERMINISM-1` triple (the vitest third is done and logged — no backend file changed this story); native `bmad-code-review`; independent Aider review via `laura-aider-review-diff`. Commit, ff-merge, push and deploy are the controller's.
14. **Epic flip.** `epic-54` moved `backlog` → `in-progress` at dev-story, per the § 17.1 deviation the Validate pass upheld (43.1/47.5 precedent).

### File List

| File | Change |
|---|---|
| `apps/web/src/locales/pl.json` | **modified** — 3 value lines: `catalog.image_viewer.trigger_label` → `"Otwórz na pełnym ekranie"`; `catalog.browse.categoryWithCount` → `"{{name}}, {{count}} modeli"`; `catalog.browse.categoryWithCount_one` → `"{{name}}, {{count}} model"`. No key added, removed or re-keyed. |
| `apps/web/src/locales/en.json` | **unchanged** — every defect was Polish-side, as § 7 allowed for. |
| `apps/web/tests/i18n.test.ts` | **modified** — extended with the § 3 scope list, the reasoned `IDENTICAL_BY_DESIGN` allowlist and **six** new `it` blocks (157-scope guard, en-identical, allowlist-honesty, placeholder/marker, interpolation multiset, viewer accessible-name uniqueness). Existing parity test byte-identical. *(Count corrected from "five" 2026-07-31 by the second native code review — the list that follows it always named six; `npx vitest run tests/i18n.test.ts` reports `7 passed` = 1 shipped parity test + 6 new.)* |
| `apps/web/src/modules/catalog/browse-i18n.test.ts` | **modified** — one `COINCIDENTAL_MATCHES` exemption + reason for `catalog.browse.categoryWithCount_one`. Mechanical consequence of ruling (c) per D-4; outside § 7's predicted set, disclosed in Completion Note 8. |
| `apps/web/tests/visual/image-viewer-zoom.spec.ts` | **modified — comment prose only** (AC-7). Zero executable-line change, proved by the § 9 command. |
| `apps/web/tests/visual/image-viewer-containment.spec.ts` | **modified — comment prose only** (AC-7). Standing suite; substance byte-identical, suite green. |
| `_bmad-output/implementation-artifacts/deferred-work.md` | **modified** — new section "Deferred from: story 54.1 dev (2026-07-31)", two entries, both `status: OPEN` (AC-11). *(Restated 2026-07-31 by the second native code review: this row described the DEV pass's snapshot. The shipped diff also carries a second new section, "Deferred from: code review of 54-1-i18n-parity-audit (2026-07-31)" — three entries from the first review plus a fourth added by the second. The earlier "Nothing else in the ledger touched" clause was true when written and false of the shipped diff; no pre-existing ledger entry was modified other than the two P-2/P-3/P-4 corrections inside 54.1's own dev entries.)* |
| `_bmad-output/implementation-artifacts/54-1-i18n-parity-audit.md` | **modified** — this file: § 12 audit table, § 13 rulings, § 14 Dev Agent Record, Tasks checkboxes, Status. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | **modified** — `epic-54` → `in-progress`, `last_updated` annotation. *(Story value restated 2026-07-31 by the second native code review: this row recorded the DEV pass's `review`. The first review's P-1 flipped it to `in-progress`; the second review's closeout sets it to `done`. The shipped value is what `sprint-status.yaml` itself carries, not this row.)* |

---

## 17. Disclosed deviations from the base workflow

1. **`epic-54` is deliberately left at `backlog`, not promoted to `in-progress` at create time.** The base `bmad-create-story` workflow promotes the epic when creating its first story. This repo's established precedent flips the epic at **`bmad-dev-story`**, not at create — applied at 43.1 and 47.5, and reviewed and **UPHELD** by the independent Validate pass on Story 49.1 (`sprint-status.yaml`, 49-1 entry: *"§17.2 deviation reviewed and UPHELD — flip at dev-story per 43.1/47.5 precedent; under open `G26-DEVGO` an in-progress epic with zero code would misreport state"*). `G26-DEVGO` is still open, so the same reasoning holds. Disclosed here, not silently applied.
2. ~~**`sprint-status.yaml`'s `last_updated` field was NOT updated.**~~ **CLOSED by the Validate pass.** The date value was already `2026-07-31` (the same day), so the load-bearing field was never wrong; its trailing annotation still described the 53.3 closeout and has been re-stamped for this story cycle. `development_status[54-1-i18n-parity-audit]` was already `ready-for-dev` from the create pass.
3. **No shell verification was possible in the authoring (create) session.** Every `Bash` call was refused by the permission layer, so no `git`, `grep`, `ls`, `pytest` or `vitest` output backed the file as first written. Every claim in § 2 and § 3 was sourced from a direct file read and cited with line numbers. **The Validate pass had shell access and re-measured all of it** — see § 18 for what held and what did not.
4. **Validate (`bmad-create-story:validate`) was deliberately not run in the same pass**, per the controller's bounded-run instruction. ✅ **It has since run** — 2026-07-31, fresh context, same baseline. Record in § 18.

---

## 18. Validation record — native `bmad-create-story` Validate (VS), 2026-07-31

**Run.** Repo-local Claude Opus 5, fresh context, `main` @ `c3db4aa`, **with** shell access (the create pass had none). Routing: session-start `bmad-help` → catalog row `[VS] bmad-create-story:validate` (`preceded-by: bmad-create-story:create`, `followed-by: bmad-dev-story`) → `checklist.md`. **Verdict: CONDITIONAL at entry → PASS after the corrections below were applied in place.** No product code, test, locale or snapshot file was touched by this pass. **NOT a human review and NOT an Ezop/Laura sign-off.**

**Re-measured and CONFIRMED (no change needed).** Baseline SHA and clean tree (V-10); the shipped parity gate at `i18n.test.ts:15-22` including the two-direction assertion at `:19-20` (V-1); flat JSON, 1048/1048 keys, sets equal, no nesting (V-2); all six § 3 prefix ranges and counts (V-3); every identical en/pl pair in V-4 read byte-for-byte; the `trigger_label`/`zoom_in` = `Powiększ` collision at `:389`/`:399` (V-5); all four terminology divergences (a)-(d) at `:292`/`:928`, `:303`/`:971`, `:294-298`/`:932-935`/`:838-841`, `:842`/`:931` (V-6); the 47.1 liveness gap verbatim in the ledger (V-7); **zero** i18n-class `status: OPEN` entry across the whole ledger (V-8); `epics.md:4417`, `prd.md:2262/2264/2265`, `architecture.md:3375/3376/3386`, `epics.md:4581-4595` all quoted accurately (V-9). Scope containment against 54.2 and the DN-4 follow-up re-checked against `epics.md:4593-4595` and the OPEN ledger entries — **no absorption**.

**Corrections applied (4 critical, 4 enhancements).**

| # | Class | Finding | Fix |
|---|---|---|---|
| VS-1 | 🚨 critical | AC-7 named **one** spec file. The collision rationale is written down in **two** — `image-viewer-containment.spec.ts:352-356` carries the same claim, and it is a **standing** suite (`architecture.md:3376`) that `image-viewer-zoom.spec.ts:16-18` tells a reader not to touch. Dev would have shipped a comment that lies. | AC-7 rewritten to cover both files with exact prose ranges, an explicit "comment prose only, standing suite stays green" constraint, and an Ask-First trigger for anything substantive. § 7 and T6 updated to match. |
| VS-2 | 🚨 critical | D-6 was left open for dev, but is mechanically answerable and **changes § 3**. | Resolved with `git log -S` + `git show`: `47e8407` (2026-05-10) introduced `openFilters` + `title` → **out of scope**; `3202b7c` (Story 52.1) introduced `openFiltersWithCount` → **in scope, owned by 52.1**. New § 2 **V-11**; D-6, § 3, T2 and § 9 rewritten. In-scope count 156 → **157**, measured. |
| VS-3 | 🚨 critical | AC-7 pointed at `image-viewer-zoom.spec.ts:74-77` as "the rationale". `:74-77` are the **locator constants**; the rationale prose is `:67-73`. Dev would have edited the wrong lines — or the right lines' meaning. | Every citation corrected (`zoom:67-73` + `:21`, `containment:352-356`; locators `:74-77` / `:357-360` explicitly left alone). |
| VS-4 | 🚨 critical | V-2 asserted the two files "line up line-for-line". **False** — `errors.not_found` / `errors.audit_log` are transposed at `:430`/`:431`. | V-2 rewritten with the measured exception and a "key by NAME, never by line index" warning. The transposition is out of scope and explicitly not 54.1's to fix. |
| VS-5 | ⚡ enhancement | AC-9 demanded dev *prove* the collision fix paints nothing, without supplying the evidence. | New § 2 **V-12**: `trigger_label` is `aria-label` at all four call sites (`ModelGallery.tsx:130,151`, `routes/share/$token.tsx:308,321`) and both specs open the viewer by `getByTestId`, not by accessible name. **No baseline may be regenerated for it.** Also surfaces the un-named fourth surface, `/share`. |
| VS-6 | ⚡ enhancement | AC-8's orphan sweep would have "discovered" `catalog.filters.tags` (`:278`, zero consumers) — already ledgered by the 47.1 review and out of § 3. | New § 2 **V-13** names it and routes it: recorded, not edited. |
| VS-7 | ⚡ enhancement | "≈156 keys" was an estimate carried into an AC that demands a measured number. | Counted with `python3`: 2+13+4+14+1+122+1 = **157**. § 3 and V-3 state it; AC-1 still requires dev to re-measure. |
| VS-8 | ⚡ enhancement | § 7's "asserted unchanged" list omitted `routes/share/$token.tsx` and the executable lines of the two viewer specs. | Both added. |

**Known cosmetic gap, accepted.** Section numbering jumps § 14 → § 17 (no § 15/§ 16). Renumbering would invalidate the `§17.1`/`§17.2` references already written into `sprint-status.yaml`; the churn is not worth it. Future appended records continue from § 18.

**Deviation § 17.1 (`epic-54` left at `backlog`) reviewed and UPHELD** — same reasoning the 49.1 Validate pass recorded: `G26-DEVGO` is still `🔓 open` (`architecture.md:3386`), and an `in-progress` epic with zero code would misreport state. The flip belongs to `bmad-dev-story`, per this repo's 43.1/47.5 precedent.

**Entry gate for dev is unchanged and still binding.** `ready-for-dev` is the BMAD artifact status. Dev starts only after the controller confirms this story under `G26-DEVGO`.
