# Story 31.5: i18n parity sweep + ops doc addendum + baseline regen

Status: review (Codex fix-up 2026-05-29 applied — pending re-review)

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
2. **New files:** this story spec — `_bmad-output/implementation-artifacts/31-5-i18n-ops-doc-baseline-regen.md` (the artifact you are reading). All other Story 31.5 work is additive to existing docs + verification, no code or test files added.
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

Equal-count `grep -c` is the cheap first signal but is NOT load-bearing on its own — equal counts can mask a divergent key-set (one locale has key A, the other has differently-named key B; both contribute one match). The load-bearing audit is a **key-set + interpolation-surface comparison** run against the two locale JSON files (each is a flat dictionary, no nesting):

```bash
# Equal-count first pass (fast):
cd apps/web/src/locales/
grep -c '"modules.spools' en.json pl.json
grep -c '"landing\.' en.json pl.json
# Equal-count is necessary but not sufficient.

# Load-bearing pass — compare the actual key sets and interpolation
# variable sets in each value (run from repo root):
python3 - <<'EOF'
import json, re
INTERP_RX = re.compile(r"\{\{\s*(\w+)\s*\}\}")
PREFIXES = ("modules.spools.", "landing.")
en = json.load(open("apps/web/src/locales/en.json"))
pl = json.load(open("apps/web/src/locales/pl.json"))
def slice_(d): return {k: v for k, v in d.items() if any(k.startswith(p) for p in PREFIXES)}
en_ns, pl_ns = slice_(en), slice_(pl)
assert set(en_ns) == set(pl_ns), \
    f"key drift en-only={set(en_ns)-set(pl_ns)} pl-only={set(pl_ns)-set(en_ns)}"
for k in sorted(set(en_ns) & set(pl_ns)):
    en_v = sorted(set(INTERP_RX.findall(en_ns[k])))
    pl_v = sorted(set(INTERP_RX.findall(pl_ns[k])))
    assert en_v == pl_v, f"interpolation drift on {k}: en={en_v} pl={pl_v}"
print(f"PASS: {len(en_ns)} keys, identical sets, zero interpolation drift.")
EOF
```

Both audits MUST pass. The Init 19 namespace surface (post-Stories 31.3 + 31.4):

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
| `SPOOLMAN_URL` | `http://spoolman:8000` (Decision AE P4b — portal-api on the shared docker network resolves the `spoolman` hostname) — fallback `http://192.168.2.190:7912` (P4a — operator override hitting the LAN-bind direct IP when the configs-side network attachment slips) | Base URL the portal API uses for Spoolman's `/api/v1/*` endpoints. | `apps/api/app/core/config.py` (Story 31.1). |
| `SPOOLMAN_AUTH_TOKEN` | empty | Reserved future Spoolman auth (Phase C trigger). Empty value disables the `Authorization` header. | Same. |
| `SPOOLMAN_LOW_STOCK_THRESHOLD_G` *(reserved slot name, NOT a real env var in MVP-A)* | NOT IMPLEMENTED — current threshold is the hardcoded `LOW_STOCK_THRESHOLD_G = 200` constant at `apps/web/src/modules/spools/components/LowStockCard.lib.ts`. | The "low stock" cutoff (grams) below which a spool surfaces on the landing `LowStockCard`. | FE component-level constant; the consumer is the **frontend bundle**, so promotion is a Vite-build-time read (`VITE_SPOOLMAN_LOW_STOCK_THRESHOLD_G`), NOT a runtime api-container env. Single-file upgrade path: replace the constant with `Number(import.meta.env.VITE_SPOOLMAN_LOW_STOCK_THRESHOLD_G ?? 200)` + add to the `.env` consumed by `apps/web/Dockerfile`'s build stage. Re-deploy required. |

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

