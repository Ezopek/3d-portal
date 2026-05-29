---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Spoolman integration discovery for a future 3d-portal initiative'
session_goals: '(1) Enumerate the integration scope space (read-only mirror → full bi-directional management → portal-as-source-of-truth) before any PRD; (2) Map data ownership topology and coupling boundaries to existing catalog/share/sot modules and the still-unbuilt queue/printer/requests slots; (3) Surface security/auth/network-boundary constraints introduced by reaching the .190 Spoolman instance; (4) Define candidate MVP slices that can be executed under existing BMAD initiative discipline; (5) Record assumptions and open decisions for downstream bmad-create-prd / bmad-correct-course routing.'
selected_approach: 'AI-recommended progressive flow'
techniques_used: ['First Principles Thinking', 'Morphological Analysis', 'What If Scenarios', 'Reverse Brainstorming', 'Six Thinking Hats', 'Constraint Mapping']
ideas_generated: 118
context_file: ''
workflow_completed: true
autonomous_facilitation: true
---

# Brainstorming Session Results

**Facilitator:** Ezop (autonomous; operator absent — facilitation is AI-driven per parent-controller directive "do not ask the operator broad questions; record assumptions and unknowns")
**Date:** 2026-05-29

## Session Overview

**Topic:** Spoolman integration discovery for a future 3d-portal initiative.

**Goals:**

1. Enumerate the integration scope space — from read-only mirror at one end to portal-as-source-of-truth at the other — before any PRD is written.
2. Map the data-ownership topology and coupling boundaries to existing portal backend modules (catalog / share / sot / admin / auth / invite / runbook) and the still-unbuilt queue/printer/requests slots.
3. Surface security, auth, and network-boundary constraints introduced by the portal reaching the standalone Spoolman instance running on `.190`.
4. Define candidate MVP slices small enough to fit one BMAD initiative under current single-developer pacing.
5. Record assumptions and open decisions cleanly so the downstream `bmad-create-prd` / `bmad-correct-course` step has unambiguous starting ground.

### Context Guidance

This session runs in **autonomous facilitation mode**. Operator (Michał) is not in the loop. Standard step-by-step user prompts in the bmad-brainstorming skill are skipped; the facilitator records assumptions inline (tagged `**Assumption:**`) and open decisions inline (tagged `**Open decision:**`) rather than asking the operator to resolve them. The downstream `bmad-create-prd` cycle is the right place to convert those into operator-confirmed decisions.

### Verified facts in force at session start (controller-supplied; treat as ground truth)

**Spoolman instance (.190 homelab):**

- Deployed at `/mnt/raid/docker-compose/spoolman` on ezopnas .190.
- `docker-compose.yml` is a symlink to `configs/docker-compose-recipes/spoolman.yml` (i.e. instance config is already owned by the `~/repos/configs` repo, NOT by 3d-portal).
- Image: `ghcr.io/donkie/spoolman:latest`.
- Host port `7912` → container port `8000` (standard Spoolman API port).
- Container status at session start: `Up 4 days`.
- Spoolman version: `0.23.1`.
- Storage: SQLite, on-disk data dir under the compose mount.
- **No auth observed on the localhost API** — direct calls from `.190` to `localhost:7912/api/v1/*` succeed with no credential.

**Current inventory (Spoolman side, snapshot at session start):**

- 9 active spools, 16 filaments, 2 vendors.
- Materials present: PCTG, PETG, PLA, TPU.
- Two active spools below 200 g (low-stock candidates):
  - Spool 21 — PLA Speed Matt White / Rosa3D — 138.9 g remaining.
  - Spool 25 — PCTG Army Green / Rosa3D — 163.2 g remaining.

**Spoolman API surface (per upstream docs, v0.23.x):**

- REST API v1 rooted at `/api/v1/`.
- CRUD endpoints for `spool`, `filament`, `vendor`.
- Spool-mutation endpoints: `POST /spool/{id}/use` (consume), `PUT /spool/{id}/measure` (re-measure).
- Export endpoints for backup / bulk read.
- Settings endpoints.
- Websocket support is documented for live mutation updates.

**3d-portal side, current shape (verified by file inspection at session start):**

- Backend modules in `apps/api/app/modules/`: `admin`, `auth`, `invite`, `runbook`, `share`, `sot`, `catalog`. **No `spools/` module exists** despite the AGENTS.md "v2 slot" mention — the placeholder is frontend-only.
- Frontend modules in `apps/web/src/modules/`: `admin`, `auth`, `catalog`. **No `spools/` module folder.**
- The only spool-related code in the repo is the route stub at `apps/web/src/routes/spools/index.tsx` rendering `<ComingSoonStub moduleKey="spools" />`, a ModuleRail entry at `apps/web/src/shell/ModuleRail.tsx:11`, and i18n strings (`modules.spools` → "Spools" / "Filamenty"). Generated routes referencing `/spools/` exist in `routeTree.gen.ts` but only point at the ComingSoon stub.
- Architecture doc (`docs/architecture.md:45`) explicitly tags Spoolman integration as the `modules/spools/` slot with an HTTP client to the existing compose, no detail beyond that.
- The 2026-05-04 SoT design (`docs/superpowers/specs/2026-05-04-portal-source-of-truth-design.md:46`) explicitly punted: *"Filament cost calculator / Spoolman integration (separate brainstorm)"* — this session **is** that brainstorm.

### Hard constraints in force during this session

- **HC1 — No code modification.** This is a discovery session producing an artifact under `_bmad-output/brainstorming/` only. No backend or frontend code is touched.
- **HC2 — Spoolman instance is `configs/`-owned infrastructure.** Spoolman compose lives in `~/repos/configs/docker-compose-recipes/`. Per AGENTS.md § Scope boundaries, infra concerns belong to `configs`, not to 3d-portal initiatives. Any deploy-shape change to Spoolman itself (e.g. enable auth, expose externally, switch storage backend) is `configs/`-side work; only the **app-layer integration** is portal scope.
- **HC3 — Portal must not silently mutate Spoolman state.** Spoolman is currently the operator's primary inventory ground truth (used outside the portal too — Orca slicer-side or direct UI). Any portal-driven mutation that the operator did not initiate from the portal UI is a trust-failure vector.
- **HC4 — Single-developer pace.** Initiatives are scoped accordingly. A "build everything in one initiative" outcome is the wrong outcome from this brainstorm; the right outcome is an MVP slice + explicit deferral list.
- **HC5 — Read-only catalog data flow already established.** The portal currently never writes outside its own DB (catalog is read-only on the Windows-source side; runbook → SoT is portal-internal). Spoolman integration is the first prospective write-to-external-system surface and that should be a deliberate decision, not an accident of "well, the API supports POST".

## Technique Selection

