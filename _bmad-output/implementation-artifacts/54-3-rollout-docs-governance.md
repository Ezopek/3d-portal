---
baseline_commit: 1906498064e49cb49f57208e4ec93faf91865b97
---

# Story 54.3 — Rollout, docs, and category governance (FR26-GOV-1)

Status: done

<!-- 2026-07-31: `ready-for-validation` -> `ready-for-dev` by the native `bmad-create-story` Validate (VS) pass, repo-local Claude Opus 5, on `main` @ `1906498`. VERDICT: PASS after five corrections applied in place (R-1 the AC-2 operations.md scope ruling, R-2 the § 3.1/§ 7 file-table contradiction, R-3 the deferred-work.md:381 mis-citation, R-4 the docs/index.md heading, R-5 the § 0.2 blanket exclusion). All ten § 2 traces independently re-measured inline and confirmed; Q-1..Q-6 ruled in § 11. Full record in § 16. This pass read only; it wrote no docs, no code, no branch, ran no gate and made no commit. **`G26-DEVGO` remains OPEN — validation does NOT grant it; the controller must issue per-story dev go before `bmad-dev-story` runs.** `G26-LIB` remains OPEN and untouched. NOT an Ezop signature and NOT human review of any kind. -->

<!-- Created 2026-07-31 by native `bmad-create-story` (Create action), repo-local Claude Opus 5, on `main` @ `1906498`, clean tree. This is a CREATE-only pass: the artifact was authored and written, and NOTHING was validated, implemented or verified by execution. NOT an Ezop signature and NOT human review of any kind. -->
<!-- Status is deliberately `ready-for-validation`, NOT `ready-for-dev`. The vanilla `bmad-create-story` template sets `ready-for-dev` at create; this repo's precedent (Story 54.2, § header comment) is that CREATE leaves the story at `ready-for-validation` and the Validate (VS) pass owns the flip. The controller granted this create pass only. Recorded as a deliberate deviation in § 11 Q-1. -->
<!-- Subagent deviation: the `bmad-create-story` workflow invites research subagents for parallel artifact analysis. This session's controller directive forbids Agent-tool dispatch without an explicit request, so every trace in § 2 was measured INLINE in this session against `1906498`. No analysis was delegated and no subagent result is cited anywhere in this file. Recorded in § 11 Q-2. -->

- **Epic:** E54 — Cross-surface i18n/a11y/visual audit + rollout and docs (Initiative 26 — Catalog Discovery). Final story of the final Initiative 26 epic. Siblings 54.1 and 54.2 are `done` (`sprint-status.yaml:407-408`); E49–E52 are `done`; E53's three stories are `done` (`sprint-status.yaml:402-404`).
- **Author:** Claude Opus 5, native `bmad-create-story`, repo-local. **NOT** an Ezop signature and **NOT** human review of anything.
- **Created:** 2026-07-31, at `main` @ `1906498` (`git status --porcelain` empty at authoring time).
- **Authorization posture:** planning artifact only. This create pass wrote exactly two files: this artifact and the `sprint-status.yaml` status line. Zero product code, zero docs, zero tests, zero locale content, zero baselines. No branch was created, no gate/test/build/script was run, no commit/stage/push/merge/deploy/migration/seed/live-DB/network action was taken. `G26-DEVGO` is **🔓 open** and **CREATE does not grant it.**

---

## 0. ⛔ ENTRY GATE — read before `bmad-create-story:validate` and before `bmad-dev-story`

> **This is a DOCUMENTATION story. Its entire deliverable is truthful prose in three files plus one new file. It ships no product code, no tests, no locale keys and no baselines.** The risk profile is inverted from 54.1/54.2: nothing here can break a gate, and everything here can quietly state something false. Every sentence written must be traceable to shipped code, a shipped seed, or a recorded decision.

### 0.1 Honesty gates — not negotiable, not discharged by this story

| Gate | State entering, during, and (unless a controller ruling says otherwise) leaving this story |
|---|---|
| **`G26-LIB`** (`architecture.md:3386`, Decision BA) | **🔓 OPEN.** This story does not close it, does not touch it, and produces no evidence toward it. **Nothing written by this story may be cited as lightbox-adoption evidence.** |
| **`G26-DEVGO`** (`architecture.md:3386`) | **🔓 OPEN.** Planning proceeds; documentation edits start only after create **+ validate** and controller confirmation of *this ready story*. **Creating this file does not grant it.** |
| **Physical Android Chrome evidence** | **NONE EXISTS, and none may be fabricated, implied, or claimed** — including by omission, e.g. a "rollout complete" or "Initiative 26 verified on mobile" sentence in any doc this story writes. Every Initiative 26 a11y/visual finding in this repo is jsdom / headless-Chromium evidence only. The `mobile-*` Playwright projects are **Pixel 5 emulation**, never Android. |
| **Ezop / human sign-off** | Not sought, not implied, not present. No sentence in any file this story writes may attribute review, approval or acceptance to a human. |
| **The real-catalogue distribution evidence behind the eight categories** | Produced by Story 49.2 against a live capture whose artefacts live under `.hermes/run-logs/` — **local and gitignored** (`seed.py:262-265`). The governance doc may state the conclusion and cite the seed comment; it **must not** imply the underlying capture is reproducible from this repository, because it is not: the test suite runs against an empty scratch DB (`seed.py:263-265`). |

### 0.2 What this story is NOT

- ⛔ **Not** `infra/scripts/cutover-smoke.sh`, in any form. It moved into Story 49.3 by the 2026-07-26 readiness narrowing (`epics.md:4481`, `epics.md:4599`; `sprint-status.yaml:409` pre-create text) and is **verified already corrected** at `1906498` (§ 2 V-5). This story **re-reads** it as part of the epic:47 cutover scan and does not edit it.
- ⚠️ **`docs/operations.md` is READ-ONLY except for AC-2's single parenthetical at `:426-427`.** The same narrowing moved this file to Story 49.3, and 49.3 corrected `:463-464` and `:613-616` but **explicitly declined `:426-427`** (its § 6 F-7, review-concurred). The validate pass ruled that one residual falsehood survives there and that this story disposes of it under AC-9 → AC-2 (§ 16 R-1). **Everything else in that file stays byte-unchanged.**
- ⛔ **Not** the `toBeVisible()` screenshot-census sweep (69 call sites across ~40 specs) and **not** the `filter-ribbon-selects-open.spec.ts` baseline rename. Both ledger entries name "Story 54.3 **or** a controller-assigned follow-up" (`deferred-work.md:376,381`). Both are **routed OUT** by D-8 — see § 12. Adopting either converts a docs-only story into a test-refactor story with PNG-churn exposure.
- ⛔ **Not** a re-decision of the eight starter categories. They are shipped in `apps/api/app/core/db/seed.py:282-361` and governed at runtime by the admin surface (Story 49.5). This story **transcribes and publishes**; it does not add, merge, rename, reorder or retire a category, and it writes no migration and no seed edit.
- ⛔ **Not** an implementation of optimistic concurrency. The LWW posture is **recorded**, with its named upgrade trigger. Writing a `revision` column or an `If-Match` header is explicitly out (`architecture.md:3340`).
- ⛔ **Not** a rebuild of the curation-QA checks. Story 52.3 shipped a live six-check panel; the "periodic QA checklist" this story owes is **operating instructions for that panel plus a cadence**, not a parallel manual procedure (D-3).
- ⛔ **Not** a `docs/index.md` regeneration and **not** a `bmad-document-project` re-run. One index line is added; nothing else in that file is touched.

### 0.3 The shape to expect

Three edited files, one new file, one BMAD ledger amendment. `docs/architecture.md` is **57 lines total** — the classification section it gains should be on the order of 20–30 added lines, not a rewrite. The runbook gains one new subsection plus a one-line honesty correction. The governance doc is the only substantial new prose, and roughly 80 % of it is transcription from two shipped sources. **A diff that rewrites `docs/architecture.md` wholesale, or that invents governance content with no shipped antecedent, is the signal to stop.**

---

## 1. Story statement

**As** the operator curating this catalogue, and as any future agent or contributor who reads this repository's live documentation to learn how models are classified,

**I want** `docs/architecture.md` and the agent add-model runbook to state plainly that the mandatory single-category taxonomy is retired and that browse categories are now an **independent, optional, many-to-many** layer alongside facet tags — and I want one published governance document that carries each category's inclusion criterion, its positive and boundary examples, the Category-vs-Tag distinction rule, the periodic QA routine, and the accepted last-writer-wins concurrency posture with the trigger that would end it,

**so that** `FR26-GOV-1` (`prd.md:2255`) is discharged in **live documentation** and not only in planning artifacts, and so that the standing epic:47 CUTOVER-CHECKLIST action item (`sprint-status.yaml:540`) — *scan operational probes and live ops/architecture documentation, not only `apps/` source* — is actually executed for Initiative 26 rather than assumed.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped content at `1906498`

> Every item below was measured **inline in this session** against a clean tree at `1906498`. No figure is inherited from the epic sketch, from a sibling story, or from a subagent.

### V-1 — `docs/architecture.md` contains **zero** occurrences of "categor" (case-insensitive). The distinction this story must publish is entirely absent.

`grep -ic categor docs/architecture.md` → **0**. The file is 57 lines. Its § "Data flow" (`docs/architecture.md:34`) enumerates *"Models, files, tags (facet-grouped), notes, prints, and external links"* — the sentence was already updated for the Initiative 25 facet-tag rebuild but **never** for Initiative 26, so browse categories are invisible in the repository's high-level architecture doc. Its § "Container responsibilities" API line (`:26`) lists *"the SoT entity tables (model, model_file, tag, tag_group, etc.)"* and likewise omits `browse_category` / `model_browse_category`.

**Consequence:** this is a pure *addition*, not a correction. There is no false category sentence in this file to repair — the file is silent, and silence is why a reader would still assume the Initiative 25 shape.

### V-2 — `docs/agents-add-model-runbook.md` contains **zero** occurrences of "categor". The agent-facing assignment contract does not exist.

`grep -ic categor docs/agents-add-model-runbook.md` → **0** across 409 lines. The closest existing analogue is § "Behavioral Notes" → *"Import flow does NOT touch tags or photos"* (`:357`), which is exactly the shape the category contract should take (D-4).

### V-3 — ⚠️ **The runbook states a falsehood about auth**, in the file this story edits.

`docs/agents-add-model-runbook.md:398` (step 10 of the worked flow) reads: *"Fetch the model via the public model-detail endpoint (`GET /api/models/{model_id}`, **unauthenticated**)."*

**Measured false three ways:**
1. `apps/api/app/modules/sot/router.py:248-252` — `def get_model(...)` carries `_user_id: uuid.UUID = current_user`.
2. `apps/api/app/main.py:50-61` — `_PUBLIC_ROUTES` contains only `/api/health`, the five `/api/auth/*` entries and the three `/api/share/{token}*` entries. `/api/models/{model_id}` is **not** in it, and the mechanical route-enforcement gate (`test_route_enforcement_gate.py`) exists precisely to keep that list honest.
3. `docs/operations.md:464-465` already says the opposite in as many words: *"'Public read' means the read half of the API, not anonymous access — every route listed here is behind `current_user`."*

**Disposition: ADOPTED** as AC-6 — one-line correction, in a file this story already opens, in the same doc-honesty family as the story's charter. It is a **pre-existing defect from the Initiative-11 default-deny work**, not Initiative 26 scope, and AC-6 says so in the diff. It is called out here rather than fixed silently so the validate pass can overrule it if it prefers a separate routed follow-up.

### V-4 — Every browse-category **write** is admin-only. The agent role gets `403`. This is deliberate and mechanically gated.

- `apps/api/app/modules/sot/browse_category_admin_router.py:62` mounts `APIRouter(prefix="/api/admin", tags=["sot-admin-governance"])`; every one of its `POST` / `PUT` / `PATCH` / `DELETE` handlers takes `current_admin` (`:168, :207, :248, :285`), including `PUT /api/admin/models/{model_id}/categories` (`:182`).
- `apps/api/app/core/auth/dependencies.py:29-30` — `current_admin` raises `403 admin_required` for any `role != "admin"`. The agent service account is `role=agent` (`docs/agents-add-model-runbook.md:16`), so it is refused.
- `apps/api/tests/test_openapi_agent_surface.py:257-273` lists all four category write routes in `_GOVERNANCE_ROUTES`, and `test_governance_routes_absent_from_agent_write_set` (`:287-294`) asserts they never carry the `agent-write` tag. The router's own docstring states the rule: *"Admin-only (`current_admin`); never agent-writable"* (`:160`).
- **Reads:** `GET /api/categories` and `GET /api/categories/{slug}` are on the public router (`sot/router.py:107,136`) but are **authenticated** SoT reads — not in `_PUBLIC_ROUTES` — so the agent (holding a valid `portal_access` cookie) **can** read them.

**Consequence for AC-5:** the agent-facing contract is a **negative capability statement plus a read affordance**. Any runbook text implying the agent can assign a category would be false against a green test.

### V-5 — The narrowed-out `docs/operations.md` + `cutover-smoke.sh` passages are **already corrected**. No edit is owed; the scan still is.

- `docs/operations.md:466-470` now carries the Story 49.3 correction verbatim: `/api/categories` hosts a *new* additive contract; the 47.5 retirement of the **recursive single-category taxonomy** stands.
- `docs/operations.md:619-625` explains the probe re-point and states both routes are equally auth-protected.
- `infra/scripts/cutover-smoke.sh:401-406` carries the matching comment and the probe stays on `/api/tags`.
- `docs/operations.md:426` remains — *"43 legacy categories (single-category taxonomy since retired by the Story 47.5 cutover — facet tags are the sole classification system)"*. This sits inside a dated **historical** block (`"As of 2026-05-05"`, `:421`) describing the SoT-migration end state. ⚠️ **The trailing clause "facet tags are the sole classification system" is true as of 2026-05-05 and false as of Initiative 26.** It is a historical-record sentence, so the honest repair is a dated pointer, not a rewrite of history — see AC-2, which bounds this to a **single parenthetical** and forbids restating the 2026-05-05 counts.

### V-6 — The "periodic QA checklist" already exists as **shipped software**. Do not write a parallel manual procedure.