- [x] **T1** (AC-1) — Run the i18n parity grep AND the load-bearing Python key-set + interpolation comparison; confirm equal counts AND identical key sets AND zero interpolation-surface drift on both `modules.spools.*` and `landing.*` namespaces.
- [x] **T2** (AC-2) — Append the `## Spoolman read-only inventory (Initiative 19)` H2 to `docs/operations.md`.
- [x] **T3** (AC-3) — Run `npm run test:visual`; confirm 364 passed / 24 skipped state.
- [x] **T4** (AC-4) — Read `_bmad-output/triage-backlog.md`; confirm zero Init 19 entries.
- [x] **T5** (AC-5) — Confirm grep invariants.
- [x] **T6** (AC-6) — Flip `epic-31` to done in `sprint-status.yaml`.
- [x] **T7** (close-out) — Commit subject `docs(ops): Spoolman operations addendum + Init 19 i18n parity close-out (Story 31.5, Init 19)`; ff-merge deferred (epic retrospective gate); push deferred until retrospective runs.

## Dev Agent Record

### Code-side gates (filled by dev-story execution)

- i18n parity audit: PASS — both equal-count signal AND load-bearing key-set + interpolation-surface comparison.
  - Equal-count signal: `modules.spools.*` en.json 14 / pl.json 14; `landing.*` en.json 6 / pl.json 6; top-level `modules.spools` en.json 1 / pl.json 1 (pre-existing side-nav label, unchanged).
  - Load-bearing key-set comparison (Python/JSON, run 2026-05-29 against this branch): en Init 19 key count = 20, pl Init 19 key count = 20, `set(en) == set(pl)` = True, en-only keys = [], pl-only keys = [].
  - Load-bearing interpolation-surface comparison: zero mismatches across the 20 shared keys. Per-key surface for the record — `landing.*` keys: no interpolation; `modules.spools.index.last_updated`: `{time}`; `modules.spools.index.last_updated_with_ago`: `{ago, time}`; `modules.spools.lowstock.more_count`: `{n}`; all remaining 16 keys: no interpolation.
  - Reserved-name guard (`{{count}}` inside the Init 19 namespace): 0 hits in either locale — Story 31.3 review round-1 lesson (renaming `count` → `ago` for `last_updated_with_ago` and using `n` for `more_count`) confirmed clean across the whole sweep. (The pre-existing `auth.2fa.status.enabled.codes_remaining` and other reserved-`count` uses outside the Init 19 namespace are intentional plural-suffix consumers and are NOT in scope.)
- `npm run test:visual` full: 364 passed / 24 skipped — exactly matches the post-31.4 state. Zero baseline drift. AC-3 zero-regen expectation confirmed.
- Grep invariants:
  - `git diff main -- apps/api/` zero diff.
  - `git diff main -- apps/web/src/` zero diff (no FE code change).
  - `git diff main -- apps/web/tests/visual/` zero diff (no spec or baseline change).
  - `git diff main -- docs/operations.md` adds the new `## Spoolman read-only inventory (Initiative 19)` H2 with 5 subsections (Environment variables, Soft-fail behavior, OD8 LAN-only bind verification recipe, GlitchTip breadcrumb category troubleshooting, Cross-references).
  - `git diff main -- _bmad-output/implementation-artifacts/` adds the story file and updates sprint-status.
- Triage backlog scan: zero open Init 19 entries; only historic readiness mentions (TB-050 + TB-051, both `done` 2026-05-29 as Init 19 readiness process-aid work). AC-4 PASS.

### Review Findings (filled by code-review execution)

#### Codex review (2026-05-29, native) — verdict NOT merge-ready, fix-up applied on this branch

Codex reviewed the Story 31.5 diff at commit `3a5707b` and returned **NOT merge-ready** with five Important findings + one Minor consistency issue. All findings were docs/artifact-only — no code or frontend changes were requested or made. Fix-up commit applied on the same branch (`feat/E31.5-i18n-ops-doc-baseline-regen`); listed verbatim below with the resolution against this branch.

**Important findings**