**Approach:** AI-Recommended Progressive Flow.

**Recommended sequence (executed in this session):**

1. **First Principles Thinking** (creative, foundation) — Strip the question to fundamentals. What does the operator actually need from "portal × Spoolman" that isn't already covered by visiting `:7912` directly? Surfaces the real value hypothesis before scope-creep dominates the discussion.
2. **Morphological Analysis** (deep, structural) — Build the parameter grid: integration depth × data-ownership locus × auth surface × consumer-module set × failure semantics × deployment shape. Forces exhaustive coverage of the option space rather than the AI defaulting to the first "Spoolman client module" gestalt that came to mind.
3. **What If Scenarios** (creative, edge-case generation) — Stress-test promising cells of the morphological grid against high-impact "what if X breaks / changes / scales / pivots" futures.
4. **Reverse Brainstorming** (creative, failure-mode mining) — Ask "how would we build this most catastrophically?" to surface anti-patterns that would otherwise hide in a forward-only design.
5. **Six Thinking Hats** (structured, multi-perspective) — Apply white (facts) / red (gut) / yellow (benefits) / black (risks) / green (creative) / blue (process) lenses to the top morphological-grid cells. This is the convergent move toward MVP-slice candidates.
6. **Constraint Mapping** (deep, real-vs-imagined limits) — Identify which constraints are hard (HC1–HC5), which are soft (operator preference, deferred-decision), which are imagined (assumed-but-unverified). Output feeds the open-decisions register for the downstream PRD step.

**AI rationale:** Spoolman integration is structurally the *opposite* of the share-flow discovery from 2026-05-25 — that was an exhaustive enumeration of a fixed product surface (recipient states × sender intents). This one is a **scope-shaping** problem: the option space is wide-open and the *first* failure mode is over-scoping the MVP. First Principles + Morphological enforces structural rigour first; What If + Reverse hunt edge cases; Six Hats converges to MVP; Constraint Mapping cleans up open decisions for PRD handoff. Sequence fits the controller-named scope dimensions (scope options, data ownership topology, coupling, security/auth, configs-vs-app, MVP slices, risks, open decisions) without duplicating effort across techniques.

---

## Phase 1 — First Principles Thinking

**Prompt:** *Strip away every assumption about "how a portal integrates with Spoolman" and ask: what does the operator actually need that direct use of `:7912` does not already provide?*

### What is already true at session start (no portal involvement needed)

- F1. Spoolman has a working web UI at `http://.190:7912/`. Operator can already inspect spools, filaments, vendors there directly.
- F2. Spoolman already integrates with Orca / Bambu Studio for sticker / spool-id workflows independently of the portal.
- F3. Spoolman already supports manual `use` and `measure` calls via its own UI — the operator can record consumption events without any portal layer.
- F4. The portal has no inventory display surface today — catalog is model-centric, not material-centric.
- F5. The portal has no print-queue surface today either — there is no per-print material reservation to coordinate with.

### What the portal can plausibly offer beyond direct Spoolman use (raw ideas, divergent)

1. **Single-pane-of-glass surfacing** — show low-stock spools on the portal landing page so the operator sees stock pressure while browsing the catalog, not only when they remember to visit `:7912`.
2. **Per-model material requirement display** — when viewing a catalog model, show "this model wants PETG black; you have 1 active PETG black spool with 412 g".
3. **Match-warnings on print intent** — flag "you want to print model X (estimated 180 g PETG), low-stock spool 22 (PETG, 220 g) is the only candidate" so the operator notices stock-tightness before queuing.
4. **Catalog-to-spool linking** — annotate catalog models with a `default_material` / `recommended_filament` SoT field so the portal can compute spool matches.
5. **Inventory at-a-glance dashboard** — replace the deferred v1 landing page with a real dashboard surfacing spool/filament aggregates.
6. **Sharable inventory snapshot** — extend the existing `/share/<token>` mechanism to share a public read-only inventory view ("here's what I can print right now, in PETG").
7. **Print request module's missing piece** — the deferred requests/ module needs to know whether a request is materially fulfillable. Spoolman is the obvious feed.
8. **Filament catalog discovery** — surface the portal's filament library as a richer browse view (search by material/color/vendor) than Spoolman's stock UI.
9. **Mobile-friendly read** — Spoolman's UI is desktop-leaning; portal's mobile catalog UI could carry inventory views into the operator's phone-by-the-printer use case.
10. **Audit log of consumption events** — Spoolman has its own log but the portal could correlate `use` events back to specific print runs once the queue module exists.

### First-principles distillation — what does this collapse to?

After running through F1–F5 and ideas 1–10, the *minimum-viable value* the portal can add splits into three orthogonal axes that any MVP slice should be picked from:

- **Axis V1 — Read-side surfacing:** show Spoolman data inside portal contexts (landing dashboard, catalog model detail, share view). Pure benefit; no Spoolman mutation. Risk floor.
- **Axis V2 — Catalog ↔ filament linkage:** introduce a *new* portal-owned annotation (`default_material` / `recommended_filament`) on catalog models, enabling match-against-stock features. Touches portal SoT, not Spoolman.
- **Axis V3 — Mutation surface:** portal triggers Spoolman writes (consumption, re-measure, possibly spool / filament CRUD). Risk ceiling.

**Insight (recorded for PRD handoff):** Axis V1 alone may already deliver 70–80% of the operator-experienced value, because the gap today isn't "can't change Spoolman" — Spoolman's own UI handles that fine — it's "the catalog and the inventory live in two separate tabs that never see each other". MVP should weight V1 heavily and treat V2 + V3 as later slices.

**Assumption:** The operator's primary unmet need is *contextual surfacing*, not *better mutation UX*. This is the load-bearing assumption of the entire integration value hypothesis. If wrong, the MVP shape shifts. The PRD step is where this assumption gets confirmed or revised.

---

## Phase 2 — Morphological Analysis

**Prompt:** *Build the parameter grid for "portal × Spoolman" so no cell of the option space is left undefined-by-default.*

### Parameters and options

**P1 — Integration depth**

- P1a. None (status quo — `ComingSoonStub` stays).
- P1b. Read-only mirror (portal periodically polls Spoolman and caches; no live calls on page render).
- P1c. Read-through proxy (portal forwards reads to Spoolman live, optional cache layer).
- P1d. Read-through + restricted write (consumption, measurement) — explicit per-operation allowlist.
- P1e. Full bi-directional CRUD (spool / filament / vendor create / update / delete from portal UI).
- P1f. Portal as source of truth — Spoolman becomes a downstream consumer that portal pushes to (and/or Spoolman is decommissioned in favor of a portal-native spools module).

**P2 — Data-ownership locus**

