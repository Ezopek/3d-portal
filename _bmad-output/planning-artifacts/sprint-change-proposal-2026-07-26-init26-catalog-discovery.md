# Sprint Change Proposal — Initiative 26: Catalog Discovery (browse categories + tag-aware search + mobile gallery maturity)

**Date:** 2026-07-26
**Workflow:** `bmad-correct-course` (BMad Method 6.10, native; routed via `bmad-help` → `_bmad/_config/bmad-help.csv` row `BMad Method,bmad-correct-course,Correct Course,CC,…,anytime,…,planning_artifacts,change proposal`)
**Author:** Claude Opus 5 (agent session), working from the operator-approved input packet `/tmp/3d-portal-init26-correct-course-input.md`
**Operator:** Ezop (Michał) · **Controller:** Laura
**Mode:** Batch (non-interactive controller session; the input packet delegates safe defaults and states that no further operator questions are needed absent a material contradiction — §"No additional operator questions are needed…")
**Branch:** `docs/init26-catalog-discovery-correct-course`
**Change class:** MAJOR — introduces a new first-class browse entity, a new schema migration, a search-semantics change on a shipped endpoint, and a catalog IA cutover.

> **Provenance / sign-off honesty (binding).** The *product direction* in this proposal is operator-approved: it is a faithful transcription of the input packet, which is itself marked "operator-approved direction". **The text of this document was reviewed and ratified by Laura (controller) on 2026-07-26**, after reading the SCP, PRD, architecture and epics artifacts under the operator-approved packet and the standing `działaj` delegation; that review produced the eight corrections recorded in §0a. **No Ezop sign-off is recorded here, and none may be inferred** — the operator approved the product direction via the packet, not this document's text. Remaining gates are enumerated in §8. This follows [[baseline-review-provenance-honesty]] and the standing epic:45/epic:46 GOVERNANCE action item (agent-forged reviewer sign-offs — two prior recurrences).

---

## 0a. Controller review iteration — 2026-07-26 (Laura)

Applied consistently across this SCP, the readiness report, `prd.md`, `architecture.md`, `epics.md` and `sprint-status.yaml`.

1. **E49 stories 49.1 + 49.2 merged into one atomic story.** ORM entities and their Alembic migration are **not independently mergeable**: `test_orm_migration_parity.py` (shipped in Story 47.5) asserts `compare_metadata` is an empty diff between the migration-upgraded scratch DB and `SQLModel.metadata`, so an entities-only branch and a migration-only branch each fail `check-all` 16/16 alone. The remaining **uncommitted** E49 stories are renumbered coherently (former 49.3→49.2, 49.4→49.3, 49.5→49.4, 49.6→49.5). No shipped identifier is touched — every renumbered key was `backlog` and had never been created, validated, or implemented. Each story now preserves a single-story branch that can pass `check-all` on its own.
2. **Replace-set last-writer-wins: the "no lost-update ambiguity" claim is RETRACTED as false.** LWW **does** permit a lost update. Accepted for the current single-admin deployment as **explicit, auditable LWW**, justified by the per-write audit row rather than by absence of the race; `revision`/ETag optimistic concurrency is a **named future trigger**, not present behaviour. Full text in §6, Decision AY.
3. **Quality NFRs are owned per story at its own merge gate.** Every UI story in E50–E53 ships its own i18n keys, component-level a11y assertions, and targeted unit/visual coverage — a surface shipped without them cannot pass its own gate. **E54.1/E54.2 recast** as the final cross-surface parity/a11y/visual **audit + remediation** (renamed `54-1-i18n-parity-audit`, `54-2-a11y-and-visual-audit`), never the first place proof appears. NFR mapping updated in `epics.md` and `prd.md`.
4. **Story 53.1 scores THREE options**, not four: YARL+Zoom, PhotoSwipe 5.4.x, and extend-the-in-house-viewer. The previous "four" was an internal miscount of the same three.
5. **Story 50.3 now states how `+tag` pill group labels are obtained.** `TagRead` carries `group_id` + `group_position` only, with no embedded label (Decision AW / D-SHAPE-1); the label is resolved from the **already-loaded** `useTagGroups()` map, rendered without a suffix when unavailable, with the **smallest additive contract extension** permitted at story-creation only if current contracts genuinely cannot supply it — **never** a duplicate suggestion endpoint and never a per-suggestion N+1.
6. **NFR26-PERF-1 made measurable without inventing wall-clock numbers.** The assertion is **query count**: constant across page size and across the number of matching tags/models (no N+1), proven by an **equal-result-count fixture-size comparison** plus distinct-`total` correctness. Precedent: Story 42.2's "constant-query no-N+1 proven".
7. **Gate decisions recorded (Laura/controller only).** `G26-SCP-RATIFY` **closed**; `G26-ROUTE-PATH` **closed** — re-use of `/api/categories` and the internal `BrowseCategory*` naming are ratified; `G26-UXGATE` **decided** — a **targeted** `bmad-ux` pass runs before Story 50.3, Epic 51 and Epic 52 (E49 and Story 53.1 are not blocked); `G26-CAT-SET` stays **open but routed** into that same UX/taxonomy pass, before Story 49.2. **No second operator question is raised** for the already-approved product direction, and **no Ezop sign-off is fabricated**. Implementation authorization stays truthful: planning proceeds; code on any story starts only after `bmad-create-story` + `:validate` and the controller confirming that specific ready story under the user's standing initiative authorization.
8. **Native readiness re-run** against the corrected artifacts; §9a and `implementation-readiness-report-2026-07-26.md` updated truthfully.

---

## 0. Checklist execution record (`checklist.md`)

| Item | Status | Where resolved |
|---|---|---|
| 1.1 Triggering story | [x] Done | §1.1 — no *failing* story; trigger is post-Initiative-25 hands-on operation + a shipped field bug (E48.1) |
| 1.2 Core problem | [x] Done | §1.2 — issue type: **new requirement emerged from stakeholder (owner) hands-on use** + **technical limitation discovered in production** |
| 1.3 Evidence | [x] Done | §1.3 — code-verified evidence table |
| 2.1 Current epic completable? | [N/A] | Initiative 25 (E41–E47) is **fully closed** (all epics `done`, retro `done` 2026-07-23). No in-flight epic to re-scope. |
| 2.2 Epic-level changes | [x] Done | §4 — **Add** new epics; nothing modified, nothing rolled back |
| 2.3 Remaining planned epics | [x] Done | §2.4 — there are none. `epic-47-retrospective` explicitly records: *"No next epic (Epic 48 / Initiative 26) is committed in any planning artifact."* |
| 2.4 Invalidated / new epics | [x] Done | §4 — E48 reconciled (shipped), E49–E54 new |
| 2.5 Epic order / priority | [x] Done | §4.1 — additive-first ordering, derived from the E41→E47 lesson |
| 3.1 PRD conflicts | [!] Action-needed → resolved | §3.1 + §5.1 (PRD edit) |
| 3.2 Architecture conflicts | [!] Action-needed → resolved | §3.2 + §5.2 (Decisions AX–BA) |
| 3.3 UI/UX conflicts | [!] Action-needed → **open gate G26-UXGATE** | §3.3, §8 |
| 3.4 Other artifacts | [x] Done | §3.4 — ops probes, live docs, runbook, i18n, visual suite, `sprint-status.yaml` |
| 4.1 Option 1 Direct Adjustment | [x] Viable — **selected (hybrid)** | §4 |
| 4.2 Option 2 Rollback | [x] Not viable — evaluated and rejected | §4 |
| 4.3 Option 3 MVP Review | [x] Viable but not selected | §4 |
| 4.4 Recommended path | [x] Done | §4 |
| 5.1–5.5 Proposal components | [x] Done | §1–§7 |
| 6.1 Checklist completion | [x] Done | this table |
| 6.2 Proposal accuracy | [x] Done | every code claim in §1.3/§6 carries a `file:line` anchor verified at HEAD `da87e71` |
| 6.3 Explicit user approval | [x] Done | §8 G26-SCP-RATIFY **closed** — direction approved by the input packet; document text ratified by Laura (controller) 2026-07-26, producing the §0a corrections. No Ezop sign-off implied. |
| 6.4 `sprint-status.yaml` update | [x] Done | §5.4 — new epics seeded at `backlog`; E48 reconciled to `done` |
| 6.5 Next steps / handoff | [x] Done | §7 |

---

## 1. Issue Summary

### 1.1 Trigger

Two independent signals, both from operating the shipped product, not from a failed story:

1. **Browse/discovery overload (Scope B + C).** Initiative 25 (E41–E47, closed 2026-07-23) replaced the mandatory single-category taxonomy with facet tags and put the **full facet taxonomy into the left navigation** (`FacetSidebar`, Story 44.1). Hands-on use shows that a complete facet taxonomy is a poor *navigation* surface: it answers "what exact properties should it have?" but the user arrives asking "what kind of thing do I want to browse?". Compounding this, free-text search still reads only three columns and cannot find a model through its own tags.
2. **Mobile fullscreen gallery (Scope A).** A field bug: on a phone, opening a wide image fullscreen rendered the dialog displaced past the right viewport edge with the close control outside the visual viewport — the user was trapped. This was fixed as a focused quickfix and is **already shipped** (see §1.4).