1. **`docs/operations.md` mis-attributes the auth-bearing routes** as `/api/spools/summary` / `/spools` / `/filaments`. The actual Story 31.2 prefix is `/api/spools`, so the second and third routes are `/api/spools/spools` and `/api/spools/filaments` (the bare `/spools` and `/filaments` form is misleading — it looks like a top-level FE route or a bare path, not the prefixed API path). **Resolution:** rewrote the intro paragraph of `## Spoolman read-only inventory (Initiative 19)` in `docs/operations.md` to spell out the three routes in full (`GET /api/spools/summary`, `GET /api/spools/spools`, `GET /api/spools/filaments`) and explicitly cite the `/api/spools` prefix from Story 31.2. Verified against `apps/api/app/modules/spools/router.py`: `APIRouter(prefix="/api/spools")` + three `@router.get` decorators at `"/summary"`, `"/spools"`, `"/filaments"`.

2. **`SPOOLMAN_LOW_STOCK_THRESHOLD_G` upgrade guidance is operationally imprecise** — the slot name uses the backend-style `SPOOLMAN_*` prefix (implying a runtime env consumed by the api container) but the upgrade path reads `import.meta.env.VITE_*` which is Vite **build-time** unless a runtime-injection layer is added. The NOT IMPLEMENTED status is correct; the upgrade-path narrative was misleading about where the env lives and what redeploy is required. **Resolution:** annotated the slot as *"reserved slot name, NOT a real env var in MVP-A"* and rewrote the Owner-column upgrade-path text in BOTH the ops doc and the story spec to call out: (a) the consumer is the frontend bundle, (b) promotion is a Vite-build-time read using the `VITE_SPOOLMAN_LOW_STOCK_THRESHOLD_G` form, (c) the env must be added to the `.env` consumed by `apps/web/Dockerfile`'s build stage (both `.190:/mnt/raid/docker-compose/3d-portal/.env` and `~/repos/3d-portal/infra/.env`), (d) re-deploy is required because Vite bakes the constant into the bundle, (e) runtime tuning would require a separate `/api/spools/config` runtime-injection endpoint which is explicitly out of scope for MVP-A.

3. **GlitchTip "ZERO `spoolman.client` breadcrumbs ⇒ upstream issue" paragraph overclaims** — absence of breadcrumbs has multiple equally-likely causes (cache-only response, no actual client call, Sentry SDK disabled / DSN missing, auth-gated 401 short-circuit before the service-layer call, request routed to a different service entirely) before "upstream" is even a candidate. **Resolution:** rewrote the GlitchTip subsection in `docs/operations.md` to walk through the five likely causes in order (no-call / SDK-disabled / 401-short-circuit / different-service / upstream) and frame "ZERO breadcrumbs ⇒ upstream" as the LAST candidate after the others are ruled out. Also added the inverse signal (presence of `level=warning` `spoolman.client` breadcrumb with `endpoint` + `status_code` + `error_class` IS a strong portal-client signal) for symmetric triage value.

4. **`grep -c` parity is necessary but not sufficient for AC-1** — equal counts on two namespaces can co-exist with divergent key sets (locale A has key X, locale B has differently-named key Y; both contribute one match). The close-out invariant should compare actual key SETS and interpolation-variable SETS, not just counts. **Resolution:** rewrote AC-1 in the story spec to add a load-bearing Python/JSON comparison pass (key-set equality assert + per-key interpolation-variable set equality assert) on top of the cheap equal-count signal; embedded the runnable Python snippet so it can be re-executed on demand. Ran the comparison against this branch's `en.json` and `pl.json`: en Init 19 key count = 20, pl Init 19 key count = 20, `set(en) == set(pl)` = True, en-only keys = [], pl-only keys = [], zero interpolation-surface mismatches across the 20 shared keys. Per-key interpolation surface (for the record): `landing.*` keys: no interpolation; `modules.spools.index.last_updated`: `{time}`; `modules.spools.index.last_updated_with_ago`: `{ago, time}`; `modules.spools.lowstock.more_count`: `{n}`; remaining 16 keys: no interpolation. Reserved-`count` hits in the Init 19 namespace: 0.

