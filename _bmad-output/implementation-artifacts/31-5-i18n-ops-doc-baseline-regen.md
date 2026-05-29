# Story 31.5: i18n parity sweep + ops doc addendum + baseline regen

Status: review

## Story

As the **portal operator** who needs to operate, troubleshoot, and translate the Initiative 19 surface in production,
I want **a one-pass close-out story that locks the Initiative 19 i18n parity invariant (every `modules.spools.*` and `landing.*` key present in BOTH `en.json` and `pl.json`), an `operations.md` addendum documenting the SPOOLMAN_* env slots + soft-fail behavior + OD8 LAN-only-bind verification recipe + GlitchTip breadcrumb category troubleshooting pointer, and a sweep of existing visual baselines for any drift caused by Stories 31.3 + 31.4's surface additions**,
so that **Initiative 19 closes with no documentation debt, the operator has one canonical doc to consult on outage triage, and any baseline drift introduced by the landing-page swap or the new `/spools` route is caught before it festers into a silent test-fail**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.3 (Story 31.5 row).
Realizes **NFR19-I18N-PARITY-1** (final sweep) + **NFR19-VISUAL-VERIFICATION-1** (closing pass).
**Codex tag:** `gpt-5.4-mini` — pure docs + verification work; no NFR-SECURITY adjacency.

## Pre-enumeration save

1. **Files reused (already shipped):**
   - `docs/operations.md` — appended new H2 section.
   - `apps/web/src/locales/en.json` + `pl.json` — read-only audit.
   - `apps/api/app/core/config.py` — referenced (`spoolman_url` + `spoolman_auth_token` already shipped in Story 31.1; no new env slot).
   - `apps/web/src/modules/spools/components/LowStockCard.lib.ts` — `LOW_STOCK_THRESHOLD_G` constant referenced in the operations doc as the upgrade-to-env trigger point.
   - `infra/env.example` — already documents `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` (Story 31.1).
2. **New files:** none — Story 31.5 is purely additive to existing docs + verification.
3. **Modified files:**
   - `docs/operations.md` — append `## Spoolman read-only inventory (Initiative 19)` H2.
4. **Test fixtures reused:** none — no new tests.
5. **Contracts already enforced (mechanisms named):**
   - **i18n parity** — verified by counting `modules.spools.` + `landing.` key occurrences in `en.json` vs `pl.json`. Mechanism: bash grep.
   - **Visual baselines stability** — verified by full `npm run test:visual` run. Mechanism: Playwright snapshot diff.
   - **OD8 LAN-only bind** — verified in Story 31.1 + AC-11 already; this story documents the verification *recipe* for future operator reuse, NOT a re-execution.
6. **Defensive policies not reversed:** none.

## Acceptance Criteria

### AC-1 — i18n parity audit on every Init 19 namespace

Run from `apps/web/src/locales/`:

```bash
grep -c '"modules.spools' en.json pl.json
grep -c '"landing\.' en.json pl.json
```

Both pairs MUST return equal counts. The Init 19 namespace surface (post-Stories 31.3 + 31.4):

- `modules.spools.index.title`
- `modules.spools.index.loading`
- `modules.spools.index.last_updated`
- `modules.spools.index.last_updated_with_ago`
- `modules.spools.index.archived_badge`
- `modules.spools.states.empty`
- `modules.spools.states.unavailable`
- `modules.spools.states.error`
- `modules.spools.lowstock.title`
- `modules.spools.lowstock.loading`
- `modules.spools.lowstock.error`
- `modules.spools.lowstock.all_ok`
- `modules.spools.lowstock.unavailable`
- `modules.spools.lowstock.more_count`
- `landing.title`
- `landing.subtitle`
- `landing.tile.catalog.label`
- `landing.tile.catalog.description`
- `landing.tile.spools.label`
- `landing.tile.spools.description`

Total: **20 keys × 2 locales = 40 entries** (8 from Story 31.3 + 6 from Story 31.4 lowstock + 6 from Story 31.4 landing). Plus the pre-existing top-level `modules.spools` key (the side-nav label, "Filamenty" in PL) which existed before Init 19 and is NOT changed.

The audit also confirms NO orphan `{{count}}` interpolation variables in the Init 19 namespace (Story 31.3 review round-1 lesson — `count` is reserved by i18next for plural-suffix resolution; all interpolation variables are non-reserved names: `time`, `ago`, `n`).

### AC-2 — `docs/operations.md` addendum

Append a new H2 section `## Spoolman read-only inventory (Initiative 19)` after the existing `## Post-cutover portal-self-auth posture — Initiative 6 default-deny (2026-05-21)` block. The addendum has the following subsections:

#### `### Environment variables`