Neither signal invalidates Initiative 25. Facet tags remain correct for *filtering*; the defect is that filtering was made to do navigation's job.

### 1.2 Core problem statement

> The catalog has one classification vocabulary (facet tags) doing two jobs it cannot do at once: **navigation** ("show me lamps") and **refinement** ("…with a threaded M10 mount, in PETG"). Free-text search compounds this by ignoring the tag vocabulary entirely, so the one input a user reaches for first cannot reach the data the taxonomy holds. Separately, the fullscreen image viewer has no zoom/pan, so a detailed or panoramic model photo cannot actually be inspected on a phone.

**Issue type (checklist 1.2):** *New requirement emerged from stakeholders* (primary — owner hands-on decision, 2026-07-26) plus *Technical limitation discovered during implementation/production* (secondary — the viewer containment defect, already remediated).

### 1.3 Evidence (code-verified at HEAD `da87e71`)

| # | Claim | Evidence |
|---|---|---|
| E-1 | Free-text `q` matches only `name_en` / `name_pl` / `slug`; tag names are unreachable by search. | `apps/api/app/modules/sot/service.py:258-266` |
| E-2 | A tag-name search endpoint **already exists** and is reusable — `GET /api/tags?q=` matches `slug`/`name_en`/`name_pl`, case-insensitive substring, `limit` 1–200, optional `with_counts`. | `sot/service.py:82-107`; `sot/router.py:46-75` |
| E-3 | The facet taxonomy is the left navigation. | `apps/web/src/modules/catalog/components/FacetSidebar.tsx` (Story 44.1, replaced `CategoryTreeSidebar`) |
| E-4 | The `+tag` affordance is a small outline button inside the filter ribbon, visually and semantically adjacent to the plain search input, with no distinct suggestion surface. | `FilterRibbon.tsx:67-72` (search `Input`), `:99-113` (`+tag` toggle button) |
| E-5 | URL state already carries `q`, `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `sort`, `page` as independent, validated layers — the new `category` scope has a working precedent to extend. | `apps/web/src/routes/catalog/index.tsx:36-103` |
| E-6 | The old `Category` entity, `Model.category_id`, the `category` table and the whole category API surface are **gone**. Migration head is `0019_drop_category`, forward-only, `downgrade()` raises. | `apps/api/migrations/versions/0019_drop_category.py:29-43`; `_entities.py` contains no `Category`; no `categor` hits in `apps/api/app/modules/sot`, `apps/web/src` (only unrelated slicer `reason_category` / material-category strings) |
| E-7 | `model_tag` is the exact structural precedent for the new M:N join: composite PK, `model_id` `CASCADE`, `tag_id` `RESTRICT`, plus a reverse-direction index. | `_entities.py:117-127` |
| E-8 | `GET /api/models`, `GET /api/tags`, `GET /api/tag-groups` are authenticated default-deny, outside `_PUBLIC_ROUTES`. Only health/auth/share are public. | `apps/api/app/main.py:50-61`; architecture.md Decision AW "Default-deny auth posture" |
| E-9 | The retired `/api/categories` path has **zero** live consumers and no live assertion depends on it 404-ing: `infra/scripts/cutover-smoke.sh:397-405` was re-pointed to `/api/tags` and only *mentions* the retirement in a comment. | `infra/scripts/cutover-smoke.sh:397-405` |
| E-10 | Live docs assert the category surface is retired, in prose that would become false if a new `/api/categories` shipped without a docs edit. | `docs/operations.md:426, 463-464, 613-614` |
| E-11 | The E48.1 quickfix is on `main`, with an honest spec that explicitly defers pinch/pan/`Viewer3DModal` residual risk to Initiative 26. | commit `da87e71`; `_bmad-output/implementation-artifacts/spec-e48-1-mobile-fullscreen-containment.md:24, 83` |
| E-12 | No planning artifact commits any epic after 47. | `sprint-status.yaml` `epic-47-retrospective` comment: *"No next epic (Epic 48 / Initiative 26) is committed in any planning artifact."* |

### 1.4 Current-state reconciliation — E48.1 is DONE (preserve, do not re-plan)

**Fact:** the Scope A quickfix shipped ahead of this planning pass.

- Commit `da87e71` — `fix(web): contain mobile fullscreen image viewer`, merged to `main`, **deployed**.
- Spec `_bmad-output/implementation-artifacts/spec-e48-1-mobile-fullscreen-containment.md`, `status: done`, `review_loop_iteration: 2`.
- Gates recorded in the spec's Verification table: `infra/scripts/check-all.sh` **16/16 green**; `npm run test` 785/785; `npm run test:visual` 536 passed / 32 expected skips; native BMAD re-review **APPROVE**; independent repo-aware Aider review **APPROVE**.
- Root cause measured and documented (`left: 50%` resolving against the *layout* viewport while `w-[98vw]` resolves against the *visual* viewport); the operator's own `min-w-0` hypothesis was tested and **recorded as disproved rather than silently dropped**; the planning claim "all four baselines unchanged" was **corrected against the measured result** rather than papered over.

**Treatment in this proposal — three binding rules:**
1. **Preserve as delivered.** E48.1 is recorded as **Epic 48, Story 48.1, `done`**. Its scope is not re-opened, re-designed, or re-implemented by any Initiative 26 story.
2. **Do not renumber.** The identifier `E48.1` is already written into a merged commit's spec artifact. Renumbering it to fit a tidier plan would falsify shipped history. Initiative 26's *planned* epics therefore start at **E49**.
3. **Keep the full gesture feature separate.** The mature lightbox (pinch/pan/double-tap/visible zoom controls) is **E53**, a distinct epic with its own adoption decision. The quickfix's own `Never:` boundary already forbade gestures and a lightbox dependency; E53 does not amend E48.1, it supersedes its capability ceiling with new work on top.

**Governance delta this exposes (must be fixed by this proposal):** E48.1 was executed as a direct spec → dev → review cycle **without** an `epic-48` / `48-1-*` key in `sprint-status.yaml` and without an entry in `epics.md`. `sprint-status.yaml` therefore currently under-reports shipped work. §5.4 corrects this truthfully, including an explicit note that 48.1 did not pass through `bmad-sprint-planning` / `bmad-create-story`.

---

## 2. Impact Analysis

### 2.1 What Initiative 25 retired, and what this initiative does *not* undo

This is the single most important truthfulness boundary in this proposal.

| Retired by Initiative 25 (stays retired, forever) | Introduced by Initiative 26 (new design) |
|---|---|
| `Model.category_id` — a **mandatory, single, NOT NULL** FK | **No column on `model`.** Membership lives only in a M:N join. |
| `category` table — self-referential tree with `RESTRICT` self-FK, `uq_category_parent_slug`, `uq_category_root_slug` | A new, differently-named physical table (§6, Decision AX) with a *nullable* `parent_id`, product-capped at depth 2 |
| The proposition "every model has exactly one category" | "A model has **0..n** categories; zero is valid and the model stays public/visible" |
| `GET /api/categories` returning `CategoryTree` (recursive tree) | `GET /api/categories` returning a **flat curated browse list with counts** (§6, Decision AY) |
| Deep drill-down navigation | Flat MVP browse, ~6–10 broad entry points |
| ORM `class Category`, schemas `CategoryNode`/`CategoryTree`/`CategoryCreate`/`CategoryPatch`/`CategorySummary`, hook `useCategoriesTree`, FE types `CategoryNode`/`CategoryTree` | **None of those identifiers are resurrected.** New code uses `BrowseCategory*` identifiers (§6, Decision AX rationale). |

**Nothing in Initiative 26 restores `Model.category_id`, the old tree semantics, or mandatory categorization.** Migration `0019_drop_category` stays forward-only and is never reverted. Every historical statement in `prd.md`/`architecture.md`/`epics.md`/`sprint-status.yaml` about the *old* category retirement remains true as written, and this proposal adds a forward-pointing note rather than editing history.

Second boundary, from the packet's tag-group decision: **`Tag.group_id` stays a single nullable FK.** No Tag↔TagGroup M:N is created. Null stays the curation-queue state and becomes visible admin hygiene (E52).

### 2.2 Epic impact

- **E41–E47 (Initiative 25): no change.** All `done`, retro `done`. Nothing is re-opened, re-scoped, or rolled back. The historical superseded keys `42-3`, `42-5`, `47-4` stay `backlog`/superseded exactly as recorded.
- **E48: reconciled, not created-as-new.** Contains exactly Story 48.1 (`done`, shipped `da87e71`). Retroactively adopted into Initiative 26 as its Scope-A phase-1 delivery.
- **E49–E54: new.** Six epics, additive-first (§4.1).
- **No epic is removed or deferred.**

### 2.3 Story impact

No existing story's scope changes. No completed story is rolled back. Two shipped stories are *extended* by new stories rather than modified:

- Story 44.1 (`FacetSidebar`) — E51 changes its **role** (navigation → refinement inside the Filters surface). The component is not deleted by the plan; E51.1/E52.1 decide whether it is relocated or re-rendered, at story-creation time against then-current code.
- Story 42.1 (`GET /api/models` facet filtering) — E49.3/E49.4 **add** `category` scope and tag-aware `q` to it. The AND-between-groups / OR-within-group semantics and `tag_match` are **unchanged**, and category scope is deliberately **not** folded into `tag_match` (packet §Browse UX).

### 2.4 Artifact conflicts

| Artifact | Conflict | Resolution |
|---|---|---|
| `prd.md` | Has no Initiative 26 section. The historical supersede note ("Categories are retired by Initiative 25") is true for the *old* entity but would be read as forbidding the new one. | Append § Initiative 26 with FR26/NFR26 blocks; append a **forward pointer** under the Initiative 25 supersede note. Do **not** rewrite the historical note. (§5.1) |
| `architecture.md` | Decisions AU/AV/AW describe the category removal as terminal. No decision covers a browse entity, the new join, category-scoped listing, tag-aware search, or a lightbox dependency. | Append § Initiative 26 with **Decisions AX, AY, AZ, BA**; append a forward pointer to Decision AW. (§5.2) |
| `epics.md` | Ends at Initiative 25 / E47. E48 (shipped) is absent. | Append § Initiative 26 with E48 (done) + E49–E54 (backlog). (§5.3) |
| `sprint-status.yaml` | **Under-reports shipped work** — no `epic-48` / `48-1-*` key despite `da87e71` being merged and deployed. | Add the E48 keys as `done` with honest provenance; seed E49–E54 + stories at `backlog` (checklist 6.4). (§5.4) |
| UX / design SoT | `docs/design/HANDOFF-tagi-fasetowe.md` is the visual SoT for the facet surfaces. There is **no** design artifact for browse categories, the suggestion dropdown, or the mature lightbox. | **Open gate G26-UXGATE** (§8) — operator decides whether `bmad-ux` runs before E51. Mirrors Initiative 25's G-UXGATE. |
| `infra/scripts/cutover-smoke.sh` | Comments assert `/api/categories` is retired; the probe itself is already re-pointed to `/api/tags` (E-9), so **no gate breaks**. | Comment accuracy pass in E54.3. Explicitly surfaced because the epic:47 CUTOVER-CHECKLIST action item requires scanning operational probes, not just `apps/`. |
| `docs/operations.md`, `docs/architecture.md`, `docs/agents-add-model-runbook.md` | Live prose states the category surface is retired (E-10). A new `/api/categories` makes that prose misleading. | E54.3 rewrites those passages to distinguish *retired mandatory single-category taxonomy* from *new independent browse categories*, and adds the agent-facing contract for category assignment. |
| i18n | New keys needed for browse nav, scope chip, suggestions, admin curation. | E54.1, en+pl parity (NFR26-I18N-1). |
| Visual suite | New surfaces need pl-PL baselines per [[web-visual-tests-render-pl-pl]]; overlapping `/api/*` route mocks must fold into one handler. | E54.2. |
| Deploy / CI | No pipeline change. Migration `0020` is **additive and reversible**, so the destructive-deploy protocol that governed `0019` does **not** apply. | §6 Decision AX; §8 gate G26-MIGRATE. |

### 2.5 Technical impact

- **Schema:** one new table + one new join table, both additive; migration `0020`, `down_revision = "0019_drop_category"`, **with a working `downgrade()`** (deliberate contrast with `0018`/`0019` — nothing is destroyed, so forward-only would be unjustified ceremony).
- **API:** additive params on `GET /api/models`; a new read surface; a new admin CRUD surface; one additive field on `ModelDetail`. **No breaking change to any shipped contract** in E49.
- **Search:** the `q` predicate gains an `EXISTS`/`IN`-subquery membership branch. The join-based alternative would inflate `total` and duplicate rows; the existing `tag_ids` implementation (`service.py:216-254`) already establishes the subquery pattern that avoids it, and `total` is computed from `base.subquery()` **before** pagination (`service.py:279-280`) — so the correctness requirement is met by extending the established pattern, not by inventing one.
- **Frontend:** one new route (`/categories/$slug` → `routeTree` regeneration required, [[reference_web_routetree_regen]]), new URL state layer, navigation IA change, a new suggestion surface, and — in E53 only — a possible new runtime dependency.
- **Risk concentration:** E53 is the only epic that may add a third-party dependency, and E51 is the only epic that changes what the user sees first on `/catalog`.

---

## 3. Artifact Conflict Detail

### 3.1 PRD

No FR/NFR currently covers: an independent browse entity, M:N model↔category membership, tag-aware free-text matching, structured inline suggestions, a browse-vs-filter IA split, category governance criteria, or gesture-capable image viewing. The Initiative 25 FR block (FR25-*) stays valid and untouched. **Action:** additive FR26/NFR26 block (§5.1). MVP is **not** reduced.

### 3.2 Architecture

Decisions AU (data model), AV (migration), AW (API contract) describe a world where categories are gone. They are historically accurate and must not be edited. What is missing: the browse entity's shape and FK posture, its migration posture, the category-scope + tag-aware-search contract, the admin/governance contract, and the lightbox adoption decision. **Action:** Decisions AX/AY/AZ/BA (§5.2, full text in §6).

### 3.3 UI/UX

`docs/design/HANDOFF-tagi-fasetowe.md` covers facet surfaces only. Initiative 26 introduces surfaces with **no visual SoT**: desktop left browse nav, mobile Browse surface, category scope chip + "Search entire catalog" affordance, the query-vs-`+tag` suggestion dropdown, the `Filters (n)` drawer, the admin category screen, and the mature lightbox chrome. The packet supplies strong, research-grounded *constraints* (≤6–8 suggestions, no internal scrollbar, ≤2–4 promoted filter groups, visually distinct suggestion classes, ≥44×44 targets) but not mockups. **This is an unresolved gate, not a decision this workflow may make silently** → **G26-UXGATE** (§8).

Accessibility is treated as a first-class constraint, not a polish pass: WCAG 2.2 Pointer Gestures (2.5.1), Dragging Movements (2.5.7) and Target Size Minimum (2.5.8) are cited by the packet and are why E53 requires *visible* Zoom In/Out/Reset controls as single-pointer alternatives to pinch, and why the close control has a hard ≥44×44 requirement.

### 3.4 Other artifacts

Covered in the §2.4 table. The two entries that exist **because of** the epic:47 retrospective's CUTOVER-CHECKLIST action item (scan operational probes and live docs, not just application source) are `infra/scripts/cutover-smoke.sh` and `docs/operations.md` — both were checked in this pass (E-9, E-10) rather than assumed.

---

## 4. Recommended Path Forward

**Selected: Option 1 — Direct Adjustment (additive), executed as a new initiative.** Formally a hybrid: Option 1 for E49–E54 plus a *retroactive reconciliation* of already-shipped E48.

| Option | Verdict | Reasoning |
|---|---|---|
| **1 — Direct adjustment / add stories** | ✅ **Selected** | Nothing shipped is wrong. Facet tags are correct for refinement; the gap is a missing *navigation* layer, a missing search predicate, and a missing gesture capability. All three are pure additions. Effort: **High** (six epics). Risk: **Low-Medium** — every backend change is additive and reversible; the only genuinely user-visible cutover is the browse IA (E51), which lands after its data and state foundations. |
| **2 — Rollback** | ❌ Not viable | Would mean reverting Initiative 25 — five epics, a deployed forward-only destructive migration whose `downgrade()` raises (`0019:40-43`), and 43 category rows + 130 assignments already permanently deleted under a recorded destructive-go. The rollback is **technically impossible via Alembic** and would destroy correct work to solve a problem that is additive. Effort: Extreme. Risk: Extreme. |
| **3 — MVP review / scope reduction** | ⚠️ Viable, not selected | The MVP is not over-scoped; it is under-served by one missing layer. Reducing scope further would leave the observed navigation defect in place. *Partially adopted anyway*: hierarchy is capped at flat-for-MVP (schema-ready for depth 2, no third level ever), promoted filter groups capped at 2–4, and one active category scope at a time — these are deliberate MVP reductions carried from the packet's research findings. |

### 4.1 Sequencing rationale (the E41→E47 lesson, applied)

Initiative 25's most expensive recurring defect — flagged **three times** (E42, E43/E44, E47) and still an open standing action item — was **stale dependency preconditions written into epic sketches at decomposition time**, each time caught only by the `bmad-create-story` spec-authoring audit. Two structural countermeasures are built into this decomposition:

1. **Additive-first, cutover-last.** Every backend and data change (E49) is additive and reversible and lands before any UI depends on it. The frontend data/state layer (E50) is additive and coexists with today's surfaces. Only E51 changes what the user sees first, and only after E49+E50 are on `main`. There is **no destructive migration and no endpoint retirement anywhere in Initiative 26**, so the compatibility-bridge discipline that E41–E47 needed is not required — the whole initiative is a bridge.
2. **Every stated precondition in §9 is marked `VERIFY-AT-CREATE-STORY`.** Per the epic:47 action item, no sketch in this proposal asserts "consumer X is already gone" or "Y is already migrated" as settled fact. Where a story depends on the state of shipped code, the sketch names the file and requires a **fresh repo-wide trace at story-creation time**, not a carried-forward claim.

---

## 5. Detailed Change Proposals

### 5.1 `prd.md` — APPEND § Initiative 26 (no existing text rewritten)

New FRs (full text lands in the PRD edit):

- **FR26-CAT-1 — Independent curated browse categories.** A `Category` is a first-class, admin-curated browse entity with a stable slug, bilingual labels, optional descriptions, and an explicit `position`. It is **not** a `TagGroup`, is **not** generated from tag data, and is governed separately. *Verifiable:* an admin creates a category with no tag-side change; `GET /api/categories` returns it; `GET /api/tag-groups` is byte-unchanged.
- **FR26-CAT-2 — Many-to-many membership, zero-valid.** Model↔Category is M:N. A model with **zero** categories is DB-valid and remains public/visible everywhere; only the admin surface flags it as `Uncategorized / needs curation`. `Model.category_id` is never reintroduced. *Verifiable:* a zero-category model appears in `GET /api/models` and on its detail page; admin lists it in the curation queue.
- **FR26-CAT-3 — Curation norm, advisory only.** 1–3 categories per model is a *warning-level* admin norm. There is **no** hard DB maximum and no enforcement that blocks a write. *Verifiable:* assigning 5 categories succeeds and produces a warning, not a 4xx.
- **FR26-CAT-4 — Hierarchy: flat MVP, depth-2 ceiling.** Browse UI is flat with ~6–10 broad categories. Schema may carry a nullable `parent_id`; product maximum depth is **2** (root + child), exactly one parent per category, never a DAG. Child-category UI ships only when real catalog distribution demonstrates the need. *Verifiable:* attempting a depth-3 assignment is rejected; MVP renders no child level.
- **FR26-SEARCH-1 — Tag-aware free-text search.** `GET /api/models?q=` additionally matches models whose assigned tags contain `q` in `Tag.name_pl` or `Tag.name_en` (case-insensitive substring), preserving correct `total`, pagination, soft-delete filtering, and combination with category scope and `tag_ids`/`tag_match`, **without row duplication or count inflation**. *Verifiable:* `q=kabel` returns both name-matching models and models tagged `Kabel`/`Cable`; `total` equals the distinct model count; a model matching on both name and tag appears exactly once.
- **FR26-SEARCH-2 — Inline structured suggestions with distinct semantics.** Typed text stays ordinary `q`; **Enter never silently converts text into a tag.** Matching tags (PL+EN) render as visually distinct pills (e.g. `+ Kabel · Zastosowanie`); selecting one stores the canonical `tag_id`, deduplicated by ID across bilingual labels, rendering the active-locale label plus an optional subtle matched alias. Combined list is capped at **6–8** items on mobile and desktop, with no internal scrollbar. The plain-search action and the `+tag` action have distinct semantics, appearance, and accessible names. *Verifiable:* Enter with a tag-matching query performs a text search; the `+tag` pill is separately labelled and reachable; the list never exceeds 8 items; a tag matching in both languages appears once.
- **FR26-BROWSE-1 — Browse navigation shows categories, not the taxonomy.** Desktop left navigation lists only broad categories with optional counts. Mobile gets a separate Browse surface. Facets/tags move into a `Filters (n)` drawer; at most 2–4 promoted groups may be surfaced outside it, and full tag search stays inside it. *Verifiable:* the default `/catalog` left rail renders categories only; every tag group remains reachable within ≤1 interaction from `Filters`.
- **FR26-BROWSE-2 — Category is a browse scope, not a filter.** The active category renders as a **scope** above results (chip), never as another checkbox, and is **excluded** from the `Filters (n)` count. Public MVP allows **one** active category scope at a time; a model may appear under many category pages. Canonical URL `/categories/{stable-slug}`; `q`/`tag_ids`/`tag_match`/`sort` stay query params. Search started inside a category stays scoped by default, with a visible chip and a one-click **"Search entire catalog"** escape. *Verifiable:* the `Filters (n)` badge does not change when a category is active; the escape control clears only the scope.
- **FR26-BROWSE-3 — Facet semantics unchanged.** OR within one `TagGroup`, AND between `TagGroup`s, `tag_match` as the user override. Category scope is **never** mixed into `tag_match`. *Verifiable:* the shipped 42.1 semantics tests still pass unmodified with a category scope applied.
- **FR26-ADMIN-1 — Category governance surface.** Admin CRUD, reorder, and **replace-set** assignment of a model's categories, with audit rows on every write. Delete is blocked while assignments exist, unless an explicit, audited detach is requested. *Verifiable:* deleting a used category without the detach flag returns a conflict, never a silent cascade.
- **FR26-ADMIN-2 — Curation QA surfaces.** Admin QA surfaces models with zero or unusually many categories, empty/tiny categories, categories behaving like narrow tags, confusing Category/Tag label overlap, and ungrouped user-facing tags. No automatic synchronization or membership inference from tags in MVP; any suggestion is advisory only.
- **FR26-GOV-1 — Category admission criteria.** Every category carries a one-sentence inclusion criterion, positive and boundary examples, bilingual labels, a stable slug, and evidence it is a useful entry point for **multiple** models. Similar Category/Tag labels are allowed only with an explicit recorded semantic distinction.
- **FR26-VIEW-1 — Mature mobile image viewing.** The fullscreen viewer supports pinch zoom, pan, double-tap, and **visible Zoom In / Zoom Out / Reset controls** as single-pointer alternatives; a stable toolbar outside the transform layer; body scroll lock with restoration; focus trap, Escape, and return focus; safe-area and dynamic-viewport handling; and explicit swipe-vs-pan conflict rules. *Verifiable:* the E53 test contract (§9, Story 53.3) passes, including physical-Android smoke.

New NFRs: **NFR26-I18N-1** (en+pl parity for every new key), **NFR26-A11Y-1** (WCAG 2.2 SC 2.5.1 / 2.5.7 / 2.5.8 — no gesture-only path, no drag-only path, ≥44×44 targets), **NFR26-DARKMODE-1** (token-only, light+dark, no color literals — reuse), **NFR26-VISUAL-1** (pl-PL Playwright baselines for every new surface; consolidate overlapping `/api/*` route mocks), **NFR26-DETERMINISM-1** (3× identical pytest+vitest pass counts before merge — reuse), **NFR26-SCHEMA-ADDITIVE-1** (migration `0020` additive **and reversible**; no destructive DDL anywhere in this initiative), **NFR26-PERF-1** (tag-aware `q` must not regress list latency materially and must not inflate `total`; membership predicate, not a row-multiplying join).

Out of scope (intentional, with named triggers): automatic category inference from tags; multi-category public scope; a third hierarchy level; a new search backend/engine; fuzzy or typo-tolerant matching; restoring anything from the retired taxonomy; changing `Tag.group_id` to M:N; migrating `Viewer3DModal` or other `DialogContent` consumers to the new lightbox (E48.1 residual — triggered only by a reported defect or an explicit story).

### 5.2 `architecture.md` — APPEND § Initiative 26 (Decisions AX / AY / AZ / BA)

Full decision text in **§6**. A short forward pointer is appended to Decision AW stating that the *new* browse category is a different entity from the retired one, and naming Decision AX as its owner.

### 5.3 `epics.md` — APPEND § Initiative 26

E48 (done, reconciled) + E49–E54 (backlog). Full epic/story sketches in **§9**.

### 5.4 `sprint-status.yaml` — reconcile E48, seed E49–E54 at `backlog`

```yaml
epic-48: done          # shipped quickfix, reconciled retroactively
48-1-mobile-fullscreen-containment: done
epic-49 … epic-54: backlog
49-1 … 54-3: backlog
```

Each key carries an honest provenance comment. The E48 comment states explicitly that Story 48.1 was executed via a direct spec → dev → review cycle and **did not** pass through `bmad-sprint-planning` or `bmad-create-story`, and that its keys are being added retroactively by this correct-course to stop `sprint-status.yaml` under-reporting shipped work.

**No status is invented.** Every gate result recorded for 48.1 (check-all 16/16, native APPROVE, Aider APPROVE) is copied verbatim from the shipped spec's own Verification section, attributed to that artifact.

---

## 6. Architecture Decisions (proposed text)

### Decision AX — Browse-category data model: a new entity, deliberately not the retired one

**Proposed** 2026-07-26 for Initiative 26; amended by the 2026-07-26 controller review. Target `apps/api/app/core/db/models/_entities.py` **and** `migrations/versions/0020_browse_categories.py` — **one atomic story (49.1)**, because `test_orm_migration_parity.py` fails on either half alone (see Decision AZ).

**Entities.**

- **`BrowseCategory`**, `__tablename__ = "browse_category"`: `id` uuid PK; `slug` (unique + index — the stable public address); `name_en`; `name_pl: str | None`; `description_en: str | None`; `description_pl: str | None`; `inclusion_criterion: str | None` (FR26-GOV-1, stored with the entity so governance is data, not tribal knowledge); `position: int = 0`; `parent_id: uuid.UUID | None` FK → `browse_category.id`, **`ondelete="RESTRICT"`**, nullable; `created_at`; `updated_at`. Explicit `Index("uq_browse_category_slug", "slug", unique=True)` so the ORM name matches the migration exactly — the drift trap `TagGroup` documents at `_entities.py:31-36`.
- **`ModelBrowseCategory`**, `__tablename__ = "model_browse_category"`: composite PK `(model_id, category_id)`; `model_id` FK → `model.id` **`CASCADE`**; `category_id` FK → `browse_category.id` **`RESTRICT`**; `created_at`. Plus `Index("ix_model_browse_category_cat_model", "category_id", "model_id")`.

**Why this exact shape — it is `model_tag` verbatim.** `ModelTag` (`_entities.py:117-127`) is already composite-PK, `model_id` CASCADE, `tag_id` RESTRICT, with a reverse-direction index `ix_model_tag_tag_model`. The composite PK gives the packet's "unique pair, indexed both ways" for free (PK covers model→category; the extra index covers category→model). This is **reuse of a proven in-repo pattern, not a parallel implementation** — the pre-enumeration discipline [[feedback_scp_pre_enumeration_phase]] requires naming it.

**Why `RESTRICT` on `category_id`.** It makes FR26-ADMIN-1 structural: a category in use cannot vanish out from under models. Delete requires an explicit, audited detach first — exactly the tag posture ("delete requires merge-or-empty"). `CASCADE` on `model_id` matches every other model-owned child row: deleting a model must not leave orphan membership.

**Why identifiers are `BrowseCategory*`, not `Category*` — load-bearing.** `class Category`, `CategorySummary`, `CategoryNode`, `CategoryTree`, `CategoryCreate`, `CategoryPatch`, `useCategoriesTree` and the table `category` were **deleted** by Story 47.5 and are referenced throughout the SCP/retro/architecture history as the *mandatory single-category tree*. Resurrecting those exact identifiers with different semantics would make every historical sentence in this repo ambiguous, and would make a migration reading `create_table("category")` after `0019_drop_category` genuinely dangerous to interpret. Distinct physical and code identifiers cost nothing (`TagGroup` ↔ `tag_group` is the same explicit-naming pattern) and buy unambiguous history. **The product vocabulary is unaffected:** users, UI, and URLs say "category"/"Kategorie".

**Invariants preserved:** `Model` gains **no** column. `Tag`, `TagGroup`, `ModelTag` are byte-unchanged. `Tag.group_id` stays a single nullable FK (no Tag↔TagGroup M:N — packet §Tag-group decision). No existing index or constraint is touched.

**Depth-2 ceiling is enforced in the service layer, not the schema.** A nullable self-FK cannot express "at most 2 levels" in SQLite DDL. Admin create/update rejects a parent that itself has a parent, and rejects a self-cycle (`_would_cycle` in the deleted `admin_service.py` is prior art for the cycle check and may be re-derived, not resurrected). MVP writes no child categories at all.

### Decision AY — API contract: additive browse reads, category scope, and tag-aware search

**Proposed** 2026-07-26. Targets `apps/api/app/modules/sot/{router,schemas,service}.py` and `{admin_router,admin_schemas,admin_service}.py`.

**Read surface (all authenticated default-deny, `current_user`, outside `_PUBLIC_ROUTES` — Decision AW / Init 6 Decision M; `main.py:50-61` needs no edit):**

- **`GET /api/categories`** — flat list of browse categories ordered by `(position, slug)`, each `{id, slug, name_en, name_pl, description_*, position, parent_id, model_count}`. `model_count` = distinct non-deleted models assigned, computed by the same shared-helper approach as `GET /api/tags?with_counts=true` so the two can never disagree. Empty categories are returned (they are exactly what the curation QA surface needs to see).
- **`GET /api/categories/{slug}`** — one category by stable slug; `404` on unknown slug.
- **`GET /api/models?category=<slug>`** — **one** category scope, addressed by **slug**. Composes with `q`, `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `sort`, pagination. An **unknown slug yields an empty page with `total = 0`, not a 404** — a stale bookmark degrades gracefully, and this matches the shipped `tag_ids` posture where an unknown id produces an unsatisfiable predicate (`service.py:231-238`).
- **`ModelDetail` gains `categories: list[BrowseCategorySummary]`.** `ModelSummary` deliberately does **not** — list cards do not render categories in the MVP IA, and adding it would mean a second per-page eager-load for no rendered pixel.

**Why slug for `category` but UUID for `tag_ids`.** The browse scope is addressed by stable slug everywhere in the product (`/categories/{slug}` is the canonical URL, and `GET /api/categories/{slug}` is the detail read), so a slug param means first paint needs no slug→id resolve round-trip. Tags keep UUIDs because tag slugs are curated and mergeable (`POST /tags/merge`), and the FE already holds the full tag set from `GET /api/tag-groups`. The `43.3` canonical-UUID hardening for `tag_ids` (`routes/catalog/index.tsx:34,57-67`) is untouched.

**Tag-aware `q` (FR26-SEARCH-1) — membership predicate, never a join.** The `q` clause at `service.py:258-266` gains one disjunct:

```
OR Model.id IN (
    SELECT model_tag.model_id FROM model_tag JOIN tag ON tag.id = model_tag.tag_id
    WHERE lower(tag.name_pl) LIKE :like OR lower(tag.name_en) LIKE :like
)
```

`IN`-subquery (or `EXISTS`) rather than a `JOIN` is **required**, not stylistic: a model carrying three matching tags would appear three times under a join, and because `total` is computed as `count(*)` over `base.subquery()` **before** pagination (`service.py:279-280`), a join would inflate both the count and the page. The subquery keeps the outer `SELECT` shape unchanged, so the existing sort / offset-limit / eager-tag / eager-gallery pipeline applies untouched — the same argument `external_url` already records at `service.py:267-276`. Soft-delete (`deleted_at IS NULL`, `service.py:210-211`) and every other predicate are unaffected because the disjunct is added **inside** the existing `q` `or_()`, not alongside the base filters. Whether `tag.slug` should also match is deliberately left to story-creation with a recommendation of **no** (slugs are internal; the packet names `name_pl`/`name_en` only). **NFR26-PERF-1 is asserted as query count, not latency:** the `q` path must execute a constant number of SQL statements across page size *and* across the number of matching tags/models (no N+1 in the membership branch, the count branch, or the eager hydration), proven by comparing executed-statement counts under two fixture sizes chosen to yield **equal result counts** on the same page, plus the distinct-`total` assertions. No wall-clock threshold is asserted — none can be honestly baselined here.

**Suggestion endpoint: REUSE, not build.** `GET /api/tags?q=&limit=&with_counts=` already returns exactly what FR26-SEARCH-2 needs (`service.py:82-107`, `router.py:46-75`): case-insensitive substring over `slug`/`name_en`/`name_pl`, bounded `limit`. **No new or duplicate endpoint is required or authorized.** **Group labels for the `+ Kabel · Zastosowanie` pills are resolved, not assumed:** `TagRead` carries `group_id` + `group_position` only with **no** embedded label (Decision AW / D-SHAPE-1, `sot/schemas.py:35-47`); Story 50.3 must (1) verify at create-story that `group_id` is still on every item, (2) resolve the label from the **already-loaded** `useTagGroups()` map with no extra request, (3) render the pill without a suffix when that map is unavailable (a groupless tag has no suffix anyway), and (4) only if the contracts genuinely cannot supply it, propose the **smallest additive extension** to the existing tags read — never a second endpoint, never a per-suggestion N+1. The 6–8 cap and the bilingual dedupe-by-`id` are **client-side** concerns (one tag matching in both PL and EN is *one row* server-side already, since the match is an `or_` over columns of the same row — so dedupe is about not rendering two *labels*, not two rows). Any story that proposes a new suggestion endpoint must first justify why this one is insufficient.

**Admin surface (`current_admin`, audit row on every write, mirroring the 42.4 tag-group governance shape and `tag_group_admin_router.py` as the structural precedent):**

- `POST/PATCH/DELETE /api/admin/categories` — create / rename+reorder+reparent / delete.
- **Delete policy:** `409 Conflict` while assignments exist. An explicit `detach=true` performs the detach + delete in one transaction and writes an audit row recording the detached model ids **and** a count. (The epic:42 action item about unbounded `detached_tag_ids` audit payloads applies here by analogy — carry both the ids and the count, and re-evaluate only if catalogs grow large.)
- `PUT /api/admin/models/{id}/categories` — **replace-set** assignment (the whole set in one call; idempotent; **explicit last-writer-wins**). Chosen over add/remove deltas because the admin UI edits a set, so replace-set matches the actual edit unit.
  - **Honest concurrency posture (correction — the earlier "no lost-update ambiguity" claim was WRONG and is retracted).** LWW **does permit a lost update**: A and B both load the set, A adds `lamps` and saves, B — still on the pre-A snapshot — adds `kitchen` and saves, and **A's change is silently discarded** because B's payload never contained it. Replace-set does not prevent this; it only makes the discarded state a whole set rather than a partial merge. **Accepted for the current single-admin deployment as explicit, auditable LWW** — the justification is the per-write audit row carrying the resulting set (a lost update is recoverable and attributable after the fact), **not** the absence of the race. **Named future trigger:** a second concurrent admin editor, or any automated/agent writer, requires optimistic concurrency (`revision` integer or ETag / `If-Match` → `409` on stale writes). Until then none is built (minimal-diff). Any UI over this endpoint must not imply merge or conflict-detection semantics it lacks.
- New audit `entity_type` `browse_category` + `browse_category.*` actions, following the `tag_group` precedent added in 42.4.

**Invariants preserved:** `GET /api/tag-groups`, `GET /api/tags`, `POST /tags/merge`, the 42.1 AND/OR facet semantics, `tag_match`, `untagged`, and the anonymous `ShareModelView` contract are **all unchanged**. Whether the anonymous share projection should carry categories is **explicitly out of scope** for the MVP and must not be added incidentally (NFR25-LEAKFENCE-1's negative share-DTO test stays as the fence).

**Route path re-use of `/api/categories` — recorded tradeoff.** This path was retired by Story 47.5 and today 404s. Re-using it for the new resource was chosen over `/api/browse-categories` because: (a) it is the correct REST name for what the product calls categories; (b) there are provably **zero** live consumers — application source is clean (E-6), `cutover-smoke.sh` is already re-pointed to `/api/tags` and only *comments* on the retirement (E-9), and 47.3 removed the runbook pre-flight; (c) the shape differs (flat list + counts vs recursive `CategoryTree`), so no caller could silently succeed against the wrong contract. **The cost is documentation drift**, which is real and is why E54.3 is a required story: `docs/operations.md:426,463-464,613-614` states the surface is retired and would become misleading. Alternative recorded for the ratifying reviewer to overturn if preferred.

### Decision AZ — Migration `0020_browse_categories`: additive **and reversible**

**Proposed** 2026-07-26. `down_revision = "0019_drop_category"`. **Ships atomically with the ORM entities as Story 49.1** — `test_orm_migration_parity.py` (`compare_metadata`) fails on an entities-only branch (metadata has tables the DB lacks) and on a migration-only branch (DB has tables metadata lacks), so neither half can pass `check-all` 16/16 alone and neither is independently mergeable. Same coupling as E41 retro action item #2 and Story 47.5's single-commit shape, applied at **decomposition** time.

`upgrade()`: `op.create_table("browse_category", …)` + `op.create_index("uq_browse_category_slug", …, unique=True)`; `op.create_table("model_browse_category", …)` with the composite PK + `op.create_index("ix_model_browse_category_cat_model", …)`. **Structural only — no seed content** (the starter category set is a separate admin-run seed, story 49.3, mirroring the 41.3 precedent that kept `0018` free of content decisions).

`downgrade()`: **implemented** — `drop_table("model_browse_category")` then `drop_table("browse_category")`. This is a **deliberate departure** from `0018`/`0019`, which raise. Forward-only exists to make an *irrecoverable data loss* honest; `0020` creates tables that did not exist and destroys nothing pre-existing, so a raising `downgrade()` here would be cargo-cult ceremony that removes a genuinely safe rollback path. **Consequence to verify at story time (`VERIFY-AT-CREATE-STORY`):** `0019.downgrade()` raises, so any test that traverses head-downward past `0019` still stops there — `0020` does not change that, and the `test_migration_00xx` family must be checked for the same head-pinning adjustment pattern that 47.5's `d11` applied.

**Table-name collision safety.** `0019` dropped `category`; `0020` creates `browse_category`. No name is reused, so no restore-then-upgrade path and no migration reader can confuse the two contracts. This is the concrete discharge of the packet's requirement that the migration "must not recreate the old dropped category table contract accidentally".

**Parity test.** The ORM↔migration parity test `test_orm_migration_parity.py` (landed in 47.5, `compare_metadata` on a migration-upgraded scratch DB) already guards drift and will fail if the new entities and `0020` disagree — **no new drift-guard needs building**, only the assertion that it is green.

**Deploy posture.** Additive + reversible ⇒ the destructive-go protocol that governed `0019` (fresh verified backup under `flock /tmp/3d-portal-deploy.lock`, demonstrated restore-readiness, sole-change deploy, whole-commit revert plan) **does not apply**. A routine pre-deploy backup per standing policy is sufficient. Single Alembic head after `0020` is still asserted.

### Decision BA — Mobile lightbox: adoption is a decision story, not a plan assumption

**Proposed** 2026-07-26. Target `apps/web/src/modules/catalog/components/imageViewer/`.

The packet states a **research preference** for *Yet Another React Lightbox* + Zoom plugin, with *PhotoSwipe 5.4.x* as plan B if physical-Android gesture quality is materially better — and explicitly states that **adoption is not pre-decided**. This decision therefore records a *decision procedure*, not a dependency:

**Story 53.1 is a spike that must score exactly THREE options — (1) Yet Another React Lightbox + Zoom, (2) PhotoSwipe 5.4.x, (3) extend the existing in-house viewer — and produce a written recommendation** against four criteria, each with recorded evidence: (1) bundle-size delta measured against the current build; (2) integration cost with both existing mounts (`ModelGallery` on `/catalog/$modelId`, `ShareCarousel` on `/share/$token`) **without disturbing their `renderImage`/`renderThumb` auth boundaries** — an explicit `Always:` constraint carried forward verbatim from the E48.1 spec; (3) accessibility — dialog semantics per the WAI-ARIA APG modal-dialog pattern, focus trap and return focus, and *visible* zoom controls satisfying WCAG 2.2 SC 2.5.1/2.5.7 without relying on pinch; (4) **physical Android Chrome gesture quality**, since synthetic Playwright touch events are regression evidence only and cannot settle this. **Option 3 must be scored as seriously as the two libraries**, since E48.1 proved the component is small, well-understood, and now has a geometry regression suite; a dependency must earn its place.

**Carried-forward invariants from E48.1 (must not regress):** viewport-anchored geometry in a single reference box (`left-[1vw]` + `translate-x-0`, not `left-1/2` + `-translate-x-1/2`) — the measured root cause of the shipped bug; `dvh` not `vh` for the height budget; **never** suppress browser pinch-zoom via `user-scalable=no`; the shared `apps/web/src/ui/dialog.tsx` primitive is `Ask First` (blast radius = every dialog); `apps/web/tests/visual/image-viewer-containment.spec.ts` is a **standing** regression suite that E53 must keep green, not replace.

**Explicitly deferred (E48.1 residual risk, not adopted into E53 scope):** `Viewer3DModal` and other `DialogContent` consumers may share the mixed-reference-box pattern. E53 touches the image lightbox only. Migrating other dialogs requires a reported defect or an explicit story — the same boundary E48.1 drew.

---

## 7. Implementation Handoff

**Change scope classification: MAJOR → route to Product Manager / Solution Architect.**

| Recipient | Responsibility |
|---|---|
| **PM / Architect (this workflow)** | ✅ Delivered: this SCP + PRD § Initiative 26 + architecture Decisions AX–BA + epics § Initiative 26 + `sprint-status.yaml` reconciliation. |
| **Controller (Laura)** | ✅ Done 2026-07-26 — ratified this document, closed G26-ROUTE-PATH, decided G26-UXGATE, routed G26-CAT-SET into the UX pass. Remaining: confirm each ready story at dev-entry (G26-DEVGO). |
| **`bmad-check-implementation-readiness` (IR)** | Required gate before implementation — run against the updated PRD / architecture / epics. |
| **`bmad-ux` (CU)** | **Required** (G26-UXGATE decided). Targeted pass over the seven no-SoT surfaces, before Story 50.3 / E51 / E52 story-creation; also produces the G26-CAT-SET starter taxonomy content before Story 49.2. |
| **`bmad-sprint-planning` (SP)** | Finalises story IDs/splits. Keys are pre-seeded at `backlog` by §5.4 per checklist 6.4; SP owns any resequencing. |
| **`bmad-create-story` (CS) + `:validate` (VS)** | Per story at dev-entry. **Every `VERIFY-AT-CREATE-STORY` marker in §9 is a mandatory fresh repo-wide trace**, per the standing epic:47 action item. |
| **`bmad-dev-story` (DS) → native review → Aider** | Per story, after explicit operator dev-go. Independent Aider review after native BMAD review, per the Laura Agent Rulebook (`laura-aider-review-diff`; Gemini is not a default reviewer; Codex is fallback/high-stakes only). |

**Success criteria for this correct-course:** planning artifacts are internally consistent; the Initiative 25 retirement history is preserved verbatim and unambiguously distinguished from the new design; E48.1 is recorded as shipped and is not re-planned; no implementation code was written; no live, destructive, or repository-publishing action was taken.

---

## 8. Gates after the 2026-07-26 controller review

| Gate | Status | Owner | Statement |
|---|---|---|---|
| **G26-SCP-RATIFY** | ✅ **closed** | Laura (controller) | SCP text read and **ratified 2026-07-26** under the operator-approved packet and the standing `działaj` delegation; the review produced the eight §0a corrections. **No Ezop sign-off is recorded or implied** — the operator approved the product direction via the packet, not this text. |
| **G26-ROUTE-PATH** | ✅ **closed** | Laura (controller) | **Ratified:** re-use of the retired `/api/categories` path for the new contract, together with the internal `BrowseCategory*` / `browse_category` identifier convention. Basis: zero live consumers (`cutover-smoke.sh` already re-pointed to `/api/tags`; Story 47.3 removed the runbook pre-flight), an entirely different response shape, and distinct code/table identifiers so no deleted symbol is resurrected. Documentation cost is owned in-story by 49.3. |
| **G26-UXGATE** | ✅ **decided** | Laura (controller) | A **targeted `bmad-ux` pass** runs before **Story 50.3, Epic 51 and Epic 52**, scoped to the seven surfaces with no visual SoT: browse nav, mobile Browse surface, category scope chip + "Search entire catalog", the query-vs-`+tag` suggestion dropdown, the `Filters (n)` drawer, the admin category/curation screens, and the lightbox chrome. **E49 and Story 53.1 are not blocked by it.** |
| **G26-CAT-SET** | 🔓 **open — routed** | Operator, via the UX/taxonomy pass | The concrete ~6–10 starter categories and their FR26-GOV-1 inclusion criteria stay owner-authored content, **routed into the same targeted UX/taxonomy pass**, and must exist before **Story 49.2** is created. Deliberately not turned into a second operator question. |
| **G26-LIB** | 🔓 open | Story 53.1 → Operator | Lightbox adoption stays undecided by design; needs the 53.1 three-option recommendation **and** physical-Android evidence. |
| **G26-MIGRATE** | 🔓 open | Story 49.1 create-story | Confirm `0020` is additive+reversible, that the `test_migration_*` head-pinning family needs no further adjustment beyond the 47.5 `d11` pattern, and that a single Alembic head remains. Explicitly **not** a destructive gate. |
| **G26-DEVGO** | 🔓 open | Controller, per story | **Planning may proceed now.** Code on any story starts only after `bmad-create-story` + `bmad-create-story:validate` and the controller confirming **that specific ready story** under the user's standing initiative authorization. This proposal authorizes no implementation by itself. |

---

## 9. Epic and story decomposition (proposed — full text lands in `epics.md`)

Legend: `VERIFY-AT-CREATE-STORY` = a stated precondition that **must** be re-traced against live code at story-creation time and never carried forward as settled (standing epic:47 action item).

### Epic 48 — Mobile fullscreen containment quickfix — ✅ **DONE (shipped 2026-07-26, `da87e71`)**

Reconciled retroactively (§1.4). **Story 48.1** — viewport-anchored dialog geometry, `dvh` height budget, viewport-safe close, new geometry regression spec, 2 mobile baselines regenerated with inspected sub-pixel deltas. `done`. **Not re-opened by any Initiative 26 story.**

### Epic 49 — Browse-category data + additive API foundation *(backend, additive)* — `backlog`

**Depends on:** nothing. **Hard prerequisite for E50–E52.** No destructive DDL, no endpoint retirement. **Not blocked by G26-UXGATE.**

> **Renumbered by the 2026-07-26 controller review.** Former 49.1 (entities) + 49.2 (migration) are **one atomic story**; former 49.3→49.2, 49.4→49.3, 49.5→49.4, 49.6→49.5. Every renumbered key was `backlog` and had never been created, validated or implemented, so no shipped identifier is affected.

- **49.1** — **`BrowseCategory` + `ModelBrowseCategory` entities AND Alembic `0020_browse_categories` (atomic).** Reuse the `ModelTag` composite-PK/CASCADE/RESTRICT/reverse-index shape verbatim; explicit index names to avoid the `TagGroup` drift trap; `Model` gains no column. Migration additive **and reversible**, no seed content, no reused table name. **Atomic because `test_orm_migration_parity.py` (`compare_metadata`) fails on either half alone** — neither half passes `check-all` 16/16, so neither is independently mergeable. One branch, one commit. `VERIFY-AT-CREATE-STORY`: the `test_migration_*` head-pinning family against the raising `0019.downgrade()`; single Alembic head.
- **49.2** *(was 49.3)* — Idempotent admin-run starter-category seed (~6–10 broad categories + FR26-GOV-1 inclusion criteria). Separate from the migration, mirroring 41.3. **No model assignments.** Gated on **G26-CAT-SET**, whose content comes from the targeted UX/taxonomy pass.
- **49.3** *(was 49.4)* — Read API: `GET /api/categories` (flat + counts), `GET /api/categories/{slug}`, `GET /api/models?category=<slug>`, `ModelDetail.categories`. Auth default-deny; `_PUBLIC_ROUTES` needs **no** edit (`VERIFY-AT-CREATE-STORY`). **Ships the `docs/operations.md` + `cutover-smoke.sh`-comment honesty correction in-story** (readiness M-1) so no shipped change leaves live docs knowingly false.
- **49.4** *(was 49.5)* — Tag-aware `q` (FR26-SEARCH-1). `IN`/`EXISTS` membership disjunct inside the existing `q` `or_()`. Correctness: name-match ∪ tag-match; a both-match model appears **once**; `total` = distinct count; composition with `category` + `tag_ids`/`tag_match` + `untagged` + soft-delete. **NFR26-PERF-1 as query count** — constant across page size and across matching tag/model counts, proven by equal-result-count fixture-size comparison. No wall-clock threshold.
- **49.5** *(was 49.6)* — Admin category governance: CRUD + reorder + reparent (depth-2 + cycle rejection), replace-set assignment under **explicit auditable LWW** (lost update possible, accepted, audit-backed, `revision`/ETag as named trigger), `409`-unless-`detach=true` delete with audit, `browse_category` audit entity_type. Structural precedent: `tag_group_admin_router.py` (`VERIFY-AT-CREATE-STORY`).

### Epic 50 — Frontend data layer, URL state, and search suggestions *(additive)* — `backlog`

**Depends on:** E49 on `main`. **Story 50.3 additionally gated on G26-UXGATE.**

- **50.1** — FE types + hooks (`BrowseCategoryRead`, `useCategories`, `useCategoryBySlug`); extend `useModels` with `category`. Additive only. No user-visible surface ⇒ no i18n/a11y/visual obligation; hook unit coverage still owed.
- **50.2** — URL state: `category` as an **independent visible layer** alongside `q`/`tag_ids`/`tag_match`/`untagged`/`sort`/`page`, extending the shipped `validateSearch` pattern. Never folded into `tag_match`. Owns its validator unit coverage.
- **50.3** — Inline structured suggestions on the **existing** `GET /api/tags?q=` (a duplicate suggestion endpoint is forbidden). Distinct query vs `+tag` pills; ≤6–8 items, no internal scrollbar; dedupe by canonical `tag_id`; **group labels resolved from the already-loaded `useTagGroups()` map**, rendered without a suffix when unavailable, smallest additive contract extension only as a last resort. **Owns at its own gate:** its en+pl keys with key-set diff; a11y assertions (plain-search vs `+tag` distinguishable by **accessible name**, listbox/option roles, focus order, ≥24×24 targets); targeted unit + pl-PL visual coverage with `toBeVisible()` before every screenshot.

### Epic 51 — Browse IA: categories as navigation *(the one user-visible cutover)* — `backlog`

**Depends on:** E49 + E50 on `main`. **Gated on G26-UXGATE (targeted `bmad-ux` pass runs first).** Every story owns its own i18n keys, component-level a11y assertions and targeted unit/visual coverage at its own merge gate.

- **51.1** — Desktop left navigation renders broad categories + optional counts; the facet taxonomy leaves the navigation role. `VERIFY-AT-CREATE-STORY`: `FacetSidebar.tsx`'s actual mounts and props at that time.
- **51.2** — `/categories/$slug` route; category scope chip above results (**not** a checkbox, **excluded** from the `Filters (n)` count); one-click "Search entire catalog"; scoped-by-default search. Requires `routeTree` regeneration.
- **51.3** — Mobile Browse surface/menu, separate from the desktop rail. `Ask First` if it touches `ModuleRail`.
- **51.4** — **Model-detail category display.** Render a model's categories on `/catalog/$modelId`, visually distinct from the shipped `TagGroupsSection`; a category click navigates to `/categories/{slug}`. *Added by the `bmad-check-implementation-readiness` gate (finding C-1) — the read-API story adds `ModelDetail.categories` and 50.1 types it, but no story consumed it.*

### Epic 52 — Filters surface + admin curation and governance — `backlog`

**Depends on:** E49 (admin API) + E51 (browse IA patterns). **Gated on G26-UXGATE.** Every story owns its own i18n keys, a11y assertions and targeted unit/visual coverage.

- **52.1** — `Filters (n)` drawer/panel consolidating tags/facets; full tag search inside; ≤2–4 promoted groups, only if justified; the tiny `+tag` ribbon control stops being the primary tag path while Filters stays discoverable.
- **52.2** — Admin category management: CRUD, reorder, per-model replace-set assignment, `Uncategorized / needs curation` queue, advisory 1–3 warning (never blocking). **Concurrency honesty carries into the UI:** under the accepted explicit-LWW posture the screen must not imply merge or conflict-detection semantics it lacks — re-fetch before editing and surface the audit trail where cheap.
- **52.3** — Curation QA surfaces (FR26-ADMIN-2): zero/many categories, empty/tiny categories, categories behaving like narrow tags, Category/Tag label-overlap warnings, ungrouped user-facing tags. Advisory only. Story-creation must pick a **concrete** number for "unusually many" (readiness m-2).

### Epic 53 — Mature mobile lightbox *(separate from the E48.1 quickfix — Decision BA)* — `backlog`

**Depends on:** nothing in E49–E52 (independent track). **Gated on G26-LIB.**

- **53.1** — **Adoption spike + written recommendation, scoring exactly THREE options:** (1) YARL+Zoom, (2) PhotoSwipe 5.4.x, (3) extend the in-house viewer. Scored on bundle delta, integration cost against both mounts **without touching their `renderImage`/`renderThumb` auth boundaries**, a11y (APG modal-dialog, focus trap/return, visible zoom controls per WCAG 2.2 SC 2.5.1/2.5.7), and **physical Android Chrome** gesture quality. Produces a recommendation, not code; **adoption is not pre-decided**. Owns no i18n/a11y/visual surface of its own. **Not blocked by G26-UXGATE.**
- **53.2** — Implement the chosen viewer (**owns its own en+pl control labels, component-level a11y assertions and targeted pl-PL visual coverage at its gate**): pinch zoom, pan, double-tap, **visible Zoom In/Out/Reset**, toolbar stable outside the transform layer, body scroll lock + restoration, focus trap/Escape/return focus, safe-area + dynamic-viewport handling, explicit swipe-vs-pan conflict rules. Must preserve every E48.1 invariant (Decision BA) and keep `image-viewer-containment.spec.ts` green.
- **53.3** — **Test contract** (packet §Scope A, verbatim): Pixel 5 portrait + landscape; light + dark; panorama 4:1 and 8:1; portrait 1:4; small source; close bounds/hit area ≥44×44; zero document overflow; rotation refit; zoom/pan clamp + reset; swipe-vs-pan; body-scroll restoration; focus trap / Escape / return focus; error + slow-load; repeated open-close. Playwright synthetic touch is **regression evidence only** — final gesture acceptance requires a physical Android Chrome smoke, recorded as operator evidence.

### Epic 54 — Cross-surface i18n/a11y/visual audit + rollout and docs — `backlog`

**Depends on:** E51–E53 surfaces landed.

> **Recast by the 2026-07-26 controller review.** 54.1/54.2 were previously written as if they were where i18n keys, a11y assertions and visual baselines *first appear*. That is incompatible with every UI story having to pass `check-all` 16/16 on its own branch. Per-story ownership is now mandatory; **E54 is the final cross-surface audit + remediation pass.**

- **54.1** — **Cross-surface i18n parity audit + remediation** (renamed from "i18n"). Full en/pl key-set parity across the whole Initiative 26 key space; no placeholder or English-identical Polish; consistent terminology for the same concept across browse nav, scope chip, suggestions, Filters drawer, admin screens and viewer controls. A finding here is a **defect in the story that shipped the surface**, not new end-of-initiative scope. `VERIFY-AT-CREATE-STORY`: which keys already exist (the epic:46 I18N SCOPE NOTE precedent).
- **54.2** — **Cross-surface a11y + visual audit + remediation** (renamed from "visual specs"). End-to-end WCAG 2.2 SC 2.5.1/2.5.7/2.5.8 over the whole journey (browse → scope → filter → detail → viewer), **including keyboard-only and screen-reader traversal between surfaces, which no single component test covers**; cross-surface light/dark consistency; the `/api/*` route-mock consolidation pass. The per-screenshot `toBeVisible()` rule is enforced at each story's own gate; this story verifies none slipped.
- **54.3** — Rollout + docs + governance: `docs/architecture.md` and the agent add-model runbook distinguish the **retired mandatory single-category taxonomy** from the **new independent M:N browse categories**; publish the category governance doc (inclusion criteria, positive/boundary examples, Category-vs-Tag distinction rule, periodic QA checklist, **and the recorded explicit-LWW concurrency posture with its named upgrade trigger**). The passages that go stale at 49.3's deploy moved into 49.3 (readiness M-1). Exists because the epic:47 CUTOVER-CHECKLIST action item requires operational probes and live docs to be scanned, not just `apps/`.

### Standalone stories

None. All Initiative 26 work sits inside E48 (shipped) and E49–E54.

---

## 9a. Readiness-gate record (`bmad-check-implementation-readiness`)

**First run, 2026-07-26 (pre-controller-review).** Verdict **⚠️ NEEDS WORK**. Found and remediated in-pass:
- **C-1 (🔴):** FR26-CAT-2 had no rendering story — the read-API story added `ModelDetail.categories` and 50.1 typed it, but nothing consumed it. → **Story 51.4 added.**
- **M-1 (🟠):** documentation forward dependency — the read-API story ships `GET /api/categories`, which immediately falsifies `docs/operations.md:426,463-464,613-614` and the `cutover-smoke.sh:397-405` comment, yet the correction sat five epics later in 54.3. → **Moved into Story 49.3**; 54.3 narrowed to the non-staling remainder.

Left open at that point: **C-2** (technical epics, accepted deviation), **M-2** (no ACs yet, accepted by convention), **M-3** (NFR26-PERF-1 unmeasurable), **m-1..m-4**.

**Second run, 2026-07-26 (re-run against the corrected artifacts after the §0a controller review).** Report: `implementation-readiness-report-2026-07-26.md`.

**Verdict: 🟢 CONDITIONALLY READY** — upgraded from NEEDS WORK. Coverage **13/13 FRs, 7/7 NFRs**; no forward dependencies; **every story now independently mergeable** under `check-all` 16/16; quality NFRs owned at the gate that ships each surface. Remaining conditions are **gates and a scheduled UX pass, not artifact defects**.

Changes in verdict-relevant findings between runs:
- **M-3 ✅ resolved** — NFR26-PERF-1 restated as a **query-count** assertion (constant across page size and across matching tag/model counts, proven by equal-result-count fixture-size comparison) with no invented wall-clock number.
- **New finding R-1 ✅ resolved in the same pass** — the former 49.1/49.2 split was **not independently mergeable** under `test_orm_migration_parity.py`; merged into the atomic Story 49.1, remaining E49 stories renumbered.
- **New finding R-2 ✅ resolved** — E54.1/E54.2 as written would have made every UI story unmergeable (a surface with no keys and no coverage cannot pass its own gate); per-story ownership made mandatory and E54 recast as the cross-surface audit.
- **New finding R-3 ✅ resolved** — the replace-set "no lost-update ambiguity" claim was **factually false**; retracted and replaced with an explicit, auditable LWW posture plus a named upgrade trigger.
- **New finding R-4 ✅ resolved** — Story 50.3 depended on a group label the `TagRead` wire does not carry; label sourcing now specified against the already-loaded `useTagGroups()` map.
- **C-2 (🔴) remains an accepted, justified deviation** — E49/E50 are technical epics with no standalone user value, and 49.1 creates both tables at once. Authorized by the operator packet's mandated additive-first sequencing, this repo's thrice-ratified Initiative 25 precedent, the single-host auto-deploy topology (a half-built vertical slice is a *live* defect), and the fact that the two tables are one referential unit. Recorded, not quietly redefined.
- **M-2 (🟠) remains accepted by convention** — story ACs are produced by `bmad-create-story` at dev-entry; every FR carries an explicit *Verifiable* clause as the AC seed. `G26-DEVGO` plus mandatory create+validate is the control.
- **m-1..m-4 (🟡)** unchanged: E48 `done` inside a `planning` initiative (reconciled with provenance); "unusually many" unquantified (52.3 must pick a number); 53.1 is a spike, not a user-value story; E53 is parallelizable and its numbering is not a strict order.

**Stated limitation, both runs:** the gate ran in the same agent session that authored the artifacts. It found and fixed six real defects across the two runs, but self-assessment is **not** a substitute for independent review.

---

## 10. Cross-references

- Input packet: `/tmp/3d-portal-init26-correct-course-input.md` (operator-approved direction, 2026-07-26).
- Readiness report: `implementation-readiness-report-2026-07-26.md` (native gate, re-run against the corrected artifacts).
- Controller review iteration: §0a of this document (Laura, 2026-07-26).
- Shipped quickfix: commit `da87e71`; spec `_bmad-output/implementation-artifacts/spec-e48-1-mobile-fullscreen-containment.md`.
- Predecessor initiative: `sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md` and its three correct-courses (`2026-07-19-e42-deferred-coupled-cutover`, `2026-07-19-e43-fe-data-additive-correction`, `2026-07-22-e47-4-absorbed-into-47-5`).
- Retrospectives consulted: `epic-41-retro-2026-07-18.md` … `epic-47-retro-2026-07-23.md` (via `sprint-status.yaml` `action_items`).
- Architecture lineage: Decisions AU / AV / AW (Initiative 25) → **AX / AY / AZ / BA** (Initiative 26).
- Standing action items honoured by this proposal: epic:47 PROCESS (decomposition-time precondition verification → every `VERIFY-AT-CREATE-STORY` marker); epic:47 CUTOVER CHECKLIST (ops probes + live docs scanned → E-9, E-10, Story 54.3); epic:45/46 GOVERNANCE (no fabricated sign-off → §0 provenance note, §8 G26-SCP-RATIFY); epic:45/46 TEST-AUTHORING (`toBeVisible()` before every screenshot → Story 54.2); epic:41 migration classification at decomposition time (→ Decision AZ, classified additive+reversible **before** any story spec exists).
- Research registry: the 18 sources in the input packet §"Research evidence summary" (Printables, MakerWorld, Thingiverse, MyMiniFactory, Sketchfab, Fab, Amazon, Poly Haven; Baymard autocomplete + horizontal filtering; Algolia autocomplete + faceting; YARL docs + Zoom plugin; PhotoSwipe options; W3C APG modal-dialog; WCAG 2.2 pointer-gestures / dragging-movements / target-size).