Story 52.3 shipped a curation-QA panel on `/admin/categories` with a **fixed six-check order** (`52-3-curation-qa-surfaces.md:135`): (a) empty categories, (b) tiny categories, (c) label collisions, (d) over-categorized models, (e) uncategorized-models count, (f) ungrouped-tags count. Backing contracts, all shipped and named in that story: `GET /api/admin/models/over-categorized` (AC-1, `:168`), `GET /api/models?uncategorized=true` (`sot/router.py:176-183,209`), `useAdminCategories()`, `useTagGroups()`. The "1–3 categories" norm is a **suggestion surfaced as a warning, never an error** (`52-3:186` AC-13). A zero-category model is a **valid, public** state (`52-3:187` AC-14, `sot/router.py:181`).

**Consequence:** AC-4's checklist is *cadence + how to read each of the six rows + what action each implies*, anchored to the shipped order. Inventing a seventh check, or restating the six as manual `curl` recipes, duplicates shipped software and is forbidden by D-3.

### V-7 — The LWW posture exists **only** in planning artifacts. Live documentation carries none of it.

`architecture.md:3340` and `epics.md:4489` carry the full corrected posture (LWW *does* permit a lost update; the justification is post-hoc auditability, not absence of the race; the named trigger is a second concurrent admin editor **or** an automated/agent writer, at which point a `revision` integer or ETag/`If-Match` → `409` is owed). `grep -rni --include=*.md 'last-writer-wins|last writer wins|\bLWW\b' docs/` → **0 hits**.

`docs/concurrency-patterns.md` is a **pattern index of solutions** (CC1–CC6, each ≤25 lines with an in-repo citation, `:1-8`). An accepted-risk posture is not a reusable primitive, so it does **not** belong there — see D-5, which records that decision so a dev does not add a CC7.

### V-8 — The eight shipped categories, and where their canonical text lives.

`apps/api/app/core/db/seed.py:282-361` — `STARTER_BROWSE_CATEGORIES`, ordered by `position` 0…7:

| pos | slug | `name_pl` | `name_en` |
|---|---|---|---|
| 0 | `storage-organization` | Przechowywanie i organizacja | Storage & Organization |
| 1 | `home-decor` | Dekoracje i wystrój | Home Decor |
| 2 | `holders-mounts` | Uchwyty i mocowania | Holders & Mounts |
| 3 | `electronics-cables` | Elektronika i kable | Electronics & Cables |
| 4 | `tools-workshop` | Narzędzia i warsztat | Tools & Workshop |
| 5 | `printer-3d` | Drukarka 3D i akcesoria | 3D Printer & Accessories |
| 6 | `toys-games` | Zabawki, gry i figurki | Toys, Games & Figures |
| 7 | `replacement-parts` | Części zamienne | Replacement Parts |

- **`inclusion_criterion` is stored as canonical ENGLISH only** (`seed.py:267-273`); "bilingual" applies to the *labels*. The seed applied exactly two normalisations to the EXPERIENCE.md sentences (strip `*` emphasis — affects only `storage-organization`; capitalise the first letter) and preserved everything else byte-for-byte, *including* the `printer-3d` em dash and the `toys-games` Oxford comma.
- **Positive / boundary examples, the collision table and the rejected-candidates table** are in `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md:95-187`. They exist **nowhere in `docs/`** and nowhere in the database — `description_en` / `description_pl` were deliberately left unseeded (`seed.py:278-281`).
- **`replacement-parts` clears the ≥3-models bar at exactly three** and is registered as a tiny-category monitoring item (`seed.py:257-260`) — the governance doc must carry this, because it is the one row a curator might otherwise "fix".
- The seed is **create-if-absent by slug and never updates an existing row** (`seed.py:367-370`), so editing `seed.py` does **not** propagate to a live category: admin governance wins. Any doc sentence implying the seed is the running source of truth would be false.

### V-9 — `docs/index.md` has a "Generated Documentation" list that a new top-level doc must join.

`docs/index.md:47-61` lists `project-overview.md`, `architecture.md`, `source-tree-analysis.md`, `operations.md`, then a "Spec & Plans (pre-existing)" block. A new living doc that is not listed there is invisible to the index's own stated purpose (*"Primary navigation hub for AI agents and human readers"*, `:4`). One line is owed; the rest of the file is out of scope (§ 0.2).

### V-10 — ⚠️ The deploy skip-gate matches the commit subject **literally**, so `docs(catalog):` would trigger a deploy.

`infra/scripts/deploy.sh:23` — `SKIP_PREFIXES=("docs:" "chore:" "wip:")`; `:55` — `[[ "$subject" == "$prefix"* ]]`. A scoped conventional subject such as `docs(catalog): …` does **not** match `docs:` and would fire a full build+deploy for a documentation-only change. Recent in-repo precedent uses the bare form: `a3aaf35 docs: close story 53.1`, `513f4bd docs: close story 52.3 after deploy`. Captured as a constraint in § 5, not as an AC, because the commit is the controller's act and not part of the dev pass's deliverable.

---

## 3. Scope — the files and the source map

### 3.1 In-scope files (exactly five, plus one ledger amendment)

| File | Action | Bound |
|---|---|---|
| `docs/architecture.md` | EDIT | Add a short classification section + touch the two sentences named in V-1. ~20–30 added lines. |
| `docs/agents-add-model-runbook.md` | EDIT | Add one § "Browse categories — what the agent may and may not do"; fix the V-3 falsehood. |
| `docs/browse-category-governance.md` | **NEW** | The FR26-GOV-1 governance publication (D-1). |
| `docs/index.md` | EDIT | Exactly one line (AC-8). |
| `docs/operations.md` | EDIT | **AC-2 only** — one parenthetical on the trailing clause at `:426-427`. Every other line byte-unchanged. Droppable by controller ruling (§ 16 R-1). |
| `_bmad-output/implementation-artifacts/deferred-work.md` | AMEND | Re-point the two entries that name Story 54.3 (§ 12 / D-8). Owner field + status prose only. |

> **Reconciliation note (validate pass).** The create pass listed "exactly four" here and omitted `docs/operations.md`, while AC-2 mandated an edit to it and § 7 predicted it. A dev following § 3.1 would have scored AC-2's edit as a scope breach; a dev following § 7 would have made it. The tables are now consistent: **five files + one ledger amendment**, and `docs/operations.md` is bounded to AC-2.

### 3.2 Source map — the documents this story is answerable to

| Claim to be published | Canonical source | Rule |
|---|---|---|
| The eight categories: slug, both labels, `position`, `inclusion_criterion` | `apps/api/app/core/db/seed.py:282-361` | **Byte-exact transcription.** If the doc and the seed disagree, the doc is wrong. |
| Positive examples, boundary/non-examples with tie-breaks, crossed tag groups | `…/ux-3d-portal-2026-07-26/EXPERIENCE.md:101-156` | Transcribe; do not invent new examples. |
| Category ↔ Tag label collisions and their resolutions | `EXPERIENCE.md:158-171` | Transcribe the eight-row table. |
| Rejected candidates and why | `EXPERIENCE.md:173-186` | Transcribe. |
| Category-vs-Tag distinction rule | `EXPERIENCE.md:158-171` + `prd.md:2255` (FR26-GOV-1) | State as a rule, then show it working via the collision table. |
| Flat MVP, depth-2 schema ceiling, never a DAG, no third level | `prd.md:2247` (FR26-CAT-4) | State the product rule and the schema affordance separately. |
| M:N, optional, independent of tags; zero categories is valid and public | `sot/router.py:174-183`, `52-3:187`, `architecture.md` Decision AY | Verified behaviour, not aspiration. |
| LWW posture + named upgrade trigger | `architecture.md:3340` | Reproduce the **corrected** posture; the retracted "no lost-update ambiguity" claim must not reappear. |
| Six-check QA panel + the 1–3 norm as a warning | `52-3-curation-qa-surfaces.md:135,168,186-187` | Point at the shipped panel (D-3). |
| Agent capability boundary | `browse_category_admin_router.py`, `dependencies.py:29-30`, `test_openapi_agent_surface.py:257-294` | Negative statement + read affordance (D-4). |
| The ≥3-models distribution evidence and its non-reproducibility | `seed.py:250-265` | State the conclusion, cite the seed comment, **name the evidence as local/gitignored** (§ 0.1). |

---

## 4. Acceptance Criteria

1. **AC-1 — `docs/architecture.md` distinguishes the two taxonomies.** The file gains a classification section that states, in this order: (a) the **retired** Initiative 25 model — one mandatory recursive `category` per model, dropped by Alembic `0019_drop_category` at the Story 47.5 cutover, **not coming back**; (b) the **current** model — facet-grouped tags (`tag`, `tag_group`, `model_tag`) **and**, independently, browse categories (`browse_category`, `model_browse_category`) in a **many-to-many, optional** relationship where a model may carry zero, one or many categories; (c) that a model with zero categories is a **valid, publicly visible** state, not an error. The § "Container responsibilities" API sentence (`:26`) and the § "Data flow" sentence (`:34`) are updated to name the two new tables. **No claim in the section may lack a shipped antecedent** (§ 3.2).

2. **AC-2 — The one remaining stale clause in `docs/operations.md:426-427` is bounded and dated, and it narrowly amends Story 49.3 § 6 F-7 *by name*.** This AC is the recorded **disposition of an AC-9 scan hit**, not re-adopted narrowed-out scope — see the validate ruling at § 16 R-1.

   **What is edited:** the trailing clause *"facet tags are the sole classification system"* only, qualified by **one** parenthetical noting that the clause describes the pre-Initiative-26 state and that browse categories are now a second, independent classification layer.

   **Binding constraints, inherited verbatim from Story 49.3 AC-25 / § 6 F-7 — the ruling this AC amends:**
   - The **first** clause (*"single-category taxonomy since retired by the Story 47.5 cutover"*) is **byte-unchanged**. It is true, permanently.
   - The parenthetical **must not** imply, by wording or by omission, that the mandatory single-category taxonomy returned. That was F-7's entire concern and it remains binding.
   - The `43 legacy categories` figure, the `**As of 2026-05-05**` frame, the surrounding historical block and **every other line of `docs/operations.md`** are **byte-unchanged**.

   **The diff must state, in the commit body or an inline note, that this narrowly amends 49.3 § 6 F-7** — F-7 correctly protected the first clause and correctly refused a rewrite; it did not separately rule on the trailing clause, which was already false at 49.3's own deploy. Silently overturning a `done`, reviewed story's explicit ruling is forbidden (§ 5 "Never invent a second competing ruling"; D-2).

   If the controller overrules § 16 R-1, AC-2 is dropped, the hit is routed to `deferred-work.md` by AC-9, and it must **not** be silently expanded into an operations.md rewrite (§ 0.2).

3. **AC-3 — `docs/browse-category-governance.md` publishes the FR26-GOV-1 payload.** It contains, per category, all eight rows in `position` order: slug, `name_pl`, `name_en`, the canonical **English** `inclusion_criterion`, positive examples, boundary/non-examples **with the tie-break reason**, and the tag groups it crosses. Plus, once each: the Category-vs-Tag distinction rule; the eight-row label-collision table with resolutions; the rejected-candidates table; the flat-MVP / depth-2-ceiling rule; the `replacement-parts` zero-margin monitoring note; and an explicit statement that `inclusion_criterion` is English-only by design while labels are bilingual.

4. **AC-4 — The periodic QA checklist is operating instructions for the shipped panel, plus a cadence.** It names `/admin/categories` and the six checks **in the shipped order** (empty → tiny → label collisions → over-categorized → uncategorized count → ungrouped tags), states for each what action it implies, states that the **1–3 category norm is a warning and never an error**, states that zero categories is valid and public, and proposes a review cadence with the reasoning for it. It introduces **no new check** and **no manual `curl` procedure that duplicates a panel row** (D-3).

5. **AC-5 — The runbook gains a truthful agent-facing category contract.** A new subsection states: the agent **may read** `GET /api/categories` and `GET /api/categories/{slug}` with its session cookie; the agent **may not** create, rename, reorder, delete or assign categories — every such route is `current_admin` and returns **`403 admin_required`** to `role=agent`; assignment is `PUT /api/admin/models/{model_id}/categories`, **admin-only, replace-set**; and therefore, as with tags and photos, **the import flow leaves a model uncategorized by default**, which is a valid state the operator curates later. Every claim cites its route/dependency/test (§ 2 V-4). The subsection **must not** be contradicted by the existing § "Behavioral Notes → Auth role gating" (`:356`) — if that sentence needs a clause to stay true, add it.

6. **AC-6 — The runbook's `GET /api/models/{model_id}` auth claim is corrected.** `docs/agents-add-model-runbook.md:398` no longer says "unauthenticated"; it says the fetch reuses the session cookie, consistent with `sot/router.py:248-252` and `main.py:50-61`. The diff notes this is a **pre-existing Initiative-11 default-deny defect, not Initiative 26 scope**. The surrounding poll loop, budgets and escalation guidance are otherwise unchanged — and the `curl` in that step is updated to actually send the cookie jar if it does not already.

7. **AC-7 — The LWW concurrency posture is published with its upgrade trigger, in its corrected form.** The governance doc states: assignment is replace-set and **last-writer-wins**; LWW **does permit a lost update** (the A-adds-`lamps` / B-adds-`kitchen` worked example); the accepted justification is that every write emits an audit row carrying the resulting set, making a lost update **recoverable and attributable after the fact**, *not* that the race is absent; and the **named trigger** — a second concurrent admin editor **or** an automated/agent writer — at which point optimistic concurrency (a `revision` integer or ETag / `If-Match` → `409`) is owed. The retracted claim that replace-set has "no lost-update ambiguity" **must not appear**. No code implements any of this in this story.

8. **AC-8 — `docs/index.md` gains exactly one line** pointing at the new governance doc, matching the existing `- [Title](./file.md) — one-line hook.` shape. No other line of that file changes.

   **Section choice is the dev's call, and it must be justified in one line in § 14.** The create pass mandated § "Generated Documentation" (`docs/index.md:47-51`); the validate pass rules that heading **factually wrong** for this file — that section lists `bmad-document-project` output (`project-overview.md`, `source-tree-analysis.md`, …) and `browse-category-governance.md` is hand-authored living reference. The closer in-file precedent is `agents-add-model-runbook.md`, a hand-authored living doc that sits under § "Spec & Plans (pre-existing)" (`:59`) — a heading that is also not a clean fit. **Pick the section whose heading is true of the file, or add a correctly-named one-line heading; do not file it under a heading that misdescribes it** — that would be exactly the small, confident falsehood this story exists to remove. Adding a heading is the one permitted departure from "no other line changes".