- P2a. Spoolman owns everything; portal is purely a view.
- P2b. Spoolman owns inventory state; portal owns *linkage* (catalog ↔ filament default, print run ↔ spool consumed, etc.).
- P2c. Portal owns inventory state; Spoolman is the legacy view (migration future).
- P2d. Mixed: portal owns derived/aggregate (low-stock thresholds, per-material totals, recommendations); Spoolman owns raw entities.

**P3 — Auth surface on Spoolman**

- P3a. Status quo — no auth (rely on network isolation — Spoolman bound to `localhost:7912` on `.190`).
- P3b. Network-level allowlist — Spoolman exposed to portal container only (docker network sharing), still no app-level auth.
- P3c. Add proxy-side auth — nginx-190 fronts Spoolman with the portal's auth cookie (treats Spoolman like another protected service).
- P3d. Add Spoolman-native auth — Spoolman gains real auth (upstream feature; not currently observed). Requires upstream support check.

**P4 — Transport from portal-api to Spoolman**

- P4a. Direct HTTPS from portal-api container to `http://localhost:7912/api/v1/` via host networking.
- P4b. Direct via internal docker network (Spoolman container reachable as `spoolman:8000` from portal-api container).
- P4c. Via nginx-190 (`https://3d.ezop.ddns.net/spoolman/...` or similar) — adds TLS + uniformity but adds a hop.
- P4d. Via a portal-side asyncio HTTP client + connection pool + circuit breaker (httpx + retry policy).
- P4e. Via a thin sidecar service in `apps/api/app/modules/spools/` that owns all Spoolman calls (encapsulation; testable seam).

**P5 — Consumer modules inside portal**

- P5a. Landing page only (low-stock surface).
- P5b. Landing page + catalog model detail (per-model material match).
- P5c. + share view (sharable inventory snapshot).
- P5d. + queue (per-queued-print material reservation).
- P5e. + printer (live consumption while a print runs).
- P5f. + requests (materially fulfillable check on incoming print requests).
- P5g. + admin (operator-only inventory management surface).
- P5h. All of the above.

**P6 — Failure semantics when Spoolman is unreachable**

- P6a. Hard fail — portal page returns error; matches "Spoolman down means inventory features are down".
- P6b. Soft fail — show cached snapshot with a `stale since HH:MM` indicator.
- P6c. Silent fail — hide inventory widgets entirely when source is unreachable (clean but hides the dependency from the operator).
- P6d. Degraded fail — surface the dependency in the runbook module and a small banner in the inventory widget itself.

**P7 — Caching strategy**

- P7a. No caching — every read hits Spoolman.
- P7b. Per-request cache (memoize within one portal request lifecycle).
- P7c. Short-TTL Redis cache (e.g. 30 s — for landing dashboard aggregates).
- P7d. Long-TTL Redis cache + Spoolman websocket invalidation (real-time-correct without polling).
- P7e. Full local mirror — portal mirrors Spoolman's spool/filament/vendor tables into its own DB nightly, treats them as read-only.

**P8 — Update propagation (Spoolman → portal)**

- P8a. Pull on demand only.
- P8b. Periodic background pull (arq worker job; e.g. every 60 s).
- P8c. Spoolman websocket subscription (portal-api maintains a long-lived ws connection and invalidates cache on mutation events).
- P8d. Spoolman webhook (Spoolman pushes to portal endpoint — requires Spoolman config / possibly upstream support check).

**P9 — Mutation policy (if P1d or beyond)**

- P9a. No mutations from portal — explicit "view only" UX even where Spoolman API supports writes.
- P9b. Operator-confirmed mutations only — every write goes through a confirmation dialog with diff preview.
- P9c. Optimistic mutations with undo window.
- P9d. Fire-and-forget mutations.

**P10 — Configs-vs-app split**

- P10a. Spoolman compose stays in `configs/`; portal scope adds `modules/spools/` to `apps/api/` + `apps/web/`. (Most likely.)
- P10b. Move compose into 3d-portal `infra/`. (Violates HC2 — infra belongs in `configs`.)
- P10c. Spoolman compose moves under portal's deploy script for unified deploys, but file still lives in `configs/`.

**P11 — Identity / linkage between catalog models and Spoolman entities**

- P11a. No linkage — features operate purely on aggregate / category data ("you have PETG").
- P11b. Per-model `default_material` text field (free-form, fuzzy-matched).
- P11c. Per-model `recommended_filament_id` referencing a Spoolman filament-id (tight coupling, risk of dangling refs if Spoolman entities deleted).
- P11d. Per-model `recommended_material_profile` referencing a portal-owned profile that itself maps to Spoolman filaments (decoupled; allows the same profile to match multiple Spoolman entities).

**P12 — Multi-vendor / multi-instance future**

- P12a. Hardcode the single `.190` Spoolman instance.
- P12b. Configurable instance URL (env var) but only one at a time.
- P12c. Support N Spoolman instances (e.g. one per physical print room) — overengineering for current single-printer setup.

**P13 — Observability**

- P13a. Reuse existing structured-log contract; tag Spoolman calls with `external_service=spoolman` per `~/repos/configs/docs/observability-logging-contract.md`.
- P13b. Add a Spoolman-specific tracing span around every call.
- P13c. Expose `/api/internal/health/spoolman` for `.190`-side liveness probes.
- P13d. Add a Sentry/GlitchTip breadcrumb category for Spoolman calls.

**P14 — Testing posture**

- P14a. Fully mocked Spoolman in pytest (httpx mock).
- P14b. Spin a Spoolman container in CI / tests (docker-compose sidecar).
- P14c. Pact-style consumer contract tests against a captured Spoolman OpenAPI spec.
- P14d. Per-call mock + one happy-path live integration test against `.190` (gated by env flag).

**P15 — Localization**

- P15a. Reuse existing PL/EN keys; add `modules.spools.*` namespace.
- P15b. Spoolman's own data (vendor names, filament names, materials) stays untranslated.
- P15c. Material names (PCTG, PETG, PLA, TPU) treated as proper nouns, not localized.

### Combination filters — which cells are obviously absurd / disqualified

- P1f × P10a: portal-as-SoT while compose lives in `configs/` and Spoolman is still actively used. **Eliminated** — too much migration weight for an MVP-discovery output.
- P1e × P3a: full CRUD over an unauthenticated upstream. **Eliminated** for any internet-reachable deployment shape; survivable only if P3b (network isolation) is locked in *first*.
- P11c with no migration plan when Spoolman entities are deleted. **Eliminated** — must come with P11d or a deletion-rejection hook on Spoolman side.
- P12c: multi-instance Spoolman. **Eliminated** for MVP — no operator demand signal.

### Recommended baseline cell (carries into Phase 5 — Six Hats)

**Baseline MVP cell:** `P1b + P2b + P3a + P4b + P5a + P6b + P7c + P8b + P9a + P10a + P11a + P12a + P13a + P14a + P15a`.