5. **Story artifact inconsistency** — the "New files" pre-enumeration save said "none" while the story spec file itself is added on this branch; T1-T7 task checkboxes remained unchecked despite the Dev Agent Record claiming the work done. **Resolution:** updated the "New files" entry to list this story spec file as the one added artifact (all other work is additive to existing docs); flipped T1-T7 from `[ ]` to `[x]` to reflect the executed-and-recorded state; T7 footnote clarifies ff-merge + push are deferred until the epic-31 retrospective runs (per operator constraint at fix-up time).

**Minor findings**

6. **Story AC-2 `SPOOLMAN_URL` fallback value (`http://localhost:7912`) disagrees with the ops doc value (`http://192.168.2.190:7912`)** — these are two different URLs and should be a single source of truth. **Resolution:** rewrote AC-2's table cell to use `http://192.168.2.190:7912` (matching the ops doc) and added the rationale parenthetical — the LAN-bind direct IP is the correct operator override because Spoolman is bound to `192.168.2.190:7912` (not `127.0.0.1`/`0.0.0.0`) per the OD8 LAN-only invariant; `localhost:7912` would not resolve to the bound Spoolman service. (The stale `localhost:7912` reference in the `apps/api/app/core/config.py` docstring is code-side and out of scope for this docs-only fix-up; flagged here for a follow-up sweep if Codex re-review surfaces it.)

**Items NOT changed**

- **LAN-bind guidance** — Codex confirmed the OD8 LAN-only verification recipe is good as-is. No edit.
- **No code or frontend changes** — fix-up is restricted to `docs/operations.md` and this story spec, per operator constraint.

**Verification commands re-run for the fix-up**

```bash
# AC-1 load-bearing parity check (also re-recorded above):
python3 - <<'EOF'
import json, re
INTERP_RX = re.compile(r"\{\{\s*(\w+)\s*\}\}")
PREFIXES = ("modules.spools.", "landing.")
en = json.load(open("apps/web/src/locales/en.json"))
pl = json.load(open("apps/web/src/locales/pl.json"))
def slice_(d): return {k: v for k, v in d.items() if any(k.startswith(p) for p in PREFIXES)}
en_ns, pl_ns = slice_(en), slice_(pl)
print(f"en={len(en_ns)} pl={len(pl_ns)} equal-set={set(en_ns)==set(pl_ns)}")
for k in sorted(set(en_ns) & set(pl_ns)):
    en_v = sorted(set(INTERP_RX.findall(en_ns[k])))
    pl_v = sorted(set(INTERP_RX.findall(pl_ns[k])))
    if en_v != pl_v: print(f"DRIFT {k}: en={en_v} pl={pl_v}")
EOF
# → en=20 pl=20 equal-set=True; no DRIFT lines printed.

# Route-prefix verification (also re-recorded above):
grep -nE '@router\.(get|post)|prefix=' apps/api/app/modules/spools/router.py
# → prefix="/api/spools" + three @router.get decorators at "/summary", "/spools", "/filaments".
```

Fix-up commit subject: `docs(bmad): apply Codex Story 31.5 review fix-up (routes, threshold guidance, breadcrumb triage, parity invariant) (Story 31.5, Init 19)`.

## Out of scope

- Promoting the `LOW_STOCK_THRESHOLD_G` constant to a runtime env slot — explicitly deferred to a future follow-up (operator may request runtime tuning later). Story 31.5 documents the upgrade path; the wire-up is not done here.
- Epic 31 retrospective itself — that runs as a separate `bmad-retrospective` invocation after this story closes.
- Any cross-initiative cleanup that surfaces during this story — out of scope; raise to the operator as a separate triage item.