9. **AC-9 — The epic:47 CUTOVER-CHECKLIST scan is executed and recorded.** The Dev Agent Record states, with commands and output, that operational probes (`infra/scripts/*.sh`) and live documentation (`docs/**/*.md`, root `*.md`) were scanned for residual references that Initiative 26 makes false, and lists every hit with its disposition (corrected / historical-and-qualified / no action + why). The `sprint-status.yaml:540` action item is annotated with the **Initiative-26 instance being discharged**; because it is a **standing discipline for future endpoint-retirement stories**, its `status:` stays `open` — closing it would be a false claim (D-7).

10. **AC-10 — No product behaviour changes and the mandatory gates stay green.** Zero files under `apps/`, `workers/`, `infra/` are modified except as AC-9's read-only scan (which modifies nothing). Zero locale keys, zero `__snapshots__/**/*.png`. `infra/scripts/check-all.sh` is run on the story branch and reported **16/16** with its real output; a docs-only change must not perturb it, and if it does, that is a finding, not a rounding error.

11. **AC-11 — The two ledger entries that name Story 54.3 are explicitly re-pointed, not silently inherited — and they are re-pointed *differently*.** Both keep `status: **OPEN**` and both gain a one-line reason naming this story as docs-only.
    - `deferred-work.md:376` (screenshot-visibility census) → **"a controller-assigned follow-up"**, the alternative the entry itself already offers. The census figure is **not** carried forward as prose — the ledger's own instruction is to re-run the script for a current number.
    - `deferred-work.md:381` (`filter-ribbon-selects-open.spec.ts` rename) → **"E54 visual-spec hygiene pass"**, the only alternative owner that entry names. It offers **no** controller-follow-up option, so inventing one would be a second competing ruling on someone else's ledger entry (D-8). The corrected figure **12** already stands and is not restated.

12. **AC-12 — Evidence honesty, stated in the artifact.** The Dev Agent Record carries an explicit statement that: no physical Android Chrome smoke was run or claimed; `G26-LIB` remains 🔓 OPEN and nothing in this story bears on it; no human reviewed anything; and every governance sentence is traceable to § 3.2's source map. Any sentence the dev could not ground is listed as **not written** rather than written with a hedge.

---

## 5. Boundaries & Constraints

### Never

- **Never** edit `apps/**`, `workers/**`, `infra/**`, `apps/web/src/locales/*.json`, or any `__snapshots__/**/*.png`. This story has no product surface.
- **Never** edit `apps/api/app/core/db/seed.py` to "align" it with the doc. The seed is the source; the doc follows. And the seed does not propagate to existing rows anyway (V-8).
- **Never** claim a category set decision, a rename, a merge or a retirement. Those are Story 49.5 admin governance at runtime.
- **Never** write a sentence implying physical-device verification, human review, Ezop sign-off, or that `G26-LIB` moved.
- **Never** invent a governance example, boundary case or crossed-tag-group that is not in `EXPERIENCE.md` — the tie-breaks were argued once and re-deriving them creates a second, competing ruling.
- **Never** state or imply that the ≥3-models distribution evidence can be re-derived from this repository (§ 0.1).
- **Never** add a CC7 to `docs/concurrency-patterns.md` (D-5).
- **Never** restate the six QA checks as manual procedures (D-3).

### Ask First

- **Any edit to `docs/operations.md` beyond AC-2's single parenthetical.** That file was Story 49.3's and 3.3's; a broader touch needs a ruling.
- **Any new top-level `docs/` file beyond `browse-category-governance.md`.**
- **Any change to `AGENTS.md` or `_bmad-output/project-context.md`.** If the governance rule turns out to have cross-agent reach, propose it and stop — `project-context.md` is regenerated by its own skill (`:319`), not hand-patched wholesale.

### Constraints

- **English only in committed content** (`project-context.md:154`). The governance doc is in English; Polish appears only as `name_pl` values and quoted tag labels.
- **Doc conventions** (`project-context.md:156`, `AGENTS.md:18-22`): `docs/design/` is dated specs, `docs/plans/` is gitignored plans, top-level `docs/*.md` is living reference. The governance doc is living reference → top level (D-1).
- **Commit subject must be bare `docs:`** to hit the deploy skip-gate. `docs(catalog):` does **not** match and would fire a full build+deploy (V-10). Precedent: `a3aaf35`, `513f4bd`.
- **Branch naming**: `docs/<short-topic>` per `project-context.md:163` — e.g. `docs/E54.3-rollout-docs-governance`. ff-only merge, no squash.
- **No `--no-verify`** (`project-context.md:167`). A docs-only commit touches no PNG, so the baseline-review hook has nothing to demand; if it fires, that is a signal something outside scope got staged.

---

## 6. Decisions

- **D-1 — The governance doc lives at `docs/browse-category-governance.md`** (top-level, living reference), **not** `docs/design/<date>-…` and **not** `docs/plans/…`. Rationale: `docs/design/` holds dated point-in-time specs and `docs/plans/` is gitignored (`project-context.md:267`); this document must be *current* and *readable by an agent at any future date*, which is exactly the `architecture.md` / `operations.md` slot. Consequence: it joins `docs/index.md` (AC-8).

- **D-2 — The governance doc is a projection of shipped state, not a new decision.** Its category rows are byte-exact against `seed.py`; its examples are transcribed from `EXPERIENCE.md`. Where the two sources disagree in wording, `seed.py` wins for the criterion sentence (it is what the database and the admin UI show) and `EXPERIENCE.md` wins for everything it alone carries. Any divergence found during the dev pass is **reported**, not reconciled by choosing a third wording.

- **D-3 — The periodic QA checklist points at the shipped 52.3 panel.** Writing a parallel manual procedure would create a second, drifting definition of "healthy taxonomy" the moment either changes, and would duplicate software that already computes the answers. The checklist's value-add is **cadence and interpretation**, which no panel provides.

- **D-4 — The agent-facing category contract is a negative capability statement.** Modelled on the existing `:357` "Import flow does NOT touch tags or photos" note. Stating what the agent *cannot* do, with the `403` and its test citation, is both true and more useful than a recipe the agent would be refused on.

- **D-5 — The LWW posture goes in the governance doc, not `docs/concurrency-patterns.md`.** That file is an index of *reusable solution shapes* with in-repo precedents (`:1-8`); "we accepted this race and here is the trigger that ends the acceptance" is a governance posture, not a primitive. Recording the decision here prevents a well-meaning CC7.

- **D-6 — `docs/architecture.md` gains a section, not a rewrite.** The file is a 57-line condensation that explicitly defers to `docs/design/2026-04-29-portal-design.md` (`:3`). The classification distinction is the smallest edit that makes it truthful; component topology, the future-proofing table and the references block are untouched.

- **D-7 — The epic:47 action item is discharged *for Initiative 26* and stays `open` as standing discipline.** Its text is explicitly forward-looking (*"future endpoint-retirement stories must…"*, `sprint-status.yaml:540`). Marking it `done` because one story complied would delete a standing rule. AC-9 annotates; it does not close.

- **D-8 — The two test-hygiene ledger entries are routed OUT of this story.** The census sweep is ~69 call-site edits across ~40 specs; the `filter-ribbon-selects-open.spec.ts` rename touches a `__snapshots__/` directory and therefore the baseline-review gate. Either one converts a docs-only, deploy-skipping story into a test refactor with PNG exposure — and neither has any documentation content.

  **Asymmetry the validate pass corrected — the two entries are NOT equivalent.** Entry A (`deferred-work.md:376`) already offers *"or a controller-assigned follow-up"* as an alternative owner, so AC-11 merely takes an option the ledger pre-authorised. Entry B (`deferred-work.md:381`) reads *"Owner: E54 visual-spec hygiene pass / Story 54.3."* — it offers **no** controller-follow-up alternative, and the create pass's claim that "both ledger entries already offer" one was **false**. Re-pointing B is therefore a genuine re-route, not the exercise of a pre-offered option: AC-11 must move it to the **"E54 visual-spec hygiene pass"** owner the ledger *does* name, and record that Story 54.3 declined it as docs-only. In a story whose charter is literal traceability, this distinction is the difference between citing the ledger and paraphrasing it.

---

## 7. Predicted file set

| File | Change | Predicted size |
|---|---|---|
| `docs/architecture.md` | EDIT — new classification section; two sentences updated (`:26`, `:34`) | +20–30 lines |
| `docs/agents-add-model-runbook.md` | EDIT — new category subsection; V-3 one-line fix at `:398`; possible clause on `:356` | +25–40 lines, 1–2 lines changed |
| `docs/browse-category-governance.md` | **NEW** | ~150–220 lines |
| `docs/index.md` | EDIT — one line, section justified per AC-8 (+ optionally one new heading) | +1–2 lines |
| `docs/operations.md` | EDIT — one parenthetical on the trailing clause at `:426-427` (AC-2; **ADOPTED** by § 16 R-1, droppable only by controller ruling) | ≤2 lines |
| `_bmad-output/implementation-artifacts/deferred-work.md` | AMEND — owner/status prose on two entries | ~4 lines |
| `_bmad-output/implementation-artifacts/54-3-rollout-docs-governance.md` | Dev Agent Record § 14 | — |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Status transitions | 1–2 lines |

**Anything outside this table is a scope breach.** In particular: zero files under `apps/`, `workers/`, `infra/`.

---

## 8. Tasks / Subtasks

- [x] **T1 — Re-verify § 2 against the tree you actually have.** (AC-1, AC-3, AC-5, AC-6)
  - [x] Re-run the V-1/V-2 greps, the V-3 route/`_PUBLIC_ROUTES` trace, and the V-4 router/dependency/test trace. If any figure moved since `1906498`, record the divergence in § 14 rather than proceeding on this file's number.
  - [x] Read `seed.py:250-361` and `EXPERIENCE.md:95-187` in full before writing any governance prose.

- [x] **T2 — Write `docs/browse-category-governance.md`.** (AC-3, AC-7)
  - [x] Header: what this document governs, what it does not (it is not the admin API reference, not the UX spec), and where the runtime source of truth is (the database, via `/admin/categories` — **not** `seed.py`).
  - [x] The Category-vs-Tag distinction rule, stated once and plainly, before the category rows.
  - [x] Eight category entries in `position` order, per AC-3. Criterion sentences transcribed byte-exact from `seed.py`.
  - [x] Label-collision table (8 rows) and rejected-candidates table, transcribed from `EXPERIENCE.md:158-186`.
  - [x] Flat-MVP / depth-2-ceiling / never-a-DAG rule (`prd.md:2247`), separating the **product** rule from the **schema** affordance.
  - [x] `replacement-parts` zero-margin monitoring note (`seed.py:257-260`).
  - [x] LWW posture + worked lost-update example + audit-row justification + named upgrade trigger (AC-7).
  - [x] Evidence-provenance note: the ≥3-models check was run against a live capture whose artefacts are local/gitignored and are **not** reproducible from this repo (§ 0.1).

- [x] **T3 — Write the periodic QA checklist section of the governance doc.** (AC-4)
  - [x] Name `/admin/categories`, the six checks in shipped order, the action each implies, the 1–3-warning-not-error rule, and the zero-categories-is-valid rule.
  - [x] Propose a cadence **with its reasoning** (e.g. tied to import batches rather than a calendar, if that is what the evidence supports) — and say plainly that no automation enforces it.

- [x] **T4 — Edit `docs/architecture.md`.** (AC-1)
  - [x] Add the classification section per AC-1 (a)/(b)/(c).
  - [x] Update the `:26` SoT-entity-tables sentence and the `:34` data-flow sentence to name `browse_category` / `model_browse_category`.
  - [x] Add a pointer to `docs/browse-category-governance.md` in § "References".

- [x] **T5 — Edit `docs/agents-add-model-runbook.md`.** (AC-5, AC-6)
  - [x] Add § "Browse categories — what the agent may and may not do" under § "Behavioral Notes", adjacent to the existing tags/photos note.
  - [x] Fix the `:398` "unauthenticated" claim and its `curl` (AC-6), with the pre-existing-defect attribution in the diff.
  - [x] Re-read `:356` "Auth role gating" and add a clause if the new subsection would otherwise contradict it.

- [x] **T6 — `docs/operations.md` single parenthetical + `docs/index.md` single line.** (AC-2, AC-8)

- [x] **T7 — Execute and record the epic:47 cutover scan.** (AC-9)
  - [x] Run the § 9 scan commands over `docs/`, root `*.md` and `infra/scripts/`.
  - [x] Table every hit with its disposition. Annotate `sprint-status.yaml:540` with the Initiative-26 discharge; leave `status: open`.

- [x] **T8 — Amend the two deferred-work entries.** (AC-11)
  - [x] Re-point owners off Story 54.3, keep `status: OPEN`, do **not** carry the `69` figure forward as fact.

- [x] **T9 — Gates and record.** (AC-10, AC-12)
  - [x] `infra/scripts/check-all.sh`; report the real 16/16 line and paste the output.
  - [x] `git diff --stat` proving zero `apps/` / `workers/` / `infra/` and zero PNG changes.
  - [x] Write § 14 including the AC-12 honesty statement and the list of anything deliberately **not** written for lack of grounding.

---

## 9. Verification plan

```bash
# T1 — re-verify the create-time traces
grep -ic categor docs/architecture.md                      # expect 0 at 1906498
grep -ic categor docs/agents-add-model-runbook.md          # expect 0 at 1906498
grep -n "unauthenticated" docs/agents-add-model-runbook.md # expect 1 hit at :398
grep -n "current_admin" apps/api/app/modules/sot/browse_category_admin_router.py
sed -n '50,61p' apps/api/app/main.py                       # _PUBLIC_ROUTES — no /api/models*
grep -rni --include='*.md' 'last-writer-wins\|last writer wins\|\bLWW\b' docs/   # expect 0 before T2

# T2 — governance content must match the shipped seed byte-for-byte
sed -n '282,361p' apps/api/app/core/db/seed.py

# T7 / AC-9 — the epic:47 cutover scan (read-only)
grep -rni --include='*.md' 'categor' docs/ *.md
grep -rn 'categor' infra/scripts/
grep -rn '/api/categories' infra/ docs/

# T9 / AC-10 — gates and the zero-product-diff proof
infra/scripts/check-all.sh
git diff --stat main...HEAD
git diff --name-only main...HEAD | grep -E '^(apps|workers|infra)/'   # expect NO output
git diff --name-only main...HEAD | grep -E '\.png$'                    # expect NO output
```

**Reporting rule:** paste real output. "check-all passed" without the 16/16 line is not evidence (`project-context.md:192-193`).

---

## 10. Dev Notes