| Slot | Default | Purpose | Owner |
|---|---|---|---|
| `SPOOLMAN_URL` | `http://spoolman:8000` (Decision AE P4b) — fallback `http://localhost:7912` (P4a) | Base URL the portal API uses for Spoolman's `/api/v1/*` endpoints. | `apps/api/app/core/config.py` (Story 31.1). |
| `SPOOLMAN_AUTH_TOKEN` | empty | Reserved future Spoolman auth (Phase C trigger). Empty value disables the `Authorization` header. | Same. |
| `SPOOLMAN_LOW_STOCK_THRESHOLD_G` | NOT IMPLEMENTED — current threshold is the hardcoded `LOW_STOCK_THRESHOLD_G = 200` constant at `apps/web/src/modules/spools/components/LowStockCard.lib.ts`. | The "low stock" cutoff (grams) below which a spool surfaces on the landing `LowStockCard`. | FE component-level constant; promote to runtime env when operator wants to tune without redeploy. |

#### `### Soft-fail behavior`

When Spoolman is unreachable, the portal degrades gracefully (FR19-FAILURE-1) — NEVER 5xx:

- **`GET /api/spools/summary`** returns HTTP 200 with empty arrays + `last_success_ts: null` when both the cache is empty and the live fetch fails (cold-cache + outage). When the cache is warm but Spoolman is currently down, the prior snapshot is served with the original (stale) `last_success_ts`; the FE indicator computes "Xm temu" from the delay.
- **`/spools` route** renders the explicit `EmptyState` "Spoolman jest nieosiągalny" with no Retry (the arq cron repopulates the cache when Spoolman returns).
- **Landing `LowStockCard`** renders the same soft-fail empty state inside the card.

Cache topology (Story 31.1, byte-pinned — change requires SCP):

- Read key: `spools:summary:v1` (JSON-encoded `SpoolmanSnapshot`, 30s TTL).
- Sibling: `spools:summary:last-success-ts` (no TTL — survives cache rotation).
- Poll lock: `spools:poll-lock` (SETNX, 90s TTL, single-poller leader-election).

arq poll cadence: 60s (FR19-CACHE-1 freshness budget).

#### `### OD8 LAN-only bind verification recipe`