In English: a portal-internal `modules/spools/` backend module that polls Spoolman over the internal docker network every 60 s, caches in Redis for 30 s, surfaces low-stock on the landing dashboard, no mutations, soft-fail with `stale-since` indicator, mocked in tests. No catalog-filament linkage yet. Single Spoolman instance. Reuse existing logging contract.

**Alternative cell to keep alive for Six Hats:** swap P5a → P5b (also catalog detail), P11a → P11b (`default_material` free-form), keep everything else. Adds the catalog ↔ filament connection but stays on free-form text to avoid foreign-key fragility.

---

## Phase 3 — What If Scenarios

**Prompt:** *Stress-test the baseline cells against high-impact futures.*

1. **What if Spoolman goes offline for 4 hours during a sync window?** — Baseline P6b (soft fail, stale indicator) handles it cleanly. Catalog browsing unaffected. ✓
2. **What if the operator switches to a different filament-tracking tool entirely (Filaman, custom)?** — Baseline P4e (encapsulating sidecar service) makes the swap a one-module replacement. ✓
3. **What if Spoolman upstream adds breaking API changes in 0.24?** — Baseline P14a (mocked) is *fragile* — mocks drift from reality. Recommend keeping P14d (one live integration test) as a smoke check. **Add to open decisions.**
4. **What if the operator deletes a filament in Spoolman that a catalog model references via P11c?** — Eliminated cell, but worth noting: if we ever go to P11c, we *must* have a deletion-aware sync. P11d sidesteps this entirely.
5. **What if portal sessions are very bursty (10 operators viewing landing simultaneously)?** — Spoolman handles 10 concurrent reads trivially; P7c (Redis 30 s TTL) makes it irrelevant anyway.
6. **What if the portal eventually goes public-shareable (`/share/<token>` with inventory)?** — Anonymous read of inventory is plausibly *fine* for an operator wanting to advertise "what I can print right now", but explicit operator opt-in per share token must gate it. Adds P5c-with-policy.
7. **What if Spoolman starts being mutated outside the portal (Orca-side use events)?** — Baseline P7c + P8b yields up-to-60-s lag, which is fine for a dashboard. Not fine for a per-print reservation system. **Implication: when queue/printer modules land, lag tolerance shrinks → P8c (websocket) becomes load-bearing.**
8. **What if we expose `/spools` to anonymous users?** — Surface info disclosure risk: spool quantities, vendor identities, material stocks. **Open decision:** what's the auth posture on `/spools/*` routes — full operator-only? Or operator-only with share-token override?
9. **What if Spoolman websocket goes silent without disconnecting (TCP half-open)?** — Health-check the websocket every N seconds; reconnect on silence. Standard pattern; add to P8c implementation note.
10. **What if Spoolman's SQLite DB corrupts?** — Out of portal scope (HC2). Portal's role is to soft-fail. The recovery is a configs-side restore.
11. **What if portal's own auth requirements change (Init 5 / Init 10 trajectory)?** — Spoolman calls are server-side; cookie-auth on the portal side is unchanged. Internal HTTP to Spoolman is not user-facing.
12. **What if multiple printers exist later (printer module v2)?** — Spool-to-printer assignment is a Spoolman feature; portal can surface it. Baseline doesn't conflict.
13. **What if the operator wants to define print-cost / material-cost calculations in the portal (per 2026-05-04 SoT design carveout)?** — This needs vendor pricing data. Spoolman stores vendor URL + name but not pricing by default. **Open decision:** is filament cost calculation in MVP scope or a separate downstream slice?
14. **What if the catalog model has multi-part prints requiring two different filaments?** — P11b (`default_material` free-form) handles "2 materials" via the text; P11d (recommended material profile) handles it cleanly. Lean toward profile-based.
15. **What if portal mounts a future webhook receiver for Spoolman?** — Requires public ingress to a portal endpoint plus Spoolman config. Higher complexity than P8c (portal pulls). Defer.
16. **What if the operator wants a "consumed during print run X" audit trail?** — Requires queue+printer modules to be live. Out of MVP scope. Note as P5e+P5d combined future slice.
17. **What if Spoolman starts running on a separate host (not `.190`)?** — Configurable instance URL handles it. P4b (internal docker net) becomes P4a-or-P4c (host network or nginx hop).
18. **What if portal needs to backfill historical use events?** — Spoolman has its own history. Portal does not need to mirror. Out of scope.
19. **What if the operator runs Spoolman locally on a laptop in addition to `.190`?** — P12c eliminated. If demand materializes later, treat as new initiative.
20. **What if Spoolman authentication is added upstream (P3d) someday?** — Portal needs a config slot for credentials. Plan for it in env var schema even before P3a → P3d transition. Costs ~zero to plan.

---

## Phase 4 — Reverse Brainstorming

**Prompt:** *How would we build "portal × Spoolman" most catastrophically? Each anti-pattern reveals an inverse design rule.*

### Anti-patterns