- **The failure mode here is a confident false sentence, not a red gate.** Nothing in this story can turn `check-all` red, which means the gate provides almost no protection. § 3.2's source map is the substitute: if a sentence cannot be traced to a row there, it does not get written.
- **`seed.py` is not the running source of truth.** It is create-if-absent by slug and never updates (`:367-370`). A live category's label or criterion may already differ from the seed if an admin renamed it. The governance doc must say where the current values live (`GET /api/admin/categories`, which returns `inclusion_criterion`; `browse_category_admin_router.py:88-94`) and present the seeded text as the **as-seeded** baseline.
- **The public read deliberately omits `inclusion_criterion`** (`sot/schemas.py:114`, Decision AY); only the admin read carries it (`:126,:133`). So the criterion is an **admin-facing admission test**, not public copy — the governance doc should not imply end users see it.
- **`ModelSummary` deliberately carries no `categories`** (`52-3:52`, Decision AY at `architecture.md:3312`). Do not write a sentence implying list views show a model's categories; only `ModelDetail` does.
- **`uncategorized=true` is a pure AND** across tags and categories (`sot/router.py:176-183`) — "no tags AND no categories", never a union. If the QA checklist describes that row, describe it correctly.
- **Depth-2 is enforced in the service layer, not the schema** — SQLite DDL cannot express it (`epics.md:4494`). Say which layer enforces what; conflating them is the kind of small lie this story exists to remove.
- **Terminology consistency is a shipped constraint, not a style preference.** Story 54.1 audited cross-surface terminology; the governance doc must use the same Polish nouns the UI uses for the same concepts, or it becomes the ninth surface with a ninth register.
- **Two ledger entries about *this* documentation family remain OPEN and are not this story's**: the `catalog.gallery.*` / `viewer3d.*` copy-register decisions (`deferred-work.md:340`). They are i18n copy, not governance. Do not absorb them.

### Project Structure Notes

- New file lands at `docs/browse-category-governance.md` — consistent with `AGENTS.md:18-22`'s tree, where top-level `docs/*.md` are the living reference docs and dated specs live under `docs/design/`.
- No `apps/web/src/` path is touched, so no route-tree regeneration and no `*.gen.ts` concern applies.
- `docs/plans/` is gitignored (`project-context.md:267`) — nothing this story writes may land there.

### References

- `_bmad-output/planning-artifacts/epics.md:4581-4599` — Epic E54 and the Story 54.3 sketch (incl. the 2026-07-26 narrowing).
- `_bmad-output/planning-artifacts/prd.md:2247` (FR26-CAT-4), `:2255` (FR26-GOV-1), `:2301` (gate register).
- `_bmad-output/planning-artifacts/architecture.md:3289` (entity shape), `:3340` (LWW posture), `:3386` (`G26-DEVGO`, `G26-LIB`).
- `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md:88-194` — category set, per-category governance record, collisions, rejected candidates, open obligation.
- `apps/api/app/core/db/seed.py:250-374` — `STARTER_BROWSE_CATEGORIES` + `seed_browse_categories`.
- `apps/api/app/modules/sot/router.py:107-183,236-252` — public category reads, `uncategorized`, model detail auth.
- `apps/api/app/modules/sot/browse_category_admin_router.py` — admin governance + replace-set assignment.
- `apps/api/app/core/auth/dependencies.py:29-30`, `apps/api/app/main.py:50-61` — role gating and the public allowlist.
- `apps/api/tests/test_openapi_agent_surface.py:257-294` — the never-`agent-write` assertion.
- `_bmad-output/implementation-artifacts/52-3-curation-qa-surfaces.md:46-52,135,168,186-187` — the shipped six-check QA panel.
- `_bmad-output/implementation-artifacts/deferred-work.md:373-381` — the two entries routed out by D-8.
- `_bmad-output/implementation-artifacts/sprint-status.yaml:540` — the epic:47 CUTOVER-CHECKLIST action item.
- `docs/operations.md:421-430,460-471,613-625`, `infra/scripts/cutover-smoke.sh:395-406` — the Story 49.3 corrections this story verifies but does not redo.

---

## 11. Story Creation Questions — RULED by the validate pass (2026-07-31)