Spoolman is configured for LAN-only exposure (operator decision 2026-05-29: NOT `0.0.0.0`, NOT `::`; specifically bound to the host's LAN interface `192.168.2.190:7912`). To verify the bind on `.190`:

```bash
docker inspect spoolman --format '{{json .NetworkSettings.Ports}}' | jq
# Expect: "8000/tcp": [ { "HostIp": "192.168.2.190", "HostPort": "7912" } ]
# REJECT:  HostIp: "0.0.0.0" or HostIp: "::"  (Docker default all-interfaces exposure).
```

If the bind drifts to `0.0.0.0` / `::`, STOP and escalate:

1. The Spoolman compose file lives at `~/repos/configs/docker-compose-recipes/spoolman.yml`.
2. The expected `ports` block: `- "192.168.2.190:7912:8000"`.
3. Fix on the configs side, re-deploy via `~/repos/configs/sync.sh`, re-run the inspect above.

The bind invariant exists because the operator + phone consume Spoolman directly on the LAN (printer pushes filament-usage updates live); a strict `127.0.0.1`-only bind would break that workflow.

#### `### GlitchTip breadcrumb category troubleshooting`

All Spoolman client calls emit a Sentry breadcrumb at category `spoolman.client` (Story 31.1 AC-6). When triaging a low-stock card error or a `/spools` 200-with-empty-arrays response in GlitchTip, filter the event's breadcrumb timeline by:

```
category:spoolman.client
```

Breadcrumbs surface: endpoint (`GET /api/v1/spool` / `/filament` / `/vendor`), `duration_ms`, `status_code`, and the failure level (`info` on success, `warning` on `httpx.RequestError` / `httpx.HTTPStatusError` / circuit-breaker open). Structured-log records carry the matching `event.action` (`spools.client.call` / `spools.client.error` / `spools.poll.refresh` / `spools.poll.error`) + `labels.external_service=spoolman` for grep filtering in the JSON log stream.

If GlitchTip shows ZERO `spoolman.client` breadcrumbs during an outage triage, the issue is upstream (network / DNS / Docker network split), not the portal client — the breadcrumbs emit unconditionally on every call attempt (including the circuit-open short-circuit, which logs `error_class=SpoolmanCircuitOpenError`).

#### `### Cross-references`

- Story 31.1 — backend client + cache + poll. Spec: `_bmad-output/implementation-artifacts/31-1-backend-spoolman-client-cache-poll.md`.
- Story 31.2 — `/api/spools/*` routes + DTOs. Spec: `_bmad-output/implementation-artifacts/31-2-backend-spools-routes-dto-cost-carry.md`.
- Story 31.3 — `/spools` index page. Spec: `_bmad-output/implementation-artifacts/31-3-frontend-spools-route-index-page.md`.
- Story 31.4 — landing dashboard + LowStockCard. Spec: `_bmad-output/implementation-artifacts/31-4-frontend-landing-low-stock-card.md`.
- Architecture decisions: `_bmad-output/planning-artifacts/architecture.md` § Initiative 19 (Decisions AD + AE + AF).
- Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md`.

### AC-3 — Visual baseline drift sweep

Run `npm run test:visual` against `origin/main` (post-Story-31.4 merge) and confirm all baselines pass. The expected count is 364 passed / 24 skipped (the post-31.4 state). Any unexpected diff is either:

1. A genuine drift introduced by Story 31.4's landing-page mount affecting an `accessibility-axe.spec.ts` or `v2-placeholders.spec.ts`-style spec — regen the affected baseline + record the regen here with a `baseline-reviewed: <reason>` justification.
2. A flaky environmental diff (font rendering, animation) — STOP, do not regen blindly; investigate per `[[feedback_visual_failure_mode_triage]]` discipline.

Story 31.5 expects ZERO baselines to need regen — the Story 31.4 dev-story already verified the full suite green (364 passed / 24 skipped, baseline 356 + 8 new landing baselines, zero existing-baseline regressions). This AC just runs the suite one more time on a clean post-merge state to lock the property.

### AC-4 — Triage script update

`_bmad-output/triage-backlog.md` MUST NOT contain any new Init 19 entry — Stories 31.1-31.5 are explicitly the scope, and any leftover NFR or deferred Phase B/C/D/E concerns are documented as "out of scope" in the SCP + retros, NOT as triage backlog items. Story 31.5 reads the triage backlog and confirms zero Init 19 entries; if any are found, raises them to the operator as a blocker.

### AC-5 — Grep invariants

- `git diff main -- apps/api/` shows zero diff (Story 31.5 is docs + verification only).
- `git diff main -- apps/web/src/` shows zero diff (no FE code change).
- `git diff main -- apps/web/tests/visual/` shows zero diff (no spec or baseline change unless AC-3 surfaces a genuine drift — none expected).
- `git diff main -- _bmad-output/` shows additions only (this story file + the sprint-status close-out).

### AC-6 — Sprint-status close-out for the epic

After Story 31.5 lands:

- `epic-31` flips `in-progress → done` (or its analog) in `sprint-status.yaml`.
- `epic-31-retrospective` row stays `pending` — the bmad-retrospective skill is called as a separate session step.

## Tasks / Subtasks

- [ ] **T1** (AC-1) — Run the i18n parity grep; confirm equal counts on both `modules.spools.*` and `landing.*` namespaces.
- [ ] **T2** (AC-2) — Append the `## Spoolman read-only inventory (Initiative 19)` H2 to `docs/operations.md`.
- [ ] **T3** (AC-3) — Run `npm run test:visual`; confirm 364 passed / 24 skipped state.
- [ ] **T4** (AC-4) — Read `_bmad-output/triage-backlog.md`; confirm zero Init 19 entries.
- [ ] **T5** (AC-5) — Confirm grep invariants.
- [ ] **T6** (AC-6) — Flip `epic-31` to done in `sprint-status.yaml`.
- [ ] **T7** (close-out) — Commit subject `docs(ops): Spoolman operations addendum + Init 19 i18n parity close-out (Story 31.5, Init 19)`; ff-merge; push.

## Dev Agent Record

### Code-side gates (filled by dev-story execution)

- i18n parity audit: PASS.
  - `modules.spools.*`: en.json 14 / pl.json 14 (equal).
  - `landing.*`: en.json 6 / pl.json 6 (equal).
  - Top-level `modules.spools`: en.json 1 / pl.json 1 (equal; pre-existing side-nav label).
  - Reserved-interpolation grep (`{{count}}` inside the Init 19 namespace): 0 / 0 hits — Story 31.3 review round-1 lesson (renaming `count` → `ago`) confirmed clean across the whole sweep.
- `npm run test:visual` full: 364 passed / 24 skipped — exactly matches the post-31.4 state. Zero baseline drift. AC-3 zero-regen expectation confirmed.
- Grep invariants:
  - `git diff main -- apps/api/` zero diff.
  - `git diff main -- apps/web/src/` zero diff (no FE code change).
  - `git diff main -- apps/web/tests/visual/` zero diff (no spec or baseline change).
  - `git diff main -- docs/operations.md` adds the new `## Spoolman read-only inventory (Initiative 19)` H2 with 5 subsections (Environment variables, Soft-fail behavior, OD8 LAN-only bind verification recipe, GlitchTip breadcrumb category troubleshooting, Cross-references).
  - `git diff main -- _bmad-output/implementation-artifacts/` adds the story file and updates sprint-status.
- Triage backlog scan: zero open Init 19 entries; only historic readiness mentions (TB-050 + TB-051, both `done` 2026-05-29 as Init 19 readiness process-aid work). AC-4 PASS.

### Review Findings (filled by code-review execution)

_pending_

## Out of scope

- Promoting the `LOW_STOCK_THRESHOLD_G` constant to a runtime env slot — explicitly deferred to a future follow-up (operator may request runtime tuning later). Story 31.5 documents the upgrade path; the wire-up is not done here.
- Epic 31 retrospective itself — that runs as a separate `bmad-retrospective` invocation after this story closes.
- Any cross-initiative cleanup that surfaces during this story — out of scope; raise to the operator as a separate triage item.