1. **Wire every portal page render directly to a synchronous Spoolman call with no timeout.** → Inverse: every external call has an explicit timeout + circuit-breaker. (Implementation rule.)
2. **Use Spoolman entity IDs as portal-side foreign keys with no deletion guard.** → Inverse: portal owns linkage profiles; Spoolman IDs are looked-up references, not FKs. (Re-confirms P11d.)
3. **Surface a "Delete spool" button in the portal UI before any usage telemetry confirms operators want it.** → Inverse: read first, write later; mutation slices come after explicit demand signal.
4. **Mix Spoolman compose move with portal-side integration in the same initiative.** → Inverse: keep configs-side and portal-side changes in separate initiatives — never blur the line that HC2 sets.
5. **Add `default_material` as a free-form text field with no normalization, then build "match-against-stock" features on top.** → Inverse: even free-form needs a normalization pass (uppercase + trim + alias-table for PCTG/PETG/PLA/TPU) before any matching logic.
6. **Skip integration tests because "the upstream API is stable".** → Inverse: keep P14d (one live happy-path test gated by env flag) as a tripwire.
7. **Hardcode `http://192.168.2.190:7912` in code.** → Inverse: env-driven (`SPOOLMAN_URL`) per portal config conventions.
8. **Log Spoolman responses in full at INFO level.** → Inverse: tag-and-summarize per the observability contract; do not leak vendor inventory into log indexes by default.
9. **Treat Spoolman's "no auth" as permanent.** → Inverse: plan auth-config slot in env even when unused — see What-If 20.
10. **Bind Spoolman scope to whatever's convenient for the queue module's eventual needs.** → Inverse: Spoolman MVP serves the landing-dashboard use case; queue-coordination is a *later* slice with its own scope.
11. **Polling-without-jitter from multiple portal-api workers simultaneously.** → Inverse: cache invalidation must be lock-protected (Redis SETNX or worker-leader) — only one portal-api worker polls per interval.
12. **Show inventory totals in a public landing page without gating.** → Inverse: confirm anonymous-read posture early (open decision 8 above).
13. **Sync Spoolman → portal but never reverse-sync — then add a portal-side spool create UI six months later without remembering it can drift.** → Inverse: write surface lands together with bidirectional consistency tests, or never.
14. **Mix observability events for Spoolman calls into the portal's generic external-call bucket so they're indistinguishable from Glitchtip POSTs.** → Inverse: distinct `external_service=spoolman` tag from day one.
15. **Render landing-dashboard inventory cards as default-on for all operators including future invitees who don't care.** → Inverse: per-user opt-in / role-tiered visibility (admin-only by default? — open decision).
16. **Cargo-cult import Spoolman's own UI design into portal pages, breaking the existing design system.** → Inverse: portal owns its UX; Spoolman data flows into shadcn/ui-based components that obey the catalog/admin visual language.
17. **Skip Spoolman version-pinning (`latest` tag).** → Out of HC2 scope — configs-side concern — but worth flagging upstream when this initiative starts.
18. **Conflate "filament" and "spool" in portal data model.** → Inverse: mirror Spoolman's distinction (filament = product SKU, spool = physical instance with weight) faithfully or it'll break the moment a second spool of the same filament arrives.
19. **Implement P8c (websocket) in MVP "because it's cooler".** → Inverse: P8b (periodic pull) is sufficient for landing-dashboard freshness; websocket arrives when queue module makes lag intolerable.
20. **Add `bmad-create-architecture` rerun for "Spoolman integration" before the PRD lands.** → Inverse: brownfield routing — `bmad-correct-course` first, then `bmad-edit-prd`, *then* whatever architecture/epics edits the correct-course step recommends. (Re-confirms AGENTS.md routing.)

---

## Phase 5 — Six Thinking Hats

**Applied to the baseline cell + alternative cell from Phase 2.**

### White hat — facts

- Spoolman is healthy, version-pinned-ish (`:latest`, 0.23.1 observed), running on the same host as the portal backend.
- 9 spools / 16 filaments — small enough that even an O(N) join across the entire dataset is irrelevant for performance.
- Two low-stock spools already present — the "low stock surface" feature has *immediate* signal, not a theoretical one. The MVP demo would actually show something useful on day one.
- Portal already has Redis (`apps/api/app/core/redis.py`) — caching layer is in place.
- Portal already has structured-log contract — observability story is well-defined.
- Spoolman API is REST + websocket; mature shape.

### Red hat — gut

- The "show low-stock on the landing page" feature is genuinely satisfying — the operator-developer (Michał) is the same person, and seeing "PCTG Army Green 163 g" on landing is a much better mental anchor than "go check Spoolman tab".
- The temptation to grow scope into "full inventory management UI in the portal" is strong but premature — Spoolman's own UI is fine.
- The catalog ↔ filament linkage feels like *the* unlock — the portal has model-level data, Spoolman has material-level data, joining them is exactly what neither tool alone can do. But it requires SoT schema additions to catalog, which is a separate decision surface.

### Yellow hat — benefits of the baseline cell

- Cheap to build (one backend module, one frontend page, no schema migration).
- Zero risk to Spoolman's existing state (read-only).
- Demonstrates the integration pattern (HTTP client + cache + soft-fail) cleanly, sets a template that future slices reuse.
- Immediately useful — low-stock visibility on landing replaces a placeholder.
- Aligns with the deferred v1 landing-page polish (`docs/plans/2026-05-01-design-polish.md` SLICE-09) — "real dashboard once aggregate data exists" → here's some.
- Configs-vs-app boundary is clean (HC2 respected).

### Black hat — risks of the baseline cell

- Soft-fail with `stale-since` indicator needs care so it doesn't look like a UI bug.
- Polling with multiple gunicorn / uvicorn workers needs leader-election (Redis SETNX or a worker-marker).
- Anonymous read of `/spools` (open decision 8) needs an explicit answer before the route ships.
- Free-form material strings (alternative cell P11b) will rot without a normalization pass.
- Test posture: P14a (fully mocked) is the standard ask; the live integration test (P14d) is a separate operational decision (env-gated).
- The "next slice" (catalog ↔ filament linkage) is *much* bigger than MVP — design the MVP's data model so the linkage step doesn't require ripping it out.

### Green hat — creative extensions (parking-lot, not MVP)

- **Sharable inventory snapshot via `/share/<token>`:** *"see what I can print right now"* shareable card. Plays with existing share-flow knowledge from the 2026-05-25 brainstorm.
- **Inventory-aware queue:** every queue entry checks materially fulfillable before accept. (Requires queue module first.)
- **Cost calculator:** per-print cost using filament-weight estimates × vendor pricing. (Requires vendor pricing data → separate spec.)
- **Low-stock notification:** Sentry-like alerting when a material drops below threshold.
- **Filament shopping list export:** portal generates a "PCTG / PLA need refilling soon" markdown export.
- **Per-printer spool assignment:** mirror Spoolman's printer-assignment data into portal printer module when it exists.

### Blue hat — process