- **Q-1 — Status at create: `ready-for-validation`, not the template's `ready-for-dev`.** ✅ **CONFIRMED.** The precedent is exact and verified: `54-2-a11y-and-visual-audit.md:16` — *"Status was `ready-for-validation` at create time. FLIPPED to `ready-for-dev` on 2026-07-31 by the native `bmad-create-story` Validate (VS) pass"* — and its § 17.2 / § 18 record the same division of labour. The create pass was right; this VS pass owns the flip. `G26-DEVGO` stays 🔓 open regardless (§ 16 R-6).
- **Q-2 — No subagents were used.** ✅ **CONFIRMED, no deviation to record.** The controller directive governs, and the traces verify: this validate pass independently re-measured **every** § 2 item inline (V-1 … V-10) and found them accurate — see § 16.1. Inline measurement produced correct results, so the workflow's subagent invitation was an optimisation, not a correctness requirement.
- **Q-3 — Is AC-2 (`docs/operations.md:426-427`) in scope?** ✅ **ADOPTED, MODIFIED.** Full ruling and reasoning at **§ 16 R-1**. Summary: the finding is real, but the create pass's justification was wrong — 49.3 did not "correctly leave it", it **explicitly ruled against editing it** (§ 6 F-7, review-concurred). AC-2 is rewritten to amend that ruling by name, to touch the trailing clause only, to inherit 49.3's AC-25 constraint, and to be the recorded disposition of an AC-9 scan hit.
- **Q-4 — Is AC-6 (the runbook's false "unauthenticated") in scope?** ✅ **ADOPTED as written.** Independently re-verified three ways (§ 16.1 V-3). The alternative is to close Initiative 26 having edited `docs/agents-add-model-runbook.md` while knowingly leaving a false auth claim in it, 350 lines from the subsection AC-5 adds. One line, same file, same doc-honesty family, `docs/operations.md:464-465` already states the opposite. Routing it out would be the more expensive and less honest choice. AC-6's requirement to attribute it as a **pre-existing Initiative-11 defect** is what keeps this from being scope creep.
- **Q-5 — Cadence for the periodic QA review (AC-4).** ✅ **CONFIRMED: (a) event-driven, binding; (b) monthly, as an explicitly-labelled backstop.** The story's own reasoning is sound and is the only option grounded in evidence: every one of the six checks is a curation-drift signal, and curation drift is caused by catalogue movement, not by the calendar. A pure calendar cadence would fire six no-op checks in a month with no imports and miss a 40-model batch landing on day 2. AC-4's existing requirement to state the reasoning stands — **and the doc must say plainly that nothing automates either cadence.**
- **Q-6 — Does the governance doc need a Polish rendition?** ✅ **CONFIRMED: English-only.** `project-context.md:154` is unambiguous and admits no per-audience exception. `name_pl` values and quoted Polish tag labels appear as **data**, which is not a rendition. Noted for the record: the operator-facing concern is real but is a `docs/` policy question, not this story's to settle — and § 5 already forbids touching `AGENTS.md` / `project-context.md`. If the operator wants Polish operating docs, that is a routed follow-up, not an AC here.

### Risks

| Risk | Why it bites | Mitigation in this spec |
|---|---|---|
| Governance doc drifts from the DB the day an admin renames a category | The seed does not propagate (V-8); a doc that presents seeded text as current becomes false silently | AC-3 + Dev Notes require the doc to name `GET /api/admin/categories` as the runtime source and label the transcription as the as-seeded baseline |
| The checklist duplicates the shipped panel and the two diverge | Two definitions of "healthy taxonomy" | D-3 + AC-4 forbid new checks and manual duplicates; the shipped six-check order is the anchor |
| Scope creep into `docs/operations.md` or a test-hygiene sweep | Both are adjacent and both are large | § 0.2, D-8, AC-11, and the § 7 file table make anything outside it a breach |
| A "rollout complete" flourish implies device verification | The story's own title contains "Rollout" | § 0.1 + AC-12; `G26-LIB` open and no Android evidence, stated in the record |
| Re-deriving an EXPERIENCE.md tie-break differently | Creates a second competing ruling on the same boundary case | D-2 + § 5 "Never invent a governance example" |

---

## 12. Deferred-work triage — what this story adopts, what it routes out

| # | Ledger entry | Disposition |
|---|---|---|
| A | `deferred-work.md:373-376` — 69 of 132 screenshot occurrences lack an explicit `toBeVisible()`; owner *"E54 test-hygiene pass / Story 54.3 or a controller-assigned follow-up"* | **ROUTED OUT** (D-8). ~69 call-site edits across ~40 specs, zero documentation content, own review surface. AC-11 amends the owner. Status stays OPEN. The `69` is **not** carried forward as prose — re-run the census script for a current figure. |
| B | `deferred-work.md:378-381` — rename/correct the `filter-ribbon-selects-open.spec.ts` baseline count (measured **12**, not 18); owner *"E54 visual-spec hygiene pass / Story 54.3."* — **no controller-follow-up alternative offered** (validate-pass correction, D-8) | **ROUTED OUT** (D-8). Touches `__snapshots__/`, therefore the baseline-review gate, in a story that must ship zero PNG churn. AC-11 re-points it to the **"E54 visual-spec hygiene pass"** owner the ledger already names, recording that 54.3 declined it as docs-only. Status stays OPEN; the corrected figure **12** already stands in the ledger. |
| C | `deferred-work.md:340` — `catalog.gallery.*` vs `catalog.image_viewer.*` noun, `viewer3d.*` register | **NOT ADOPTED.** i18n copy, not governance; already routed away from E54's audit stories. No action. |
| D | `deferred-work.md:349-371` — the four contrast/target-size findings and the over-photo scrim question | **NOT ADOPTED.** Product/design surfaces with controller-assigned owners; no documentation content. No action. |
| E | `sprint-status.yaml:540` — epic:47 CUTOVER-CHECKLIST | **ADOPTED, partially.** AC-9 executes the Initiative-26 instance and annotates it. `status:` stays `open` — it is standing discipline (D-7). |
| F | `sprint-status.yaml` epic:51 action items still `open` (51.1 `FacetSidebar` relocation → E52; 51.1 baseline provenance) | **NOT ADOPTED.** Product/commit-provenance items outside this story's file set. No action. |

---

## 13. Out of scope — named, so nobody re-derives them

- Any code, test, locale key, migration, seed edit or baseline.
- `docs/operations.md` beyond AC-2's single parenthetical; `infra/scripts/cutover-smoke.sh` in any form.
- The screenshot-visibility census sweep and the `filter-ribbon-selects-open.spec.ts` rename (§ 12 A/B).
- Any change to the eight-category set, their labels, order, criteria or parentage.
- Optimistic concurrency (`revision` / ETag / `If-Match` / `409`) — recorded as a future trigger only.
- A child-category level, or any UI for `parent_id` (FR26-CAT-4: flat MVP, depth-2 ceiling is schema affordance only).
- `AGENTS.md`, `_bmad-output/project-context.md`, `docs/concurrency-patterns.md` (D-5), and any `docs/index.md` line beyond AC-8's one.
- The epic-54 retrospective (`epic-54-retrospective: optional`) and any initiative-level close-out.
- Anything bearing on `G26-LIB`.

---

## 14. Dev Agent Record

### 14.1 Context Reference

Dev pass run 2026-07-31 by the native `bmad-dev-story` workflow, repo-local, on branch
`docs/E54.3-rollout-docs-governance` at `1906498` — **identical to this file's
`baseline_commit`**, so § 2's traces and this pass's re-measurement were taken against the same
tree. Session began with the mandatory native `bmad-help` routing call (`AGENTS.md:209`), which
returned `bmad-dev-story` as the next required skill (`_bmad/_config/bmad-help.csv`:
`bmad-create-story:validate` → `bmad-dev-story`, `required=true`).

Authorization: the controller issued per-story `G26-DEVGO` **for Story 54.3 only**, under the
standing Initiative 26 delegation. That is a **controller decision, not an Ezop/human review or
signature**, and it does **not** close `G26-LIB`.

No subagents were dispatched (controller directive). Every measurement below was taken inline.

**Session continuity.** The dev pass ran across two sittings. The first authored all five doc
files, the ledger amendment, the AC-9 scan and this record, then **timed out while the full gate
was still running** (its `check-all` log is partial — see § 14.9). The controller re-ran the gate
to completion; a second sitting verified that log directly and finished the bookkeeping (§ 14.5,
§ 14.9, the Status flip). **No deliverable file was edited after the gate ran** — see § 14.9.

### 14.2 Agent Model Used

Claude Opus 5 (`claude-opus-5[1m]`), repo-local session, native BMAD `bmad-dev-story` skill.

### 14.3 AC-by-AC disposition

| AC | Disposition | Evidence |
|---|---|---|
| **AC-1** | ✅ DONE | `docs/architecture.md` gains § "Classification: browse categories and facet tags" (+22 lines) stating (a) the retired mandatory single-category taxonomy, dropped by `0019_drop_category` at the 47.5 cutover, `Model.category_id` **not coming back**; (b) the current two independent layers — facet tags (`tag`, `tag_group`, `model_tag`) and browse categories (`browse_category`, `model_browse_category`, `0020_browse_categories`), M:N and optional; (c) zero categories is a valid, publicly visible state. The `:26` container sentence and the `:34` data-flow sentence now name the two new tables. § "References" gains a pointer to the governance doc. Every claim traces to § 3.2. |
| **AC-2** | ✅ DONE, with one recorded rendering deviation | `docs/operations.md:427` only. The first clause (`single-category taxonomy since retired by the Story 47.5 cutover`) is **byte-unchanged** on `:426`; the `43 legacy categories` figure, the `**As of 2026-05-05**` frame and every other line of the file are byte-unchanged. The qualifier states the clause describes the pre-Initiative-26 state, that browse categories are now a second independent optional layer, and explicitly that *"the mandatory single-category taxonomy did not return"* — inheriting 49.3 AC-25's constraint verbatim. **Deviation:** the AC says "one parenthetical"; the clause already sits *inside* a parenthetical, and nesting a second one there reads badly, so the qualifier is rendered as a semicolon-delimited clause within the existing parentheses. Same scope, same single edit target, better prose. **The F-7 amendment note is NOT inline** (an inline note would have added lines to a file the AC requires byte-unchanged elsewhere) — see § 14.8 for the exact commit-body text the controller must use to satisfy AC-2's "commit body **or** an inline note". |
| **AC-3** | ✅ DONE | `docs/browse-category-governance.md` (NEW, 232 lines). All eight categories in `position` order 0…7, each with slug, `name_pl`, `name_en`, the canonical English `inclusion_criterion`, positive examples, boundary/non-examples with tie-break, and crossed tag groups. Criterion sentences transcribed byte-exact from `seed.py:282-361`; examples/boundaries/crossings transcribed from `EXPERIENCE.md:101-156`. Plus, once each: the Category-vs-Tag rule; the eight-row collision table (`EXPERIENCE.md:162-171`); the rejected-candidates table (`:177-186`); the flat-MVP/depth-2 rule; the `replacement-parts` zero-margin monitoring note; and the explicit statement that `inclusion_criterion` is English-only by design while labels are bilingual. |
| **AC-4** | ✅ DONE | Governance doc § "Periodic curation QA". Names `/admin/categories`, the six checks in the **shipped order** (a) empty → (b) tiny → (c) label collisions → (d) over-categorized → (e) uncategorized count → (f) ungrouped tags (`52-3-curation-qa-surfaces.md:135`), with the action each implies. States the 1–3 norm is a **warning, never an error** (`ADVISORY_MAX = 3`, `curationThresholds.ts:24`) and that zero categories is valid and public. Cadence: **event-driven (after every import batch) as binding, monthly as an explicitly-labelled backstop**, with the reasoning, and the plain statement that **nothing automates either**. Zero new checks; zero manual `curl` duplicates of a panel row. Thresholds quoted are the shipped ones (`TINY_MAX = 2` → the tiny band is stated as 1–2; over-categorized `≥ 4` per `min_categories` default). |
| **AC-5** | ✅ DONE | `docs/agents-add-model-runbook.md` gains § "Browse categories — what the agent may and may not do" (+37 lines) directly under § "Behavioral Notes", adjacent to the tags/photos note. Read affordance (`GET /api/categories`, `GET /api/categories/{slug}`, `router.py:107,136`, `current_user`, cookie-jar `curl`s); negative capability (`browse_category_admin_router.py:62,168,207,248,285` under `current_admin`; `dependencies.py:29-30` → `403 admin_required`; `test_openapi_agent_surface.py:257-294` asserts never-`agent-write`); assignment named as `PUT /api/admin/models/{model_id}/categories`, admin-only, replace-set; and the consequence — **the import flow leaves a model uncategorized by default**, a valid state to curate later. The pre-existing § "Auth role gating" note at `:356` **did** contradict this (it said all `/api/admin/*` writes accept `role=agent`), so it gained the required clause: `Most …` + a named admin-only family list. |
| **AC-6** | ✅ DONE | `:398` no longer says "unauthenticated". It now says the fetch reuses the session cookie jar, cites `sot/router.py:248-252` and `main.py:50-61`, and carries the inline attribution *"corrects a pre-existing defect … dating from the Initiative-11 default-deny work; it is not an Initiative 26 change"*. The step's `curl` did **not** send the cookie jar and now does (`-b /tmp/portal-cookies.txt`, matching the file's own convention at `:54`). Poll loop, budgets and escalation guidance otherwise unchanged. |
| **AC-7** | ✅ DONE | Governance doc § "Concurrency posture on assignment — accepted last-writer-wins". Reproduces the **corrected** posture from `architecture.md:3340`: replace-set + explicit LWW; **LWW does permit a lost update**, with the A-adds-`lamps` / B-adds-`kitchen` worked example; the justification is audit-row recoverability/attributability, explicitly **not** absence of the race; the named trigger is a second concurrent admin editor **or** an automated/agent writer, at which point a `revision` integer or ETag/`If-Match` → `409` is owed. The retracted *"no lost-update ambiguity"* claim **does not appear** anywhere in the file. No code implements any of it. |
| **AC-8** | ✅ DONE (+ the one permitted heading) | `docs/index.md` gains exactly one entry line, under a **new** two-word heading `## Living Reference (hand-authored)`. **Heading justification (required by AC-8):** § "Generated Documentation" is factually wrong — it lists `bmad-document-project` output, and this file is hand-authored. § "Spec & Plans (pre-existing)" is false on all three counts: the governance doc is not a spec, not a plan, and not pre-existing. Neither existing heading is true of the file, so per AC-8 / § 16 R-4 a correctly-named heading was added rather than mis-filing it — which is exactly the small confident falsehood § 10 names as this story's real failure mode. No other line of `docs/index.md` changed; existing entries (including `agents-add-model-runbook.md`) were left where they are, since moving them is outside this story. |
| **AC-9** | ✅ DONE | Scan executed and tabled in full at § 14.7. `sprint-status.yaml:542` annotated with the Initiative-26 discharge; `status:` stays **`open`** per D-7. |
| **AC-10** | ✅ DONE | `git status --porcelain` + `git diff --stat`: 6 modified + 2 untracked, **zero** files under `apps/`, `workers/`, `infra/`; **zero** `.png`; zero locale keys. `git diff --check` → exit 0, no output. `infra/scripts/check-all.sh` → **16/16, `all green.`, exit 0** — a docs-only change did not perturb it, as the AC requires. Full evidence, provenance and per-stage figures in § 14.5 and § 14.9. |
| **AC-11** | ✅ DONE | `deferred-work.md:376` → owner **"a controller-assigned follow-up"** (the alternative that entry already offered); `:381` → owner **"E54 visual-spec hygiene pass"** (the only alternative that entry names — no controller-follow-up option was invented). Both keep `status: OPEN`; both gained a one-line reason naming this story as docs-only. The `69` census figure is **not** carried forward as prose (the entry's own "re-run the script" instruction is preserved); the corrected `12` is not restated. |
| **AC-12** | ✅ DONE | § 14.6. |

### 14.4 File List

Measured with `wc -l` and `git diff --numstat`, not estimated. **Figures restated by the code-review pass** after its two in-scope repairs (§ 17.3) — the dev pass's original numbers were `docs/architecture.md +28 / −2` and `sprint-status.yaml "2 lines"`; the first moved by the repair, the second was simply wrong (three lines change in that file, not two).

| File | Action | Lines |
|---|---|---|
| `docs/browse-category-governance.md` | **NEW** | 289 (whole file) |
| `docs/agents-add-model-runbook.md` | EDIT | +41 / −3 |
| `docs/architecture.md` | EDIT | +29 / −2 |
| `docs/operations.md` | EDIT | +5 / −1 |
| `docs/index.md` | EDIT | +4 / −0 |
| `_bmad-output/implementation-artifacts/deferred-work.md` | AMEND | +2 / −2 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | STATUS + AC-9 annotation | +3 / −3 |
| `_bmad-output/implementation-artifacts/54-3-rollout-docs-governance.md` | Dev Agent Record § 14 + task checkboxes + Status | — |

**Nothing outside § 7's predicted table was touched.**

⚠️ **One prediction overshot, disclosed rather than trimmed.**
`docs/browse-category-governance.md` is **289 lines against a predicted 150–220** — **+69 over
the upper bound (+31 %)**. This is a *line-count* overshoot, not a content overshoot: every
section maps 1:1 onto an AC (AC-3's eight entries, AC-4's six-check table, AC-7's LWW posture)
and nothing was added beyond them. The excess comes from formatting choices — prose hard-wrapped
at ~95 columns, one blank line between bullets, and the six-row QA table rendered as a table
rather than prose because AC-4 requires *"what action each implies"* per check. Trimming to the
predicted band would mean either unwrapping the prose into long lines or dropping the per-check
action column, and the second would break an AC. **Flagged for the controller as a disclosed
deviation from § 7, not silently absorbed.**

`docs/architecture.md` gained 29 lines against a predicted 20–30 — inside the band, and inside
D-6's "a section, not a rewrite" bound (the file goes 57 → 84 lines; the component topology,
future-proofing table and references block are untouched apart from one added reference line).
No other prediction was exceeded.

### 14.5 Gates

| Gate | State |
|---|---|
| `G26-DEVGO` | 🔓 **OPEN as a gate register entry**, but the controller issued **per-story dev go for Story 54.3 only** under the standing Initiative 26 delegation, which is what authorized this pass. That is a **controller decision, not an Ezop/human review or signature.** This dev pass does not close the register entry. |
| `G26-LIB` | 🔓 **OPEN.** Untouched. Nothing this story wrote is lightbox-adoption evidence, and nothing here bears on it. |
| `git diff --check` | ✅ **PASS** — exit 0, no output (no whitespace errors, no conflict markers). |
| Scope proof (AC-10) | ✅ **PASS** — `git status --porcelain \| grep -E '^..(apps\|workers\|infra)/'` → no output. `\| grep '\.png$'` → no output. |
| `infra/scripts/check-all.sh` **16/16** | ✅ **PASS — `passed: 16`, `all green.`, `CHECK_ALL_EXIT=0`.** Log: `.hermes/run-logs/check-all-54-3-controller-bg-20260731_203955.log` (`:5042` `passed:  16`, `:5059` `all green.`, `:5060` `CHECK_ALL_EXIT=0`). See § 14.9 for provenance and per-stage figures — **this run was completed by the controller, not by this dev session.** |
| Physical Android Chrome smoke | ⛔ **NOT RUN AND NOT CLAIMED.** None exists in this repository. |
| Human / Ezop review | ⛔ **NONE.** Not sought, not implied, not present. |

### 14.6 Honesty statement (AC-12)

- **No physical Android Chrome smoke was run, and none is claimed** — not directly, and not by
  omission. Nothing this story wrote says "rollout complete", "verified on mobile", or anything
  that a reader could take as device evidence. Every Initiative 26 a11y/visual finding in this
  repository remains jsdom / headless-Chromium evidence; the `mobile-*` Playwright projects are
  Pixel 5 **emulation**, never Android.
- **`G26-LIB` remains 🔓 OPEN.** This story produced no evidence toward it and nothing written
  here may be cited as lightbox-adoption evidence.
- **No human reviewed anything.** The controller's per-story dev-go is a controller decision, not
  an Ezop signature and not human review of any kind. No sentence in any file this story wrote
  attributes review, approval or acceptance to a human.
- **Every governance sentence is traceable to § 3.2's source map.** The eight category rows,
  their criteria, examples, boundaries and crossed tag groups come from `seed.py:282-361` and
  `EXPERIENCE.md:101-186` and nowhere else. No example, boundary case, tie-break or crossed tag
  group was invented. Where the seed and `EXPERIENCE.md` differed in wording on a criterion
  sentence (the seed capitalises the first letter and strips `*` emphasis), the **seed** wording
  was used per D-2 — that is what the database and the admin UI show. No third wording was coined.
- **The ≥3-models distribution evidence is stated as a conclusion with its provenance named as
  local and gitignored, and explicitly as *not reproducible from this repository*.** The
  governance doc says so in as many words.
- **`seed.py` is not presented as the running source of truth.** The doc names
  `GET /api/admin/categories` as the runtime source and labels its own transcription the
  "as-seeded baseline", with the create-if-absent/never-updates behaviour spelled out.

**Deliberately NOT written, for lack of grounding** — listed rather than hedged:

1. **No count of how many models currently sit in each category.** The repository has no database
   and the distribution capture is gitignored. Any figure would be unverifiable.
2. **No claim that the eight categories are "sufficient" or "complete" for the catalogue.** The
   evidence supports only "each clears the ≥3-model bar", which is what was written.
3. **No statement that list views show a model's categories.** `ModelSummary` deliberately carries
   no `categories` field (Decision AY); only `ModelDetail` does. Rather than risk implying
   otherwise, the doc says nothing about which view surfaces them.
4. **No claim that `inclusion_criterion` is visible to end users.** The public read omits it by
   design; the doc frames it as an admin-facing admission test.
5. **No cadence number tied to a calendar as the primary rule.** The binding cadence is
   event-driven because that is what the evidence supports; the monthly backstop is labelled as a
   backstop rather than presented as a policy anyone enforces.
6. **No new `docs/concurrency-patterns.md` entry (a "CC7").** Per D-5 the LWW posture is a
   governance acceptance, not a reusable primitive; that file was not opened.
7. **No repair of `docs/project-overview.md`** — see § 14.7 hit H-3, which is a real residual
   falsehood left unfixed on scope grounds and surfaced to the controller.

### 14.7 AC-9 — the epic:47 CUTOVER-CHECKLIST scan, executed and tabled

Three read-only passes, run on the story branch at `1906498`. Nothing was modified by the scan.

```bash
grep -rni --include='*.md' 'categor' docs/ *.md
grep -rn 'categor' infra/scripts/
grep -rn '/api/categories' infra/ docs/
```

Root `*.md` (`AGENTS.md`, `CLAUDE.md`, `README.md`): **zero** hits for `categor` — verified
separately with `grep -in 'categor' *.md` → no output.

| # | Hit | Disposition |
|---|---|---|
| **H-1** | `docs/operations.md:426-427` — *"facet tags are the sole classification system"* | **CORRECTED** under AC-2 (trailing clause only; narrowly amends Story 49.3 § 6 F-7). This is the one residual falsehood the scan found in live operational documentation. |
| **H-2** | `infra/scripts/cutover-smoke.sh:401-406`; `infra/scripts/audit-six-scenarios.sh:673-677` | **NO ACTION — verified already correct.** Both carry the Story 49.3 corrections stating `/api/categories` is live again under the Initiative 26 additive contract behind `current_user`. Re-read, not re-edited (§ 0.2 forbids editing `cutover-smoke.sh` in any form). |
| **H-3** | ⚠️ `docs/project-overview.md:174` lists `Category` among the current SoT tables — **that table was dropped by `0019_drop_category`**. Same file `:52` claims free-text search covers categories; `q` matches model names and **tag** names only (`sot/router.py` `get_models` description), never categories. `:53` / `:59` ("filter by … categories", "edit … categories") are **true again** under Initiative 26 and need nothing. | **NO ACTION — OUT OF SCOPE, SURFACED TO THE CONTROLLER.** Two grounds: (a) `docs/project-overview.md` is not in § 3.1's frozen five-file set, and § 7 makes anything outside that table a scope breach; (b) it is `bmad-document-project` output, and § 0.2 explicitly excludes *"a `bmad-document-project` re-run"* from this story — hand-patching generated output would fight its generator. **This is a live residual falsehood and it remains one.** Recorded here, in `sprint-status.yaml:542`, and raised as a protest in the closeout. Adopting it by dev discretion is precisely what § 16 R-1 forbade. |
| **H-4** | `docs/operations.md:456` (Slice 3B `CategoryTreeSidebar` record), `:508-516` (pre-47.3 on-disk `<category-slug>/` folder layout) | **NO ACTION — historical and already correctly framed.** `:456` is a dated slice record; `:508` is explicitly a *"Migration note (story 47.3)"* about **filesystem folders**, not the DB taxonomy. |
| **H-5** | `docs/operations.md:464-474`, `:623-629` | **NO ACTION — verified already correct** (Story 49.3). Both passages already describe the new additive contract and state both routes are equally auth-protected. |
| **H-6** | `docs/operations.md:777-863` — GlitchTip breadcrumb `category:spoolman.client` | **NO ACTION — different sense of the word.** Sentry breadcrumb categories, unrelated to the catalogue taxonomy. |
| **H-7** | `docs/design/*.md`, `docs/superpowers/specs/*.md`, `docs/plans/*.md`, `docs/migration-reports/*.md` (~90 hits: `CategoryTree`, `category_id`, `POST /api/admin/categories` with `parent_id`, the recursive DDL sketch, …) | **NO ACTION — dated point-in-time specs by construction.** Per `AGENTS.md:18-22` and `project-context.md`, `docs/design/` holds dated specs and `docs/plans/` is gitignored; these describe what was designed on their stated dates and are not living reference. Rewriting them would destroy the design record. |
| **H-8** | `infra/scripts/migrate_catalog_3mf.py`, `infra/scripts/tests/*.py` (`category="practical"`, `own_models`, `<category>/<basename>/`) | **NO ACTION — a different system.** These are the **Windows catalog index**'s own `category` field (the source file tree), not the portal's browse taxonomy. Also `infra/**`, which this story may only read. |

### 14.8 Commit-body text the controller must use (AC-2 requirement)

AC-2 requires the diff to state — *in the commit body or an inline note* — that the
`docs/operations.md` edit narrowly amends Story 49.3 § 6 F-7. **The dev pass does not commit**
(the controller owns review, gates and the final commit), and an inline note was rejected because
AC-2 also requires every other line of that file to stay byte-unchanged. The obligation therefore
transfers to the commit body. The exact text owed:

> `docs/operations.md:426-427` — narrowly amends Story 49.3 § 6 F-7. F-7 correctly protected the
> first clause ("single-category taxonomy since retired by the Story 47.5 cutover" — byte-unchanged
> here) and correctly refused a rewrite of the dated historical block. It did not separately rule
> on the trailing clause "facet tags are the sole classification system", which was already false
> at 49.3's own deploy and which the 2026-07-26 narrowing left orphaned. Only that trailing clause
> is qualified, and the qualifier explicitly states the mandatory single-category taxonomy did not
> return.

Also owed at commit time, per § 5 / V-10: the subject must be **bare `docs:`**, not `docs(catalog):`
— `deploy.sh:23,55` matches `SKIP_PREFIXES` literally, so a scoped subject would fire a full
build+deploy for a documentation-only change. Precedent: `a3aaf35`, `513f4bd`.

### 14.9 `check-all.sh` provenance — who actually ran the gate

**Honesty note: this dev session did NOT complete the full gate.** It started one
(`.hermes/run-logs/check-all-54-3-20260731_202347.log`) which was **cut off mid-`apps/api pytest`
at ~21 %** when the session timed out. That log is **partial and carries no verdict**; it must
not be cited as evidence. **The controller re-ran the gate to completion**, and the run recorded
below is the controller's, not this session's.

The result was **verified in this session by reading the controller's log directly**, not taken
on report:

| Property | Verified value | Where |
|---|---|---|
| Exit code | `CHECK_ALL_EXIT=0` | log `:5060` |
| Summary | `passed:  16` · `all green.` | log `:5042`, `:5059` |
| Failed stages | none listed | log `:5042-5058` (16 `✓` lines, no `✗`) |
| `apps/web` vitest | `154 passed (154)` files / `1139 passed` tests | log |
| `apps/api` pytest | `1961 passed, 3 skipped` (452.51 s) | log `:3966` |
| `workers/render` pytest | `21 passed` | log `:3972` |
| `infra/scripts` pytest | `13 passed` | log `:3978` |
| `apps/web` visual regression | **`806 passed`, `50 skipped`, 0 failed** (4.9 m) | log `:5019-5020` |
| Drift gates | settings-env-compose-diff OK; `uv lock --check` OK (apps/api + workers/render); local-env-secrets OK | log `:5025-5040` |

**The run covered the exact content under review.** The log's own header records
`HEAD=1906498064e49cb49f57208e4ec93faf91865b97`,
`BRANCH=docs/E54.3-rollout-docs-governance`, and a `STATUS_BEFORE` block listing the identical
eight-file dirty tree this record describes. Every one of the eight files was last written at or
before **20:26:51**, and the gate started at **20:39:55** — so no deliverable changed after the
gate observed it. The only edits made *after* the run are inside this § 14 record and the
`sprint-status.yaml` status line: BMAD bookkeeping prose, which no `check-all` stage inspects.

**Zero PNG churn**, as AC-10 requires: the visual stage reports `0 failed` against the committed
baselines, and `git status --porcelain | grep '\.png$'` returns nothing.

---

## 15. Change log

| Date | Change | By |
|---|---|---|
| 2026-07-31 | Created via native `bmad-create-story` (Create **CS**) on `main` @ `1906498`, clean tree. Status set to `ready-for-validation`; `sprint-status.yaml` moved `backlog` → `ready-for-validation`. No code, no docs, no branch, no gate run, no commit/merge/deploy. **No `G26-DEVGO` issued by this pass.** NOT an Ezop signature and NOT human review. | Claude Opus 5 (native BMAD) |
| 2026-07-31 | **Implemented via native `bmad-dev-story`** on branch `docs/E54.3-rollout-docs-governance` @ `1906498`, under the controller's per-story `G26-DEVGO` for 54.3 only. T1–T9 complete; AC-1…AC-12 all discharged (§ 14.3). Five doc files (four EDIT + one NEW `docs/browse-category-governance.md`), one ledger amendment, one `sprint-status.yaml` AC-9 annotation. Zero `apps/` / `workers/` / `infra/`, zero PNG, zero locale keys. `git diff --check` exit 0. `infra/scripts/check-all.sh` **16/16, `all green.`, exit 0** — **run completed by the controller after this session timed out mid-gate**; verified here by reading the log (§ 14.9). Status `ready-for-dev` → `in-progress` → **`review`**. Two disclosed deviations: the governance doc is 289 lines vs § 7's predicted 150–220 (§ 14.4), and AC-2's F-7 amendment note is owed in the **commit body** rather than inline (§ 14.8). One unfixed residual falsehood surfaced and routed, not adopted: `docs/project-overview.md:174,:52` (§ 14.7 H-3). **`G26-LIB` remains 🔓 OPEN**; no physical Android Chrome smoke run or claimed; **no human review of any kind**; NOT an Ezop signature. Not committed, not merged, not deployed. | Claude Opus 5 (native BMAD) |
| 2026-07-31 | **Reviewed via native `bmad-code-review`** against the dirty tree on `docs/E54.3-rollout-docs-governance` @ `1906498`. **VERDICT: ✅ APPROVE** after 2 substantive + 1 bookkeeping repair applied in pass (§ 17.3). Status `review` → **`done`** = review gate discharged only. Findings: **F-1** the AC-5 role-gating clause claimed *"two families are admin-only"* — false, the same `sot-admin-governance` router also owns tag-group governance + `POST /api/admin/tags`, and share/invite/user/slicer/queue admin surfaces are admin-only too (the `_GOVERNANCE_ROUTES` set the subsection itself cites contains the tag-group routes); **F-2** the new `docs/architecture.md` section enumerated 5 of the 8 shipped facet groups, omitting the largest (`type`/Typ); **F-3** § 14.4 bookkeeping (orphan table header, `sprint-status.yaml` "2 lines" vs actual `+3/−3`). 4 dismissed. All 8 seeded categories re-verified byte-exact against `seed.py`; the six QA checks, thresholds, LWW posture, depth-2 422 names and AC-6 auth fix re-verified against shipped code; the controller's `16/16 / all green. / CHECK_ALL_EXIT=0` log read directly and confirmed to carry the same HEAD, branch and eight-file dirty tree. Repairs touched only `docs/` files this story already opened; `check-all` NOT re-run and does not need to be — no stage reads `docs/**/*.md` (§ 17.3). `docs/project-overview.md` H-3 protest **UPHELD, not adopted** — needs controller routing. **`G26-LIB` remains 🔓 OPEN**; no physical Android Chrome smoke run or claimed; **no human review of any kind; NOT an Ezop signature**. AC-2's F-7 commit-body note and the bare-`docs:` subject remain OWED at commit (§ 17.5). Not committed, not staged, not merged, not deployed. | Claude Opus 5 (native BMAD) |
| 2026-07-31 | **Arbitrated** an independent Aider stdin diff review that returned **REQUEST_CHANGES** (`.hermes/run-logs/aider-review-54-3-20260731_210716.log`), against the native `bmad-code-review` **APPROVE**. **VERDICT: ✅ APPROVE-after-arbitration — 0 of 7 findings actionable** (4 false-positive, 1 noise, 1 valid-but-already-recorded as owed at commit, 1 external-evidence confirmed). Full per-finding record with re-measured evidence at **§ 18**. Key measurements re-run in this pass, not inherited: `docs/operations.md` is `+5/−1` = **one** line replaced hard-wrapping to five (AC-2's three binding constraints all byte-exact); AC-8's heading is **explicitly permitted** by AC-8 § 207 and Aider's `Spec & Plans` alternative is the one § 16 R-4 ruled out; AC-6's inline attribution **is present** at `docs/agents-add-model-runbook.md:436`; AC-9's eight-row scan table **is present** at § 14.7; `check-all` log re-read → `passed: 16` / `all green.` / `CHECK_ALL_EXIT=0`; scope proof re-run → zero `apps/`/`workers/`/`infra/`, zero PNG. Root cause of five findings: the Aider pass ran with `Git repo: none` on a truncated stdin diff and could not open the artifacts it declared missing. **No product doc edited, no AC re-opened, status stays `done`.** AC-2's F-7 commit-body note and the bare-`docs:` subject remain **OWED at commit** (§ 17.5) — this pass does not waive them. **`G26-LIB` remains 🔓 OPEN**; no physical Android Chrome smoke run or claimed; **no human review of any kind; NOT an Ezop signature**. `check-all` not re-run. Not committed, not staged, not merged, not deployed. | Claude Opus 5 (repo-local, arbitration) |
| 2026-07-31 | Validated via native `bmad-create-story` (Validate **VS**) on `main` @ `1906498`. All ten § 2 traces independently re-measured inline and confirmed. **Five corrections applied in place** (§ 16.2). Q-1…Q-6 ruled (§ 11). Status `ready-for-validation` → **`ready-for-dev`**. Still no code, no docs, no branch, no gate run, no commit/merge/deploy. **`G26-DEVGO` remains 🔓 OPEN — validation does NOT grant it.** NOT an Ezop signature and NOT human review. | Claude Opus 5 (native BMAD) |

---

## 16. Validation record — `bmad-create-story` Validate (VS), 2026-07-31

**Verdict: ✅ PASS** — after the five corrections in § 16.2 were applied in place. Status flipped `ready-for-validation` → **`ready-for-dev`**.

Run repo-local (Claude Opus 5) on `main` @ `1906498`, working tree carrying only the create pass's two files. **Zero product files, docs, tests, locales or baselines were read-modified; no branch, no gate, no commit.** No subagents dispatched (controller directive); every measurement below was taken inline in the validate session against the checked-out tree, independently of § 2's numbers.

### 16.1 Independent re-measurement of § 2 — all ten traces CONFIRMED

| Trace | Validate-pass measurement | Verdict |
|---|---|---|
| V-1 | `grep -ic categor docs/architecture.md` → **0**; file is **57** lines | ✅ exact |
| V-2 | `grep -ic categor docs/agents-add-model-runbook.md` → **0**; **409** lines | ✅ exact |
| V-3 | `:398` reads *"…`GET /api/models/{model_id}`, unauthenticated"*; `router.py:248-252` `get_model` carries `_user_id: uuid.UUID = current_user`; `main.py:50-61` `_PUBLIC_ROUTES` = health + 5 auth + 3 share, **no `/api/models*`**; `operations.md:464-465` states the opposite | ✅ falsehood confirmed 3 ways |
| V-4 | `browse_category_admin_router.py:62` `prefix="/api/admin"`; `current_admin` at `:168,:207,:248,:285`; decorators `post:149 put:181 delete:222 patch:260`; `:160` docstring *"never agent-writable"*; `dependencies.py:29-30` → `403 admin_required`; `test_openapi_agent_surface.py:257-273` `_GOVERNANCE_ROUTES` lists all four writes; reads at `router.py:107,136` | ✅ exact |
| V-5 | `operations.md:466-470` + `:619-625` carry the 49.3 corrections; `cutover-smoke.sh:401-406` matching comment, probe on `/api/tags`; `:426-427` stale clause present | ✅ exact — **and see R-1** |
| V-6 | `52-3:135` fixes the six-check order (a)…(f); `:168` AC-1 over-categorized route; `:186` 1–3 norm is a warning; `:187` zero-category valid and public | ✅ exact |
| V-7 | `grep -rniE 'last-writer-wins\|last writer wins\|\bLWW\b' docs/` → **0 hits**; `architecture.md:3340` carries the full corrected posture incl. the retracted "no lost-update ambiguity" claim | ✅ exact |
| V-8 | All **8** rows re-read from `seed.py:282-361` — every slug, `name_en`, `name_pl` and `position` in § 2's table is **byte-exact**, incl. the `printer-3d` em-dash criterion and the `toys-games` Oxford comma. `seed.py:365-370` create-if-absent, never updates. `EXPERIENCE.md` anchors verified: collision table **8 rows** at `:158-171`, rejected candidates at `:173-186` | ✅ exact |
| V-9 | `docs/index.md:47-51` § "Generated Documentation" (4 entries), § "Spec & Plans (pre-existing)" from `:53` | ✅ exact — **but see R-4** |
| V-10 | `deploy.sh:23` `SKIP_PREFIXES=("docs:" "chore:" "wip:")`; `:55` `[[ "$subject" == "$prefix"* ]]` — literal prefix match, so `docs(catalog):` **would** deploy | ✅ exact |

Also confirmed: `sprint-status.yaml:540` is the epic:47 **CUTOVER CHECKLIST** action item, `status: open`, owner *"standing discipline for future endpoint-retirement stories"* — D-7's reading is correct and AC-9 must **not** close it. `architecture.md:3386` confirms **`G26-LIB` 🔓 open** and **`G26-DEVGO` 🔓 open**.

### 16.2 Corrections applied in place

- **R-1 — AC-2 ADOPTED, MODIFIED. The create-pass scope tension is resolved in favour of taking the fix, on corrected grounds.** *(This is the ruling the controller asked for; stated in full.)*

  **The narrowing is real and the create pass under-reported it.** `sprint-status.yaml:409` (pre-create) and `epics.md:4599` both name `docs/operations.md:426` **explicitly** among the passages *"moved INTO story 49.3"*. So AC-2 does re-enter narrowed-out territory. Worse, Story 49.3 did not merely fail to fix it: its § 6 F-7 **ruled against editing it** — *"Reported, deliberately not edited"* — its § 15 reviewer independently called that judgment *"sound"*, and its AC-25 verification asserts *"`:426-427` deliberately untouched"*. The create pass's framing (*"49.3 correctly left it"*) papered over a live, reviewed ruling it was proposing to overturn.

  **The finding is nonetheless real, and the passage is now orphaned.** The narrowing's own criterion was *"the passages that go stale **at Story 49.3's deploy**"*. The trailing clause *"facet tags are the sole classification system"* went stale at exactly that deploy — browse categories were seeded by 49.2 and read-exposed by 49.3 — so by the narrowing's own test it was 49.3's, and 49.3 declined it. It is assigned to a `done` story that refused it and narrowed out of the only remaining story. Nobody owns it.

  **F-7's defence does not survive scrutiny of the second clause.** F-7 argued the passage sits in a dated *"As of 2026-05-05"* historical block. But the parenthetical is **editorially maintained, not frozen history**: *"since retired by the Story 47.5 cutover"* is itself a forward reference to an event well after 2026-05-05. It was already updated once to track a later initiative; it simply was not updated again for Initiative 26. F-7 was **right** that the *first* clause must not be rewritten (the Initiative 25 retirement stands permanently, and implying otherwise is the real hazard) — and it never separately examined the *trailing* clause, which is the only thing AC-2 touches.

  **Decision: AC-2 STAYS, MODIFIED.** Story 54.3 is the last story of the last epic of Initiative 26, and E54's stated goal is *"leave the documentation truthful"* (`epics.md`). Closing the initiative with a known-false classification sentence in live ops documentation — found by a scan this story is required to run — would defeat the story's charter. AC-2 is rewritten to: (a) touch the **trailing clause only**; (b) name and narrowly amend **49.3 § 6 F-7**, rather than silently overturning it; (c) inherit 49.3 **AC-25**'s constraint verbatim — the parenthetical must not imply the mandatory single-category taxonomy returned; (d) be the **recorded disposition of an AC-9 scan hit**, not free-standing re-adopted scope, which keeps the frozen narrowing honest because the *scan* is unambiguously 54.3's; (e) cite the correct **`:426-427`** two-line range. It remains droppable, but now only by controller ruling — not by dev discretion.

- **R-2 — § 3.1 contradicted AC-2 and § 7.** The in-scope table said *"exactly four"* and omitted `docs/operations.md`, which AC-2 mandates and § 7 predicts. A dev following § 3.1 would have scored the AC-2 edit as a scope breach; § 7 says *"anything outside this table is a scope breach"*. Reconciled to **five files + one ledger amendment**, with the operations.md row bounded to AC-2.

- **R-3 — D-8 / § 12-B cited the ledger inaccurately.** The claim *"Both ledger entries already offer 'or a controller-assigned follow-up'"* is **false for entry B**. `deferred-work.md:376` does offer it; `:381` reads *"Owner: E54 visual-spec hygiene pass / Story 54.3."* with no such alternative. AC-11 now re-points the two entries **differently** — A to a controller-assigned follow-up (pre-offered), B to the "E54 visual-spec hygiene pass" the ledger itself names. Routing conclusion unchanged; its justification is now true.

- **R-4 — AC-8 filed a hand-authored doc under a heading that misdescribes it.** § "Generated Documentation" lists `bmad-document-project` output; `browse-category-governance.md` is hand-authored living reference, and the in-file precedent for that (`agents-add-model-runbook.md`) sits under a different, also-imperfect heading. AC-8 now requires the dev to pick a heading that is **true** of the file — or add one — and justify it in § 14. Mis-filing it would be precisely the small confident falsehood § 10 names as this story's real failure mode.

- **R-5 — § 0.2's blanket "Not `docs/operations.md`" bullet** asserted the cutover scan *"currently does not"* find a residual falsehood there. It does (R-1). Split into a hard exclusion for `cutover-smoke.sh` and a read-only-except-AC-2 rule for `docs/operations.md`.

### 16.3 Checks that PASSED with no change required

- **AC completeness.** AC-1…AC-12 cover every deliverable in the epic sketch and the `sprint-status.yaml:409` narrowing text: `docs/architecture.md` (AC-1), the agent runbook incl. the assignment contract (AC-5), the governance doc with inclusion criteria / positive+boundary examples / Category-vs-Tag rule / periodic QA checklist / LWW posture with named upgrade trigger (AC-3, AC-4, AC-7), plus the epic:47 scan the story exists for (AC-9). **FR26-GOV-1's full payload** (`prd.md:2255`) maps onto AC-3 with nothing dropped.
- **No accidental code or product scope.** § 5 "Never", AC-10 and the § 7 table each independently fence `apps/**`, `workers/**`, `infra/**`, locales and `__snapshots__/**/*.png`. AC-9's scan is read-only. AC-10's `git diff --name-only` proofs are mechanical, not attestations. ✅
- **`G26-LIB` remains 🔓 OPEN.** Confirmed at `architecture.md:3386`. § 0.1, § 13 and § 14.5 all hold it open and forbid citing anything here as lightbox-adoption evidence. Nothing in this story bears on it. ✅
- **No physical Android Chrome evidence is claimed** anywhere in the artifact. § 0.1 forbids it including *by omission* (a "rollout complete" flourish), § 13 excludes it, AC-12 requires the dev to state its absence, and the § 11 risk table names the story's own title as the temptation. `prd.md:2255`-adjacent FR26-VIEW-1's physical-smoke requirement belongs to Story 53.3, not here. ✅
- **`G26-DEVGO` remains 🔓 OPEN.** Confirmed at `architecture.md:3386`: *"code starts only after create+validate and controller confirmation of that specific ready story"*. Create + validate are now both complete, which satisfies the **precondition** — it does **not** satisfy the gate. **This validate pass does not grant `G26-DEVGO` and has no authority to.** The controller must grant per-story dev go before `bmad-dev-story` runs. ✅
- **Predicted file set** (§ 7) is now consistent with § 3.1 and proportionate: `docs/architecture.md` is 57 lines and gains 20–30, matching D-6's "section, not a rewrite" bound. ✅
- **Source map** (§ 3.2) grounds every publishable claim in a shipped file, and every anchor spot-checked in § 16.1 resolved correctly. ✅

### 16.4 Not fixed — deliberately left to the dev pass

- **T1 re-verification stands.** § 16.1 confirms § 2 at `1906498`, but T1's instruction to re-measure against the tree the dev actually has is **not** discharged by this pass and must still run — the dev may branch from a later commit.
- **No AC was added for the `docs/index.md` heading choice** beyond AC-8's justification requirement; it is a one-line judgement, not a deliverable.

---

## 17. Code review record — native `bmad-code-review`, 2026-07-31

**Verdict: ✅ APPROVE**, after the two in-scope documentation repairs in § 17.3 were applied in
pass. Status `review` → **`done`** — meaning *the story review gate is discharged*, nothing more:
**not committed, not staged, not merged, not deployed**, and § 17.5 lists what the controller
still owes at commit time.

Run repo-local (Claude Opus 5, `claude-opus-5[1m]`) against the **dirty working tree** on branch
`docs/E54.3-rollout-docs-governance` at `1906498` — identical to this file's `baseline_commit`,
so § 2, § 14 and this review all measured the same tree. Session opened with the mandatory native
`bmad-help` routing call, which returned `bmad-code-review` (`4-implementation`, `preceded-by:
bmad-dev-story`). **NOT an Ezop signature and NOT human review of any kind.**

**Procedural deviation, recorded.** `step-02-review.md` calls for Blind Hunter / Edge Case Hunter
/ Acceptance Auditor as parallel subagents. This session's controller directive forbids Agent-tool
dispatch, and the step's documented fallback (write prompt files and HALT) would have stalled a
run the controller asked to complete with a verdict. All three lenses were therefore executed
**inline** — adversarial reading of the diff, boundary/enumeration hunting over every new
universal claim, and an AC-1…AC-12 audit against § 4. No subagent result is cited anywhere in
this section. Same posture as the create, validate and dev passes on this story.

### 17.1 What was independently re-verified (not taken from § 14)

| # | Claim under test | Method | Result |
|---|---|---|---|
| 1 | All 8 seeded categories transcribed byte-exact | Parsed `STARTER_BROWSE_CATEGORIES` out of `seed.py` and string-matched every `inclusion_criterion` + header against `docs/browse-category-governance.md` | ✅ 8/8 byte-exact, incl. the `printer-3d` em dash and `toys-games` Oxford comma |
| 2 | Examples / boundaries / collisions / rejected candidates transcribed, not invented | Read `EXPERIENCE.md:95-195` against the doc | ✅ faithful; the doc trims two source asides and never adds a tie-break |
| 3 | Six QA checks in the shipped order, with shipped thresholds | `curationChecks.ts:222-233` (D-7 order array), `curationThresholds.ts` (`TINY_MAX = 2`, `ADVISORY_MAX = 3`), `browse_category_admin_router.py:142` (`min_categories` default **4**) | ✅ order a–f exact; 1–2 tiny band and ≥ 4 over-categorized both correct |
| 4 | AC-7 LWW posture matches shipped behaviour | `browse_category_admin_router.py:181-200` — replace-set, idempotent, "NO optimistic-concurrency precondition", one `model.update` audit row with `before`/`after` id sets | ✅ exact; the retracted "no lost-update ambiguity" phrasing appears nowhere |
| 5 | Depth-2 is service-layer, with the named 422s | `admin_service.py:1426-1531` (`self_cycle`, `parent_not_root`, `reparent_exceeds_depth`) | ✅ all three names real |
| 6 | AC-6 auth correction | `sot/router.py:248-252` (`current_user`), `main.py:50-61` (`_PUBLIC_ROUTES` = health + 5 auth + 3 share) | ✅ the "unauthenticated" claim is gone and the `curl` now sends `-b` |
| 7 | AC-9 scan hits | Re-ran the three greps; `grep -in categor *.md` → no output; `docs/project-overview.md:174` still lists `Category`, `:52` still claims search covers categories (`q` matches model + **tag** names only) | ✅ H-1…H-8 reproduce; **H-3 is a real, still-live falsehood, correctly left unfixed and surfaced** |
| 8 | The gate log is the controller's and covers this content | Read `.hermes/run-logs/check-all-54-3-controller-bg-20260731_203955.log` directly: `:1-11` header `HEAD=1906498…`, `BRANCH=docs/E54.3-rollout-docs-governance`, the identical 8-file `STATUS_BEFORE` block; `:5042` `passed:  16`; `:5059` `all green.`; `:5060` `CHECK_ALL_EXIT=0` | ✅ verified by reading, not by report. § 14.9's "the controller ran it, not this session" disclosure is accurate |
| 9 | Scope proof | `git status --porcelain \| grep -E '^..(apps\|workers\|infra)/'` → empty; `\| grep '\.png$'` → empty; `git diff --check` → exit 0 | ✅ AC-10 holds |
| 10 | Ledger amendments | `deferred-work.md` `:376` → "a controller-assigned follow-up"; `:381` → "E54 visual-spec hygiene pass", both `OPEN`, `69` not carried forward, `12` not restated | ✅ AC-11 discharged, including the R-3 asymmetry |
| 11 | Honesty constraints | Full-text read of all five doc files + both ledger lines: no "rollout complete", no device/mobile verification sentence, no human/Ezop attribution, no `G26-LIB` movement, evidence provenance named as local + gitignored + **not reproducible from this repository** | ✅ § 0.1 and AC-12 hold in the shipped prose, not only in the record |

### 17.2 Findings — 2 patch, 1 patch (bookkeeping), 0 decision-needed, 0 defer, 4 dismissed

Both substantive findings are the **same defect class this story exists to eliminate**: a
confident *closed enumeration* that is false against shipped code. Neither was caught by the
gate, exactly as § 10 predicted.

- [x] **[Review][Patch] F-1 (high) — the new "Auth role gating" clause enumerated *two* admin-only families; there are many** [`docs/agents-add-model-runbook.md:356`]
  AC-5 required the pre-existing `:356` sentence to gain a clause so the new subsection would not
  contradict it. The clause added read *"Two families are **admin-only** … hard-delete
  (`?hard=true`), and every browse-category governance route."* Measured false: the **same
  `sot-admin-governance` router** also carries `POST /api/admin/tag-groups`,
  `PATCH`/`DELETE /api/admin/tag-groups/{group_id}` and `POST /api/admin/tags`, all under
  `current_admin` (`tag_group_admin_router.py:4,38,57,86,115,139`) and all deliberately relocated
  **off** the agent-write surface by D-ADMINONLY-1. `share/admin_router.py:18,59,69`,
  `invite/admin_router.py:40,64,120,174`, `auth/password_reset/admin_router.py:70`,
  `admin/router.py:29,48,67,135,170,263,366,425,482`, `slicer/admin_router.py` and
  `queue/admin_router.py:42` are further admin-only surfaces. Sharpest evidence: the
  `_GOVERNANCE_ROUTES` set the new subsection *itself cites*
  (`test_openapi_agent_surface.py:257-273`) contains the four tag-group/tag-create routes
  alongside the four category routes — the enumeration was contradicted by the very citation
  next to it. Consequence for the doc's only consumer, an ingesting agent: it would read
  `POST /api/admin/tag-groups` as callable and take a `403`.
- [x] **[Review][Patch] F-2 (medium) — the new architecture section enumerated 5 of the 8 shipped facet groups** [`docs/architecture.md:41`]
  *"grouped into facets (material, room, system, use, printer)"* reads as the facet list. The
  shipped `STARTER_TAXONOMY` carries **eight** groups — `type`/Typ, `room`, `system`, `use-case`,
  `printer`, `material`, `creator`, `level`. The omitted `type` group is the largest (12 tags) and
  is the one this story's own collision table leans on hardest (`Dekoracje`, `Uchwyty`,
  `Wazony`, `Klipsy`, `Etui` are all `Typ` tags), so the omission is load-bearing, not cosmetic.
- [x] **[Review][Patch] F-3 (low) — § 14.4 bookkeeping** [`54-3-rollout-docs-governance.md:493`]
  A duplicated orphan table header preceded the File List, and `sprint-status.yaml` was recorded
  as "2 lines" against an actual `+3 / −3` (three lines change: `last_updated`, the story key, and
  the `:542` action-item annotation).

**Dismissed as noise (4), recorded so they are not re-raised:**
1. *AC-2 rendered as a semicolon clause rather than a second parenthetical.* Disclosed in § 14.3;
   `:426`'s first clause, the `43 legacy categories` figure and the `As of 2026-05-05` frame are
   all byte-unchanged, and the qualifier states the mandatory taxonomy did not return. The AC's
   intent is satisfied; nesting parentheses would be worse prose.
2. *`docs/index.md` gained 4 lines, not "exactly one".* AC-8 explicitly permits one added heading;
   the other two lines are the blank lines markdown requires around it. Justification is in
   § 14.3, as AC-8 demanded, and the chosen heading is true of the file.
3. *Governance doc 289 lines vs § 7's predicted 150–220.* Disclosed, not absorbed; every section
   maps to an AC and trimming would drop AC-4's per-check action column.
4. *`docs/project-overview.md` H-3 left unfixed.* Correctly out of scope and correctly protested
   — see § 17.4. Fixing it here is what § 16 R-1 forbade.

### 17.3 Repairs applied in pass

Controller directive pre-authorized in-pass repair of docs defects inside Story 54.3 scope, so
`step-04-present.md` § 5's HALT was not taken (same posture as the 54.1/54.2 reviews). Two files
touched, both already in § 3.1's frozen five-file set — **no file was opened that this story had
not already opened**:

- `docs/agents-add-model-runbook.md:356` — F-1. `Two families are` → `Several families are`, the
  enumeration widened to name the whole `sot-admin-governance` router (tag-group governance, the
  global tag-create `POST /api/admin/tags`, every browse-category route) plus
  `/api/admin/share/*`, `/api/admin/invites/*` and user management, and closed with an explicit
  *"that list is not exhaustive"* pointing at the `agent-write` OpenAPI filter the runbook already
  documents at § "Endpoint Discovery via OpenAPI". A non-exhaustive list with a mechanical
  fallback is true and stays true as routers are added; a closed list is a maintenance trap.
- `docs/architecture.md:41` — F-2. Facet enumeration completed to all eight shipped groups.
- `54-3-rollout-docs-governance.md` § 14.4 — F-3, plus the `+29 / −2` restatement this repair
  itself caused.

**Post-repair re-measurement** (AC-10 re-proved after the edits, not inherited):
`git diff --numstat HEAD` → `docs/agents-add-model-runbook.md +41/−3`, `docs/architecture.md
+29/−2`, `docs/operations.md +5/−1`, `docs/index.md +4/−0`, `deferred-work.md +2/−2`,
`sprint-status.yaml +3/−3`. `git status --porcelain | grep -E '^..(apps|workers|infra)/'` → no
output. `| grep '\.png$'` → no output. `git diff --check` → exit 0.

**Gate status after the repairs, stated honestly.** `check-all.sh` was **not** re-run by this
pass. It does not need to be: all three repairs are prose inside `docs/*.md` and
`_bmad-output/`, and no stage in `infra/scripts/check-all.sh:54-119` reads either path — the
sixteen stages are ruff ×4, typecheck, build, lint, vitest, pytest ×3, visual regression, and the
four drift gates. The controller's `16/16` run therefore still covers every byte any stage
inspects. **This is a reasoned claim about stage coverage, not a claim that a gate ran after the
repairs.**

### 17.4 Honesty constraints — audited, all hold

- **`G26-LIB` 🔓 OPEN.** Untouched by this story and by this review. Nothing written here or in
  the five doc files is lightbox-adoption evidence, and nothing cites it as such.
- **No physical Android Chrome smoke** was run, claimed or implied — by this pass or by the diff.
  Full-text read of all five doc files found no "rollout complete", no device-verification and no
  mobile-verified sentence, despite the story's own title. The `mobile-*` Playwright projects
  remain Pixel 5 **emulation**.
- **No human review of any kind.** This review is an agent pass. The controller's per-story
  `G26-DEVGO` was a controller decision. **NOT an Ezop signature.** No sentence in any file this
  story writes attributes review, approval or acceptance to a human.
- **AC-2 stays a narrow amendment of Story 49.3 § 6 F-7.** Verified in the shipped diff: `:426`'s
  first clause byte-unchanged, only the trailing clause qualified, the qualifier states in as many
  words that *"the mandatory single-category taxonomy did not return"* (49.3 AC-25's constraint),
  and the `43 legacy categories` count and `As of 2026-05-05` frame are untouched. The narrowed-out
  `infra/scripts/cutover-smoke.sh` was re-read and **not edited** (`git status` proves zero
  `infra/`).
- **The `docs/project-overview.md` protest is upheld, not overruled.** H-3 is a genuine live
  falsehood (`:174` lists a `Category` SoT table dropped by `0019_drop_category`; `:52` claims
  free-text search covers categories when `q` matches model and **tag** names only). It is
  correctly outside § 3.1's frozen five-file set and correctly excluded by § 0.2's
  "not a `bmad-document-project` re-run". **This review declines to adopt it** — doing so would
  repeat exactly the dev-discretion scope grab § 16 R-1 ruled against. It needs controller
  routing; it is recorded in `sprint-status.yaml:542` and § 14.7 H-3 and stays visible.
- **Evidence provenance.** The ≥3-models distribution claim is published as a conclusion with its
  capture named local, gitignored and **not reproducible from this repository**. Verified against
  `seed.py:250-265`.

### 17.5 Still owed at commit time — controller, not this pass

1. **AC-2's F-7 amendment note in the commit body.** AC-2 requires the diff to state that the
   `docs/operations.md` edit narrowly amends Story 49.3 § 6 F-7. § 14.8 carries the exact text and
   the reason it is not inline (AC-2 requires every other line of that file byte-unchanged).
   **AC-2 is not fully discharged until that commit body exists** — this review approves the diff
   with the obligation transferred, it does not waive it.
2. **Bare `docs:` commit subject.** `deploy.sh:23,55` matches `SKIP_PREFIXES` literally, so
   `docs(catalog):` would fire a full build + deploy for a documentation-only change (V-10).
   Precedent: `a3aaf35`, `513f4bd`.
3. **Route `docs/project-overview.md` H-3** to a follow-up owner.
4. Nothing is committed, staged, merged or deployed by this pass.

---

## 18. Arbitration record — independent Aider diff review, 2026-07-31

**Input.** An independent Aider stdin diff review returned **REQUEST_CHANGES**
(`.hermes/run-logs/aider-review-54-3-20260731_210716.log`, `openrouter/deepseek/deepseek-v3.2`,
`ask` format, `Git repo: none`, repo-map disabled, 63k tokens sent). This contradicted the native
`bmad-code-review` **APPROVE** at § 17, so the controller commissioned arbitration. **VERDICT:
APPROVE-after-arbitration. No finding survived as actionable against the working tree.** Every
disposition below was re-measured mechanically in this pass; none is inherited from § 14 or § 17.

**Reviewer-environment caveat, stated first because it explains five of the seven findings.** The
Aider pass was handed a diff on stdin with **no repository**. It could not open a file, could not
resolve a line number, and could not see anything the diff text did not literally contain. Two of
its findings assert absence of content that is present in the diff hunks; the rest reason about
line *counts* in a hard-wrapped Markdown file, where wrapped continuation lines are indistinguishable
from added content. That is a known failure mode of repo-less diff review on prose, not a defect
in the diff.

| # | Aider finding | Classification | Evidence re-measured in this pass |
|---|---|---|---|
| **1** | *Critical* — AC-2: `docs/operations.md` is a "5-line addition", violating "one parenthetical" / byte-unchanged-except-trailing-clause | ❌ **FALSE POSITIVE** (line-count artefact) + already-dismissed disclosed deviation | `git diff --numstat HEAD -- docs/operations.md` → **`5  1`**: exactly **one** existing line is replaced, and the replacement hard-wraps to five at the file's ~72-col width. The content added is **one clause**, not five lines. All three of AC-2's binding constraints hold byte-exact: `:426`'s first clause (*"single-category taxonomy since retired by the Story 47.5 cutover"*) unchanged; `43 legacy categories` and the `**As of 2026-05-05**` frame unchanged; every other line of the file unchanged. The qualifier states in as many words that *"the mandatory single-category taxonomy did not return"* — 49.3 AC-25's constraint. The **rendering** deviation (semicolon clause inside the existing parenthetical rather than a nested second one) is real, was disclosed by the dev at § 14.3 and dismissed with reasons at § 17.2 noise-1. AC-2 § 186-189 lists its binding constraints explicitly and punctuation shape is not among them. **Not a scope breach.** |
| **2** | *Critical* — AC-8: the new `## Living Reference (hand-authored)` heading is a scope breach; `Spec & Plans` would have been appropriate | ❌ **FALSE POSITIVE — contradicts the frozen spec** | AC-8 (§ 207) **explicitly permits** the heading: *"Adding a heading is the one permitted departure from 'no other line changes'."* It also **pre-ruled Aider's recommendation out**: § 16 R-4 and AC-8 both name `Spec & Plans (pre-existing)` *"also not a clean fit"* and forbid filing the doc under a heading that misdescribes it — *"that would be exactly the small, confident falsehood this story exists to remove."* Aider's factual sub-claim is correct (`agents-add-model-runbook.md` does sit there, `docs/index.md:64`) but it is the **premise R-4 examined and rejected**, not new information. `git diff --numstat` → `4  0`: heading + entry + the two blank lines Markdown requires around a heading; **zero existing lines modified**. The § 14 justification AC-8 demanded is present. Adopting this finding would require overturning a validate-pass ruling on reviewer preference — forbidden by § 5 / D-2. |
| **3** | *Critical* — G26-LIB: the story title may imply rollout completion | ⚪ **NOISE — out of scope, and the title is not this story's to coin** | The title originates in the epic sketch (`epics.md:4435`, `:4597` — *"Story 54.3 — Rollout, docs, and category governance (FR26-GOV-1)"*) and is the `sprint-status.yaml:409` story key. It predates the story file; renaming it would desynchronise three planning artifacts to fix an implication Aider itself concedes the content does not make (*"the content appears honest"*). The honesty obligation is discharged where it belongs, in prose: § 14.6 and § 17.4 state **`G26-LIB` 🔓 OPEN**, no physical Android Chrome smoke run or claimed, `mobile-*` projects are Pixel 5 **emulation**; § 17.4 records a full-text read of all five doc files finding no *"rollout complete"* and no device-verification sentence, *"despite the story's own title"* — the exact risk Aider raises, already audited. **`G26-LIB` remains 🔓 OPEN after this arbitration.** |
| **4** | *Important* — AC-6: the required inline attribution *"corrects a pre-existing defect …"* is **not present in the diff** | ❌ **FALSE POSITIVE — the text is in the diff hunk and in the tree** | `grep -n "corrects a pre-existing defect" docs/agents-add-model-runbook.md` → **`:436`**: *"(This corrects a pre-existing defect in this runbook dating from the Initiative-11 default-deny work; it is not an Initiative 26 change.)"* — italicised, inline, in the same `+` hunk that makes the auth correction. AC-6 is fully discharged inline; nothing is owed at commit for it. |
| **5** | *Important* — AC-9: the scan table / commanded output is absent from the Dev Agent Record | ❌ **FALSE POSITIVE — present, most likely truncated out of the reviewed diff** | § 14.7 (this file, `:581-603`) carries the three commands verbatim, the root-`*.md` zero-hit check, and the full **eight-row** hit table `H-1…H-8` with a disposition and reason for each (corrected / historical-and-qualified / no action + why). That is exactly AC-9's demand. It sits inside the `+886`-line story-file addition; at 63k tokens sent against a 1259-line diff, the reviewer plausibly never received it. `sprint-status.yaml:542` carries the Initiative-26 discharge annotation with `status:` correctly left **`open`** per D-7. |
| **6** | *Minor* — AC-2's Story 49.3 § 6 F-7 amendment note is not in the diff | ✅ **VALID BUT NOT ACTIONABLE HERE — already recorded as owed at commit** | Correct and already on the books twice. AC-2 requires the note *"in the commit body **or** an inline note"*; inline was rejected because AC-2 simultaneously requires every other line of `docs/operations.md` byte-unchanged, so the obligation transferred to the commit body. Exact required text is pre-written at **§ 14.8**; it is item 1 of **§ 17.5**. No dev, review or arbitration pass commits, so this cannot be discharged by any of them. **It remains a hard precondition on the commit — this arbitration does not waive it.** |
| **7** | *Missing* — no `check-all` evidence and no zero-product-change proof in the diff | 🔗 **EXTERNAL EVIDENCE — correct that it is not in the diff, independently re-verified here** | Gate evidence is a run log, not a diff artifact. Re-read directly in this pass: `.hermes/run-logs/check-all-54-3-controller-bg-20260731_203955.log` → **`passed:  16`**, sixteen `✓` stages with **no `✗`**, **`all green.`**, **`CHECK_ALL_EXIT=0`**. Scope proof re-run here, not inherited: `git status --porcelain \| grep -E '^..(apps\|workers\|infra)/'` → **no output**; `\| grep '\.png$'` → **no output**. `git diff --stat` → 8 files, all under `docs/` or `_bmad-output/`. AC-10 holds. Provenance stays honest: § 14.9 states the gate was completed **by the controller** after the dev session timed out mid-`pytest`, and § 17.3 states `check-all` was **not** re-run after the review repairs, with the stage-coverage reasoning for why it need not be. |

**Net: 0 actionable, 4 false-positive, 1 noise, 1 valid-and-already-recorded (commit-time), 1
external-evidence-confirmed.** No product doc was edited by this arbitration and no AC was
re-opened. The two reviews do not actually disagree on any fact — findings 1 and 2 were reached
independently by § 17.2 and dismissed there on the same grounds, and findings 4, 5 and 7 dissolve
once the artifacts are opened, which the Aider environment could not do.

**Unchanged by this pass, restated so nothing is read as expanded:** status stays **`done`**
(review gate discharged only). **`G26-LIB` 🔓 OPEN.** **`G26-DEVGO`** unchanged. No physical
Android Chrome smoke was run or claimed. **No human review of any kind — this is an agent
arbitration pass by repo-local Claude Opus 5, NOT an Ezop signature.** `docs/project-overview.md`
H-3 remains a live, unfixed falsehood awaiting controller routing (§ 14.7 H-3, § 17.5.3).
`check-all.sh` was **not** re-run by this pass — it read the controller's log. Nothing was
committed, staged, merged or deployed.