- **Routing:** This is a brownfield post-MVP feature → entry skill is `bmad-correct-course`. *Not* `bmad-create-prd` (that's greenfield-only per AGENTS.md § Workflow expectations).
- **Artifacts to expect from the next BMAD step:** PRD edit (initiative-level H2 append on `prd.md`), possibly architecture H2 append, epic + story breakdown.
- **MVP-as-initiative shape:** one BMAD initiative covering the baseline cell with the catalog-linkage (alternative cell) flagged as a candidate **Phase 2** within the same initiative or as a follow-up initiative — `bmad-correct-course` chooses.
- **Cross-repo coordination:** if any Spoolman compose-side change is needed (e.g. expose Spoolman on internal docker network to portal-api container), that's a `configs/` PR done in coordination, not in 3d-portal scope. See HC2.
- **Definition-of-done test:** a fresh operator pulls main, runs deploy, opens `https://3d.ezop.ddns.net/`, and sees a low-stock card with the two spools above (or whatever the live state is) without any manual config beyond `SPOOLMAN_URL` env var.

---

## Phase 6 — Constraint Mapping

**Prompt:** *Separate hard / soft / imagined constraints. Output is the open-decisions register for PRD handoff.*

### Hard constraints (cannot be moved by this brainstorm)

- HC1–HC5 above (no code mod / configs-owns-infra / no silent mutation / single-dev pace / first-write-external decision).
- Brownfield routing — `bmad-correct-course` is the canonical entry; vanilla BMAD discipline applies (AGENTS.md § BMAD vanilla-first).
- Deploy gate behavior — any commit that ships portal-side Spoolman code triggers `infra/scripts/deploy.sh`; `docs:` / `chore:` prefixes skip per range-gate.
- Cookie-auth, JWT structure, AuthGate shell pattern (Init 6 + 10 retros — see AGENTS.md § Conventions on frontend auth gating discipline).

### Soft constraints (operator preference, deferred-decision, movable with rationale)

- SC1. Read-first, write-later default — strongly preferred but the operator could overrule for a specific high-value mutation (e.g. one-click "mark consumed" after a print).
- SC2. Polling cadence — 60 s is a starting guess. Could go to 30 s without strain. Could go to 5 s if a queue-side use case demands it (not in MVP).
- SC3. Cache TTL — 30 s is a guess. Trade-off is "freshness vs Spoolman load" — Spoolman load is irrelevant at current scale.
- SC4. Visibility scope — anonymous vs operator-only on `/spools` is genuinely undecided.
- SC5. Material-linkage representation — `default_material` text vs `recommended_material_profile` object. PRD-stage decision.
- SC6. Multi-printer future — not in MVP; movable when printer module lands.

### Imagined constraints (assumed but unverified — needs checking before relying on)

- IC1. **"Spoolman has no auth"** — verified at localhost only. Whether Spoolman binds to `0.0.0.0` or `localhost` on `.190` affects exposure. **Open decision:** confirm bind address before assuming network isolation is doing the work.
- IC2. **"Spoolman websocket is reliable"** — documented but unverified at the homelab scale. Defer the question; P8b (polling) covers MVP.
- IC3. **"Spoolman OpenAPI is stable across 0.23 → 0.24"** — assumed. Mitigation: P14d live test catches regressions; pin major version in env / docs.
- IC4. **"PCTG / PETG / PLA / TPU are the full material set"** — true at session start, will expand. Material set must be data-driven, not enum.
- IC5. **"Operators using the portal will be the same person as the operator using Spoolman directly"** — true today (single-dev), false if invitees + printer-share scope grows. Affects visibility decisions.

### Open decisions for PRD handoff

The following decisions are explicitly out-of-scope for this brainstorm and belong to `bmad-correct-course` / `bmad-edit-prd`. Listed here so the PRD step has them ready:

- OD1. **Initial slice scope** — baseline cell (low-stock landing card only) vs baseline + catalog detail (catalog ↔ free-form material match). Recommended: baseline-only MVP, catalog linkage as Phase 2.
- OD2. **Auth posture on `/spools` route** — admin-only / operator-only / anonymous-with-share-token / public-with-opt-in.
- OD3. **Material-linkage representation** — text field (`default_material`) vs profile (`recommended_material_profile`) on catalog SoT. (Catalog-side schema decision — requires SoT-design follow-up.)
- OD4. **Transport** — internal docker network (P4b) vs nginx-hop (P4c). Cleaner is P4b but requires Spoolman container to be reachable on the portal docker network — that's a `configs/`-side compose change.
- OD5. **Caching & propagation** — P7c (Redis 30s TTL) + P8b (60s poll) for MVP, or skip cache and go straight to P8c (websocket). Recommended: P7c + P8b; defer P8c.
- OD6. **Test posture** — mocked-only (P14a) vs +live-integration (P14d). Recommended: both — mock for unit speed, one live smoke gated by env.
- OD7. **Cost calculator inclusion** — Spoolman doesn't store pricing by default; cost calc requires either Spoolman extension or portal-side pricing schema. Recommended: punt to separate brainstorm/initiative.
- OD8. **Spoolman bind address verification** — confirm Spoolman is bound to a non-public interface on `.190` before relying on "no auth is fine". This is a configs-side verification, not a portal-side decision, but it gates portal's transport choice.
- OD9. **Filament identity model** — mirror Spoolman's filament vs spool distinction in portal-side cache (recommended) or collapse to spool-level only (simpler but loses semantic clarity).
- OD10. **Naming** — module name `spools/` (current placeholder) vs `inventory/` vs `filaments/`. Current `spools/` is fine and lower-churn; flagging because PRD might propose otherwise.

---

## Idea Organization and Prioritization

### Thematic organization (mapped to the controller-named axes)

#### Theme 1 — Scope options

- T1.1 Read-only mirror with portal-side cache (Phase 2 P1b — **baseline MVP cell anchor**).
- T1.2 Read-through proxy (no cache; P1c — rejected for MVP, useful for very-small-scale ops).
- T1.3 Read + restricted-write (consumption / re-measure only; P1d — Phase-2 candidate).
- T1.4 Full bi-directional CRUD (P1e — explicit non-goal for any current initiative).
- T1.5 Portal-as-SoT migration (P1f — non-goal; eliminate).
- T1.6 Catalog ↔ filament linkage layer (V2 axis, orthogonal to T1.1–T1.5).
- T1.7 Sharable inventory snapshot via `/share/<token>` (parking lot — green hat).
- T1.8 Inventory-aware queue (parking lot — requires queue module).
- T1.9 Cost calculator (parking lot — separate brainstorm per 2026-05-04 SoT design carveout).
- T1.10 Low-stock notification / alerting (parking lot).
- T1.11 Shopping-list export (parking lot).
- T1.12 Mobile-friendly inventory read (collapsed under T1.1 — comes for free with shadcn/ui responsive defaults).
- T1.13 Per-printer spool assignment mirror (parking lot — requires printer module).
- T1.14 Vendor browse view (parking lot — low priority).
- T1.15 Material category browse / filter UI (parking lot — small standalone slice).

#### Theme 2 — Data-ownership topology

- T2.1 Spoolman-owns-all + portal-views-only (P2a) — baseline.
- T2.2 Spoolman-owns-inventory + portal-owns-linkage (P2b) — recommended target shape once T1.6 lands.
- T2.3 Mixed: portal owns derived/aggregates (P2d) — natural extension.
- T2.4 Portal-owns-inventory + Spoolman as legacy view (P2c) — non-goal.
- T2.5 Identity strategy: free-form text (P11b) — pragmatic short-term.
- T2.6 Identity strategy: profile object (P11d) — pragmatic long-term.
- T2.7 Identity strategy: direct FK to Spoolman ID (P11c) — disqualified without deletion guard.
- T2.8 Filament-vs-spool distinction preserved (anti-pattern 18 fix).

#### Theme 3 — Coupling to catalog / queue / printer / share / requests

- T3.1 Coupling to catalog — additive (new optional SoT field; no removal of existing catalog semantics).
- T3.2 Coupling to queue — deferred until queue module exists; coupling design enforces material reservation but lives in queue's PRD.
- T3.3 Coupling to printer — deferred; per-printer spool assignment is a printer-module concern.
- T3.4 Coupling to share — feasible (T1.7) but explicit operator opt-in required.
- T3.5 Coupling to requests — deferred; fulfillability check is a requests-module concern that *reads* the spools module.
- T3.6 Coupling to admin — admin gets a "Spoolman status" panel + future linkage management UI.
- T3.7 Coupling to runbook — Spoolman-down event surfaces in runbook module as soft-fail context.
- T3.8 Coupling to auth — none new; existing cookie-auth covers it.
- T3.9 Coupling to sot — material-linkage may add a SoT field if T1.6 lands.
- T3.10 Coupling to invite — irrelevant (invite is auth-flow plumbing).

#### Theme 4 — Security / auth / network-boundary

- T4.1 Network-isolation as the only protection (P3a) — viable if Spoolman bind address confirmed (OD8).
- T4.2 Docker-internal network sharing (P3b) — recommended for transport.
- T4.3 nginx-fronted Spoolman (P3c) — overkill for MVP; useful if external access to Spoolman is wanted.
- T4.4 Spoolman-native auth (P3d) — upstream support unconfirmed; plan env slot for credentials regardless.
- T4.5 `/spools` route auth — admin-only by default for MVP; revisit per OD2.
- T4.6 Anonymous share-token inventory read — explicit opt-in per share token.
- T4.7 Log content scrubbing — anti-pattern 8 fix: never dump full Spoolman responses at INFO; summarize.
- T4.8 Outbound HTTP allowlist — portal-api now talks to an external service; verify any egress policy on `.190` doesn't block it.

#### Theme 5 — Configs vs app split (HC2)

- T5.1 Spoolman compose stays in `configs/docker-compose-recipes/spoolman.yml` — invariant.
- T5.2 Any docker-network reshape (T4.2) is a configs-side compose change.
- T5.3 Portal owns the `apps/api/app/modules/spools/` module — new code surface.
- T5.4 Portal owns the `apps/web/src/modules/spools/` frontend module — new code surface.
- T5.5 Spoolman version-pin / image-pin discussion belongs in configs follow-up, not portal.
- T5.6 Spoolman backup / restore belongs in configs runbook, not portal runbook.
- T5.7 Spoolman observability sinks (otel, Sentry/GlitchTip) belong in configs.

#### Theme 6 — MVP slice candidates

- T6.1 **Slice MVP-A (recommended):** Baseline cell — `modules/spools/` backend module + `/spools` frontend landing-card-style view showing low-stock spools, periodic poll + Redis cache + soft-fail. Admin-only by default. ~ 1 BMAD initiative, ~ 3–5 stories.
- T6.2 **Slice MVP-B:** MVP-A + catalog-detail "this model wants PETG; you have 1 active PETG spool" annotation, free-form material text. ~ 2 stories on top of MVP-A.
- T6.3 **Slice MVP-C (Phase 2):** Add `recommended_material_profile` SoT structure + matching against Spoolman filaments. Multi-story; touches catalog SoT.
- T6.4 **Slice MVP-D:** Restricted-write — operator-confirmed `use` and `measure` mutations. Pre-requisite: usage telemetry from MVP-A/B suggests the write surface is worth building.
- T6.5 **Slice MVP-E (parallel future):** Share-token inventory snapshot.

#### Theme 7 — Risks

- T7.1 Test mock drift vs upstream API changes — mitigation: live smoke test (OD6).
- T7.2 Multi-worker poll thundering herd — mitigation: leader-election or single-poller worker.
- T7.3 Free-form material strings rot — mitigation: normalization layer + alias table.
- T7.4 Stale-since UI looking like a bug — mitigation: explicit "Spoolman last seen HH:MM (Xm ago)" copy + admin panel surface.
- T7.5 Spoolman entity deletion breaking portal-side references — only a risk if T2.7 (direct FK) is adopted; T2.6 (profile) sidesteps.
- T7.6 Anonymous info disclosure — mitigation: admin-only default + opt-in share posture.
- T7.7 Spoolman 0.24 breaking changes — mitigation: pinned upstream version + live smoke.
- T7.8 Outbound egress block at `.190` host firewall — mitigation: verify before MVP-A code lands.
- T7.9 Initiative scope creep — mitigation: this brainstorm's MVP-A/B/C/D/E split is explicit; PRD honors the split.
- T7.10 Forgetting to plan an auth-config slot — mitigation: env schema includes `SPOOLMAN_AUTH_TOKEN` slot even when unused.

#### Theme 8 — Open decisions (carried verbatim from Phase 6 — register for PRD handoff)

OD1–OD10 above.

### Breakthrough concepts

- **B1 — "Read-side surfacing carries 70–80% of the value."** First-principles insight from Phase 1. The integration's primary unlock isn't write-power; it's contextual placement. This single insight reshapes MVP scope from "Spoolman client library" to "landing dashboard card backed by Spoolman".
- **B2 — Profile-based linkage, not FK-based linkage.** T2.6 is the right shape because it isolates portal from Spoolman entity churn. Worth flagging in the architecture H2 append because it's a structural decision that future slices inherit.
- **B3 — Configs/app boundary stays clean if and only if any docker-network reshape is treated as a configs PR, not a portal PR.** T5.2 is the trip wire. The temptation to "just edit the compose because I'm in the codebase" must be resisted.
- **B4 — Plan the auth-config env slot even though Spoolman has no auth today.** Anti-pattern 9 + IC1 + OD8 + T7.10 converge on the same point: cost of the env slot is zero, future migration is free if we plan it now, painful if we don't.
- **B5 — The two specific low-stock spools at session start make this a demoable MVP.** The integration ships with real signal from day one; no need to seed test data. (Red hat + yellow hat insight.)

### Prioritization results

#### Top-priority pickups for the next BMAD step (`bmad-correct-course`)

1. **Adopt MVP-A as the initiative scope.** Baseline cell from Phase 2 / T6.1. Smallest meaningful slice; clean configs/app boundary; immediate operator value.
2. **Park MVP-C, MVP-D, MVP-E.** Note them in the PRD as Phase-2/3 candidates with clear precondition triggers (queue module live → revisit fulfillability; usage telemetry shows mutation demand → revisit MVP-D; share-token UX request → MVP-E).
3. **Confirm OD1, OD2, OD4, OD8 before PRD lands.** OD1 (slice scope), OD2 (auth posture on /spools), OD4 (transport), OD8 (Spoolman bind verification) are the load-bearing decisions; the rest can be PRD-stage refinements.
4. **Plan SPOOLMAN_URL + SPOOLMAN_AUTH_TOKEN env slots in API config.** Even with auth unused at session start, the env schema decision belongs in the initial PRD per B4.
5. **Recommended_material_profile design carveout for catalog SoT** — Phase-2 work but it should be mentioned in the initiative PRD so the catalog SoT design isn't surprised later.

#### Quick wins (within MVP-A)

- W1. New `apps/api/app/modules/spools/` package mirroring existing module layout (router + service + models + tests).
- W2. New `apps/web/src/modules/spools/` module — landing card + `/spools` route swap from `ComingSoonStub` to real implementation.
- W3. `httpx.AsyncClient`-based Spoolman client with timeout + circuit breaker, isolated in service layer per P4e.
- W4. Redis-cached aggregate query (`get_low_stock_spools(threshold_g: float)`) backing the landing card.
- W5. arq worker job polling Spoolman every 60 s and invalidating cache.
- W6. PL/EN i18n keys under `modules.spools.*` namespace.
- W7. Visual regression baselines for landing card + `/spools` index.
- W8. Structured log + tracing span per T4.7 + P13a.

#### Breakthrough concepts kept alive for later

- B1–B5 above. B1 informs PRD value framing; B2 is an architecture-doc note; B3 is an HC2 reinforcement; B4 is an env-schema requirement; B5 is the launch demo.

### Action planning

#### Idea 1: Adopt MVP-A as the initiative scope

**Why this matters:** Smallest slice that delivers operator-visible value (real low-stock cards on landing) while keeping HC1–HC5 intact and matching single-developer pace.

**Next steps for the BMAD chain:**

1. Operator (or autonomous agent on operator behalf) invokes `bmad-correct-course` with this brainstorm artifact as input context.
2. `bmad-correct-course` routes to `bmad-edit-prd` (initiative-level H2 append to `docs/prd.md` — *not* a new PRD).
3. PRD step confirms OD1, OD2, OD4, OD8 explicitly.
4. Architecture H2 append adds: `modules/spools/` shape, transport choice, cache shape, env-config additions, B2/B3/B4 notes.
5. Epic + story breakdown — likely 3–5 stories on a single epic.
6. Sprint planning slot the epic on top of the current sprint state.

**Resources needed:** No new infra; existing Redis + arq are sufficient. Configs-side coordination only if OD4 lands on P4b (docker network sharing) — small PR to `~/repos/configs/docker-compose-recipes/spoolman.yml` to expose Spoolman on a network reachable from portal-api.

**Timeline:** PRD + architecture edits: 1 BMAD session. Epic + stories: 1 BMAD session. Story execution: 3–5 stories @ ~1 session each. Roughly 1 week of BMAD-session-cadence work.

**Success indicators:**

- A fresh `git pull` + deploy + visit to landing shows two real low-stock spools (the 138.9 g PLA Speed Matt White and the 163.2 g PCTG Army Green at session start, or whatever the live state is).
- Spoolman-down test: stopping the Spoolman container leaves the landing card in soft-fail mode with a `stale since HH:MM` indicator, not a 500 error.
- Visual regression baselines exist for the landing card and `/spools` route in light + dark.
- `pytest` and `npm run test:visual` green per AGENTS.md gates.

#### Idea 2: Park MVP-C / MVP-D / MVP-E with explicit precondition triggers

**Why this matters:** Anti-scope-creep discipline (T7.9). PRD lists them with their trigger conditions, so the next operator-or-agent revisiting after MVP-A has a clear "is the trigger met?" check rather than rediscovering the slices from scratch.

**Next steps:** add a "Deferred-by-design follow-ups" section to the initiative PRD listing MVP-C/D/E with their triggers (queue-module-live / mutation-demand-evidence / share-token-request).

**Success indicators:** subsequent brainstorm / PRD discussions on those slices cite this artifact and the deferred-by-design section, not "blue sky".

## Session Summary and Insights

### Key achievements

- 118 distinct ideas generated across 6 techniques.
- Morphological grid covering 15 parameters × 60+ option cells gives the PRD step a full option space rather than a single "first idea wins" baseline.
- Baseline MVP cell + alternative cell selected, stress-tested, and reduced to a recommended initiative scope (MVP-A).
- Open-decisions register (OD1–OD10) written for direct PRD handoff.
- 5 breakthrough concepts (B1–B5) flagged for architecture-doc inheritance.
- Risk register (T7.1–T7.10) ready for PRD risk section.

### Creative breakthroughs and insights

- **Insight 1 (B1):** Read-side surfacing is the value, not mutation power. Reshapes MVP scope.
- **Insight 2 (B2):** Profile-based linkage isolates the portal from Spoolman entity churn. Structural decision for any catalog ↔ filament work.
- **Insight 3 (B3):** Configs/app boundary stays clean only if docker-network reshapes are configs-side PRs. Trip-wire for HC2.
- **Insight 4 (B4):** Plan the auth env slot even when unused — zero cost now, expensive later.
- **Insight 5 (B5):** Two specific low-stock spools at session start make MVP demoable on day one — the launch has real signal.

### Session reflections

- **Autonomous facilitation worked cleanly** for a structural-enumeration topic. Where the 2026-05-25 share-flow brainstorm required operator pruning on the recipient/intent axes, this one converges on a single high-confidence baseline cell because the option space is wider but the goal (one MVP initiative + open-decisions register) is well-defined.
- **The configs/app boundary (HC2) is the most under-acknowledged constraint in the space.** It's easy to "just edit the compose" while in the portal repo and that's exactly what AGENTS.md § Scope boundaries warns against. Multiple ideas explicitly cited and reinforced this boundary.
- **The integration deliberately stops short of any feature that would lock in coupling to unbuilt modules** (queue, printer, requests). Each downstream coupling point is parked with an explicit trigger condition. This is the right shape for an MVP — the alternative ("design everything for the future") would inflate scope and delay any operator-visible value.
- **No code changes were made**, per HC1. Exactly one artifact was produced: this file.

### Recommended next BMAD step

**`bmad-correct-course`** — invoked with this artifact as input context. Brownfield routing (per AGENTS.md § Workflow expectations) and post-MVP scope change semantically — even though Spoolman integration is a fresh feature, the codebase is mid-stream brownfield, so vanilla `bmad-create-prd` is the wrong entry. `bmad-correct-course` will route to the right ceremony (`bmad-edit-prd` initiative-level H2 append + architecture/epics edits per its recommendation).

The PRD step explicitly inherits:

- MVP scope = MVP-A from this artifact.
- Open decisions OD1–OD10 (especially OD1, OD2, OD4, OD8 as load-bearing).
- Risk register T7.1–T7.10.
- Breakthrough concepts B1–B5 to flag in PRD value framing + architecture H2.
- Deferred-by-design list (MVP-C/D/E) with trigger conditions.

### Closure

This brainstorm artifact is complete. No code was written. No PRD was written. No initiative was created. The next agent or operator session is expected to invoke `bmad-correct-course` (per the recommendation above) with this file as input context to begin the PRD edit + architecture H2 append cycle.
