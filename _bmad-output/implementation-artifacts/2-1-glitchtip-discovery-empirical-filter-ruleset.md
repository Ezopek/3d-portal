# Story 2.1: 30-Day GlitchTip Issue Discovery + Empirical Filter Ruleset

Status: done

## Story

As the SDK-config author drafting `apps/web/src/instrument.ts` filter logic for Story 2.4,
I want a documented sample of the last 30 days of GlitchTip issues from the homelab instance (frequency-ranked) and a derived filter ruleset (`denyUrls` regex patterns + `ignoreErrors` title patterns),
So that the in-code filter is empirically grounded — anticipated patterns (browser-extension URLs, `ResizeObserver loop limit exceeded`) are a floor, not a ceiling, per FR6 + architecture Decision H + AR11.

This is a **research/discovery story**, not a code-shipping story. It produces a single markdown artifact in the gitignored `_bmad-output/implementation-artifacts/` tree. No production code changes, no deploy. Output gates AR6 / FR6 / Story 2.4 implementation.

## Acceptance Criteria

1. **AC1 — Source data fetch.** A shell session against the homelab GlitchTip instance queries
   `GET ${GLITCHTIP_URL:-http://192.168.2.190:8800}/api/0/projects/${GLITCHTIP_ORG_SLUG}/${GLITCHTIP_PROJECT_SLUG}/issues/?statsPeriod=30d&limit=100&sort=lastSeen`
   with `Authorization: Bearer $GLITCHTIP_AUTH_TOKEN`. Token is sourced from `infra/.env` via `set -a; source infra/.env; set +a` exactly once. The HTTP response status is 200; on non-200 the dev stops and reports (no silent retry, no token regeneration without operator).

2. **AC2 — Output file location + naming.** The discovery report is written to
   `_bmad-output/implementation-artifacts/glitchtip-discovery-<YYYY-MM-DD>.md`
   where `<YYYY-MM-DD>` is the UTC date the discovery is actually run (`date -u +%Y-%m-%d`), NOT the date this story file was authored. If shipped 2026-05-10, the file is `glitchtip-discovery-2026-05-10.md`. The `_bmad-output/` tree is gitignored — the file stays local to the dev box; no commit, no push.

3. **AC3 — Document contents (mandatory sections, in order).**
   - **Header:** ISO-8601 timestamp of the run, GlitchTip endpoint used, org+project slugs, total issue count returned for the 30-day window.
   - **Frequency-ranked table (top 25 issues by event `count`, descending).** Columns: `rank`, `count`, `title` (markdown-escaped), `culprit` (or `—` if absent), `sample request.url` (or `—` if absent), `last_seen` (ISO-8601). If the result set has fewer than 25 issues, list all of them.
   - **Derived `denyUrls` array.** TypeScript-paste-ready regex literals separated by commas, one per line, each followed by a one-line `// ` justification with frequency count. Anticipated minimums (mandatory, even if zero matches in the sample): `/^chrome-extension:\/\//`, `/^moz-extension:\/\//`, `/^safari-web-extension:\/\//` — labeled `// floor: anticipated minimum (FR5)`. Empirical additions appended below the floor section, each with `// empirical: <count> events` justification.
   - **Derived `ignoreErrors` array.** Same paste-ready format. Anticipated minimums (mandatory): `/ResizeObserver loop/`, `/Non-Error promise rejection captured/` — labeled `// floor: anticipated minimum (FR6)`. Empirical additions appended with `// empirical: <count> events` justification.
   - **Methodology section.** One short paragraph describing how empirical patterns were derived (regex authored to match the noisy title family, not just the exact string; case-sensitivity rationale; why a pattern was chosen over a literal match).
   - **Sample queries appendix.** The exact `curl` invocation(s) used, with the token replaced by `$GLITCHTIP_AUTH_TOKEN` so the file is safe to read without leaking credentials.

4. **AC4 — Story 2.4 paste-readiness.** The two derived arrays are syntactically valid TypeScript when copy-pasted between `const denyUrls: RegExp[] = [` and `];`. Verification step: run `node -e "const a=[<paste>]; console.log(a.length, a.every(r=>r instanceof RegExp))"` against each array (or equivalent quick check) and record the pass in the dev log. Story 2.4 imports the ruleset literally — no manual translation, no reshuffling, no re-ordering.

5. **AC5 — Floor patterns are mandatory.** The 3 browser-extension URL regexes (FR5) and the 2 noise-title regexes (FR6) MUST appear in the output even if zero matching events were observed in the 30-day window. They are the architectural floor; the empirical sample only EXTENDS the floor.

6. **AC6 — Read-only against GlitchTip (FR20 / NFR-S2).** The discovery uses only `GET` requests against `/api/0/...`. No `POST`, no `PUT`, no `DELETE`. No issue is mutated (no `status` change, no resolve/mute, no delete) as a side effect of the discovery. If the dev needs to drill into a single issue for `request.url` extraction, it goes via `GET /api/0/issues/<id>/events/latest/` — also read-only.

7. **AC7 — Token hygiene (NFR-S1).** `GLITCHTIP_AUTH_TOKEN` is never `echo`'d, `cat`'d, logged, or written into the discovery markdown. The exact `curl` examples in the appendix use `$GLITCHTIP_AUTH_TOKEN` placeholder, never the resolved value. The dev workflow runs from `infra/.env`-loaded environment only.

8. **AC8 — No code, no deploy, no commit.** This story produces zero changes inside `apps/`, `infra/scripts/`, `docs/`, or any tracked path. The only artifact lands in gitignored `_bmad-output/implementation-artifacts/`. `git status` after the story is run shows clean tree (modulo unrelated drift). No `infra/scripts/deploy.sh` is invoked.

9. **AC9 — Sprint-status update.** When the discovery is complete and the report file is written, `_bmad-output/implementation-artifacts/sprint-status.yaml` updates `2-1-glitchtip-discovery-empirical-filter-ruleset` from `ready-for-dev` to `done` (this story has no review surface — the output IS the review). `epic-2` flips from `backlog` to `in-progress` if not already done by `bmad-create-story` (it is — see Step 1.6 of the activation log).

## Tasks / Subtasks

- [x] **Task 1: Pre-flight (AC1, AC6, AC7)**
  - [x] Subtask 1.1: From the 3d-portal repo root, source the env: `set -a; source infra/.env; set +a`. Confirm `GLITCHTIP_AUTH_TOKEN`, `GLITCHTIP_ORG_SLUG`, `GLITCHTIP_PROJECT_SLUG` are populated (via `[ -n "$GLITCHTIP_AUTH_TOKEN" ] || echo missing`). Do NOT print the token value.
  - [x] Subtask 1.2: Verify `jq` and `curl` are on PATH (`command -v jq curl >/dev/null` — same idiom as `verify-symbolication.sh`).
  - [x] Subtask 1.3: Determine GlitchTip URL: prefer LAN (`http://192.168.2.190:8800` — same default as `verify-symbolication.sh`). If the dev box is off-LAN, fall back to `https://glitchtip.ezop.ddns.net` (sub-MB GETs work fine over the public proxy per Decision D). Record which endpoint was used in the report header.
  - [x] Subtask 1.4: Reachability smoke: `curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "$GLITCHTIP_URL/api/0/organizations/"` should return `200`. On non-200, stop and surface the failure mode (`401`/`403` → token/scope problem; `5xx` → GlitchTip down; other → unexpected). Do NOT proceed with the discovery if reachability fails — that's an unknown unknown.

- [x] **Task 2: Fetch top 100 issues for the 30-day window (AC1, AC3 header section, AC6)**
  - [x] Subtask 2.1: Run the canonical query (URL-encode the path components if the slugs ever contain special characters; for the homelab `homelab` / `3d-portal` they don't):
        ```bash
        curl -sS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
          "$GLITCHTIP_URL/api/0/projects/$GLITCHTIP_ORG_SLUG/$GLITCHTIP_PROJECT_SLUG/issues/?statsPeriod=30d&limit=100&sort=lastSeen" \
          > /tmp/gt-issues-30d.json
        ```
  - [x] Subtask 2.2: Capture `Link` headers separately (`-D /tmp/gt-issues-30d.headers`) so pagination can be inspected if needed (per agent-guide's pagination section). For 30-day homelab volume, 100 issues is expected to comfortably cover the window — but if the response saturates the limit AND a `next` cursor is present in `Link`, fetch the next page once and merge for a 200-issue ceiling. Document in the report whether pagination was triggered.
  - [x] Subtask 2.3: Sanity-check the response shape with `jq 'length'` on `/tmp/gt-issues-30d.json` (expect a JSON array of issue objects). If it's an object with `detail` field, that's an error response — abort with the body printed.

- [x] **Task 3: Extract + rank top 25 (AC3 frequency table)**
  - [x] Subtask 3.1: Use `jq` to project the fields needed and sort by `count` (event-count, not issue-count) descending. Field gotcha (per agent-guide, line 276): `/issues/` list returns **camelCase** (`lastSeen`, `count`, `culprit`, `title`). The example projection:
        ```bash
        jq -r '.[] | {id,title,count: (.count|tonumber),culprit,lastSeen,permalink}' /tmp/gt-issues-30d.json \
          | jq -s 'sort_by(-.count) | .[:25]'
        ```
  - [x] Subtask 3.2: For each of the top 25, optionally fetch `GET /api/0/issues/<id>/events/latest/` (read-only) to extract `request.url` from the latest event payload. Skip when the count is small (`<5`) and the title alone is enough to reason about the noise pattern — drill-down is for cases where the URL identifies the noise source (e.g., extension URL pattern in `request.url`). Cap drill-down to the top 10 issues to keep the discovery quick.
  - [x] Subtask 3.3: Build the markdown table with columns `rank | count | title | culprit | sample request.url | last_seen`. Escape pipes inside titles (`|` → `\|`). If `request.url` is absent, write `—`.

- [x] **Task 4: Derive `denyUrls` patterns (AC3, AC5, FR5)**
  - [x] Subtask 4.1: Always include the 3 anticipated-minimum extension regexes:
        ```typescript
        /^chrome-extension:\/\//,           // floor: anticipated minimum (FR5)
        /^moz-extension:\/\//,              // floor: anticipated minimum (FR5)
        /^safari-web-extension:\/\//,       // floor: anticipated minimum (FR5)
        ```
  - [x] Subtask 4.2: Scan the top-25 + drill-down `request.url` values for any URL family that's clearly noise but NOT a browser-extension scheme (e.g., a CDN that injects ads, a third-party widget). For each one, propose a regex (anchored where appropriate) and append below the floor section with `// empirical: <count> events — <one-sentence rationale>`. Be conservative: only add when the count is meaningful (≥3 events from the same URL family) and the noise is unambiguous (clearly non-app traffic). False positives here silently drop real signal.
  - [x] Subtask 4.3: Verify each empirical addition is a regex literal (slash-delimited), not a string. Story 2.4's `instrument-filters.ts` will use `RegExp[]`, not `string[]`.

- [x] **Task 5: Derive `ignoreErrors` patterns (AC3, AC5, FR6)**
  - [x] Subtask 5.1: Always include the 2 anticipated-minimum noise-title regexes:
        ```typescript
        /ResizeObserver loop/,                              // floor: anticipated minimum (FR6)
        /Non-Error promise rejection captured/,             // floor: anticipated minimum (FR6)
        ```
  - [x] Subtask 5.2: Scan the top-25 titles for noise families. Common candidates to consider (only add if observed): `/Script error\./` (cross-origin script with stripped detail), `/Failed to fetch/` (network blip noise), `/Load failed/` (Safari analog), `/Object Not Found Matching Id/` (common extension-injected error), `/cancelled/` (AbortController noise). Propose a regex per family with `// empirical: <count> events — <rationale>`.
  - [x] Subtask 5.3: Match against `event.exception?.values?.[0]?.value` (per Decision H step 2, architecture line 301) — when in doubt about whether a title comes from `value` vs `type` vs `culprit`, drill into one event of that issue family via `/issues/<id>/events/latest/` and inspect `data.exception.values[0].value`.
  - [x] Subtask 5.4: Be conservative: same threshold as Task 4 (≥3 events, unambiguous noise). Errors that COULD be real bugs (e.g., `/TypeError/`, `/ReferenceError/`) NEVER make it into `ignoreErrors` — those are signal, not noise, even when high-volume.

- [x] **Task 6: Write the discovery markdown (AC2, AC3)**
  - [x] Subtask 6.1: Resolve filename: `OUT="_bmad-output/implementation-artifacts/glitchtip-discovery-$(date -u +%Y-%m-%d).md"`. If a file with the same date already exists (re-run on the same day), overwrite it — discovery is idempotent.
  - [x] Subtask 6.2: Compose the report with the 6 mandatory sections (header, frequency table, denyUrls, ignoreErrors, methodology, appendix). Use the structure layout below — this is the contract Story 2.4 reads.
  - [x] Subtask 6.3: In the appendix, paste the actual `curl` invocations with the token rewritten as `$GLITCHTIP_AUTH_TOKEN` placeholder. Confirm the file does not contain the literal token value (`grep -q '<first-6-chars-of-token>' "$OUT"` should return non-zero).

- [x] **Task 7: Verify Story 2.4 paste-readiness (AC4)**
  - [x] Subtask 7.1: Extract just the `denyUrls` array body from the report and run:
        ```bash
        node -e 'const a=[/* paste array body here */]; console.log(`denyUrls: ${a.length} regexes,`, a.every(r=>r instanceof RegExp) ? "all valid" : "INVALID")'
        ```
        Expected: prints count + `all valid`. If parsing fails (e.g., comma after last item, comment syntax), fix the markdown.
  - [x] Subtask 7.2: Repeat for `ignoreErrors`. Both arrays must round-trip cleanly into a Node REPL.
  - [x] Subtask 7.3: Spot-check one regex from each array against a sample input that should match (e.g., `/^chrome-extension:\/\//.test('chrome-extension://abc/inject.js')` → `true`).

- [x] **Task 8: Token hygiene + working tree audit (AC7, AC8)**
  - [x] Subtask 8.1: `grep -i "$(echo $GLITCHTIP_AUTH_TOKEN | head -c 10)" _bmad-output/implementation-artifacts/glitchtip-discovery-*.md` should return zero hits. If anything matches, redact and re-write.
  - [x] Subtask 8.2: `git status` should show no changes inside tracked paths. The new markdown lives under `_bmad-output/` (gitignored) and is invisible to git. Confirm with `git status --ignored | grep glitchtip-discovery`.
  - [x] Subtask 8.3: Do NOT run `infra/scripts/deploy.sh`. This story produces nothing deployable — auto-deploy memory rule explicitly excludes doc-only / artifact-only work.

- [x] **Task 9: Sprint-status finalization (AC9)**
  - [x] Subtask 9.1: Update `_bmad-output/implementation-artifacts/sprint-status.yaml`:
        - `2-1-glitchtip-discovery-empirical-filter-ruleset: ready-for-dev → done`
        - Append a brief inline comment: `# Discovery shipped <YYYY-MM-DD>; ruleset paste-ready into Story 2.4 instrument-filters.ts.`
        - Update `last_updated` field to today's date.
  - [x] Subtask 9.2: `epic-2` should already be `in-progress` (set by `bmad-create-story` activation when this story file was created). If for some reason it's still `backlog`, flip it to `in-progress`.

## Discovery Markdown Layout (the contract Story 2.4 reads)

````markdown
# GlitchTip Discovery — 30-Day Issue Sample + Empirical Filter Ruleset

**Run timestamp (UTC):** 2026-05-10T12:34:56Z
**GlitchTip endpoint:** http://192.168.2.190:8800
**Project:** homelab / 3d-portal
**Window:** statsPeriod=30d (sort=lastSeen, limit=100, [pagination=triggered|not_triggered])
**Total issues returned:** 47

## Top 25 issues by event count (descending)

| rank | count | title | culprit | sample request.url | last_seen |
|---|---|---|---|---|---|
| 1 | 142 | ResizeObserver loop limit exceeded | unknown | https://3d.ezop.ddns.net/catalog/m_142 | 2026-05-10T11:08:42Z |
| 2 | 89 | Script error. | unknown | chrome-extension://abc/inject.js | 2026-05-10T09:14:12Z |
| ... | ... | ... | ... | ... | ... |

## Derived `denyUrls` (regex array, paste-ready into Story 2.4 `instrument-filters.ts`)

```typescript
export const denyUrls: RegExp[] = [
  // --- floor: anticipated minimums (FR5) ---
  /^chrome-extension:\/\//,           // floor: anticipated minimum (FR5)
  /^moz-extension:\/\//,              // floor: anticipated minimum (FR5)
  /^safari-web-extension:\/\//,       // floor: anticipated minimum (FR5)
  // --- empirical additions ---
  /^https:\/\/widgets\.example\.com\//, // empirical: 17 events — third-party widget injecting console.error
];
```

## Derived `ignoreErrors` (regex array, paste-ready into Story 2.4 `instrument-filters.ts`)

```typescript
export const ignoreErrors: RegExp[] = [
  // --- floor: anticipated minimums (FR6) ---
  /ResizeObserver loop/,                              // floor: anticipated minimum (FR6)
  /Non-Error promise rejection captured/,             // floor: anticipated minimum (FR6)
  // --- empirical additions ---
  /Script error\./,                                   // empirical: 89 events — cross-origin scripts strip detail
  /Object Not Found Matching Id/,                     // empirical: 23 events — known extension-injected error
];
```

## Methodology

Patterns are anchored where the noise source is structural (`^chrome-extension:\/\/` matches the URL scheme exactly). Title patterns use a substring regex (`/ResizeObserver loop/`) rather than the full literal because GlitchTip / browser variants append `limit exceeded` / `completed with undelivered notifications` — matching the family is more robust than an exact string. Empirical additions require ≥3 events and unambiguous noise (i.e., the issue is clearly not signal). Real error families (`TypeError`, `ReferenceError`) never enter `ignoreErrors` — those are bugs, not noise.

## Appendix — sample queries used

```bash
# 30-day issue list (top 100 by lastSeen)
curl -sS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GLITCHTIP_URL/api/0/projects/$GLITCHTIP_ORG_SLUG/$GLITCHTIP_PROJECT_SLUG/issues/?statsPeriod=30d&limit=100&sort=lastSeen" \
  > /tmp/gt-issues-30d.json

# Drill-down: latest event for issue <id> (camelCase shape)
curl -sS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GLITCHTIP_URL/api/0/issues/<id>/events/latest/"
```
````

## Dev Notes

### What this story is and isn't

**Is:** A read-only investigation that emits a markdown report. Output is the only deliverable. The dev runs queries, reads JSON, makes editorial calls about regex granularity, writes a file. No TypeScript, no bash scripts, no docker, no deploy.

**Isn't:** A code-shipping story. Don't create `apps/web/src/instrument-filters.ts` here — that's Story 2.4. Don't modify `apps/web/src/instrument.ts` — that's Stories 2.2/2.3/2.4. Don't write a permanent script under `infra/scripts/` — discovery is a one-shot, not a recurring ritual (FR16's "decay protection" is for `verify-symbolication.sh`, not for filter rulesets — those rebase only when a follow-up scope explicitly requests it).

### Architecture pin: AR11 (Discovery story — empirical filter ruleset)

> Sample 30-day GlitchTip issues from homelab instance → derive empirical `denyUrls` / `ignoreErrors` patterns. Anticipated minimums (browser-extension URLs, `ResizeObserver loop`) are a floor, not a ceiling. Output gates AR6 / FR6 implementation.
> [Source: `_bmad-output/planning-artifacts/epics.md` line 150]

The "floor, not a ceiling" framing is the crux: the dev MUST emit the anticipated minimums even when the 30-day sample shows zero hits, because future builds will see them (extensions especially). Empirical additions ONLY extend that floor; they never replace it.

### Architecture pin: AR6 / Decision H (`beforeSend` filter ordering)

> Filter executes in fixed order with separate `if` branches and early `return null`: (1) `denyUrls` regex match against `event.request?.url`; (2) `ignoreErrors` title match against `event.exception?.values?.[0]?.value`; (3) `!navigator.onLine` → drop; (4) `hint.originalException instanceof ApiError && hint.originalException.body?.detail === "access_expired"` → drop; (5) return event unchanged.
> [Source: `_bmad-output/planning-artifacts/epics.md` line 143; `_bmad-output/planning-artifacts/architecture.md` lines 205–210, 298–306]

This is Story 2.4's territory — but Story 2.1's output IS the input to step (1) and step (2). Two implications:
- **`denyUrls` regexes are matched against `event.request?.url`**, which is the page URL the user was on when the event fired (NOT the script URL). For browser-extension noise that fires from `chrome-extension://...` pages this matches; for noise injected into the user's `request.url` via referrer-style attribution, it also matches. If the noise source is a script URL only (not a page URL), it won't be caught by `denyUrls` — drop it via `ignoreErrors` (title) instead, or accept that this filter family is not the right tool.
- **`ignoreErrors` regexes are matched against `event.exception?.values?.[0]?.value`**, i.e., the FIRST exception's `value` field. NOT `title`, NOT `culprit`, NOT `message`. When picking a regex from a top-25 title, verify against an actual `events/latest/` payload that the title text appears in `exception.values[0].value` — sometimes GlitchTip's "title" is a derived/synthesized string not literally present in `value`.

### Architecture pin: AR13 (curl + jq idiom for GlitchTip REST)

> Standard pattern across the four scripts: `http_code=$(curl -sS -o /tmp/gt-response.json -w '%{http_code}' -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "$GLITCHTIP_URL/api/0/...")` followed by a `case "$http_code"` dispatch (20* success, 401/403 → exit 3, 5* → exit 2, * → exit 1).
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 387–407]

Story 2.1 isn't writing a permanent script, but the dev SHOULD use the same idiom for one-off queries — it surfaces auth/scope failures cleanly instead of silently producing empty JSON. If the dev opts for a tiny throwaway shell script in `/tmp/` to run the discovery, follow this pattern.

### NFR pins

- **NFR-S1 (Token hygiene):** `GLITCHTIP_AUTH_TOKEN` exists ONLY in `infra/.env` on the dev box. Never in image layers, never in commits, never in BMAD planning artifacts. The discovery markdown follows the same rule — only `$GLITCHTIP_AUTH_TOKEN` placeholders, never the resolved value. [Source: `_bmad-output/planning-artifacts/prd.md` NFR-S1]
- **NFR-S2 (Read-only triage scope):** The triage path is read-only; only `GET` requests against `/api/0/...`. Story 2.1 honors this — no issue mutation as a discovery side effect. [Source: PRD FR20]
- **NFR-I3 (BMAD pipeline contract):** Story 2.4 imports from this file literally; the layout in this story IS the contract. Drift between this layout and Story 2.4's import expectations is a breaking change. [Source: PRD NFR-I3]

### File-structure footprint (single NEW artifact, gitignored)

| Path | Status | Notes |
|---|---|---|
| `_bmad-output/implementation-artifacts/glitchtip-discovery-<YYYY-MM-DD>.md` | NEW | Single output file. Gitignored (the `_bmad-output/` line in `.gitignore`). Stays local to the dev box. |
| Everything else | UNTOUCHED | No source file modifications. No commits expected from this story. |

### GlitchTip API surface notes (load-bearing for the discovery)

- **Endpoint base (LAN):** `http://192.168.2.190:8800/api/0/` — preferred for the dev box on home LAN. HTTP, not HTTPS — that's by design (the LAN proxy bypass per Decision D, architecture line 175).
- **Endpoint base (public fallback):** `https://glitchtip.ezop.ddns.net/api/0/` — works for sub-MB GETs from off-LAN. Same Bearer token works against both.
- **Issues list query parameters:** `statsPeriod=30d` is the canonical 30-day window. `sort=lastSeen` orders by most-recently-seen issue. `limit=100` is the max page size GlitchTip 6.1.x honors per request — pagination via `Link` header `cursor=` if more entries exist (rare for 3d-portal volume, but check).
- **Response shape gotcha (camelCase vs snake_case):** `/issues/<id>/events/latest/` returns **camelCase** (`eventID`, `dateCreated`, `groupID`). But `/issues/<id>/events/` (the *list*) returns **snake_case** (`event_id`, `date_created`). The 30-day list at `/projects/<org>/<proj>/issues/` returns **camelCase** (issue summaries — `lastSeen`, `firstSeen`, `count`, `culprit`, `permalink`). Don't pipe between them without normalizing. [Source: `~/repos/configs/docs/glitchtip-agent-guide.md` line 276]
- **Issue object key fields used here:** `id` (numeric string), `title` (string), `count` (numeric — total event count for the issue, what we rank by), `culprit` (string or null), `lastSeen` (ISO-8601 string), `permalink` (string — direct link to GlitchTip web UI for the issue, useful as reference but NOT required in the report).

### Why this story has no review gate

Most stories ship with a `done` ← `review` ← `in-progress` arc, with `code-review` running before close-out. Story 2.1 bypasses `review` because:
1. The output is a markdown file, not code — nothing to lint/typecheck/test.
2. The output is gitignored — it never enters PR/code-review surface.
3. Story 2.4 is the implicit consumer-side review: if 2.1's output is wrong, 2.4 will fail (paste fails parse, regex doesn't match, etc.) and 2.1 gets re-run.

This pattern is consistent with Story 1.1 (Phase 0 dry-run gate), which also produced a `_bmad-output/`-only artifact (`phase0-result.md`) and went `ready-for-dev` → `done` directly.

### Project context patterns inherited (not re-stated here)

The following patterns from `_bmad-output/project-context.md` apply unchanged:
- **Bash script conventions** (when running ad-hoc shell): `set -euo pipefail`, `command -v jq curl >/dev/null` dependency check, `set -a; source infra/.env; set +a` env loading, no silent defaults on required vars.
- **Doc-only commits skip auto-deploy** — but this story produces NO commits at all (output is gitignored), so the rule is doubly out of scope.
- **Cross-repo grounding before non-trivial work** — `~/repos/configs/docs/glitchtip-agent-guide.md` is the canonical REST recipe source. Read it if any unfamiliar query is needed.

## Previous Story Intelligence

### From Epic 1 close-out (Stories 1.1 → 1.6, all `done`)

- **Story 1.1 / `phase0-result.md`** established the load-bearing facts that Story 2.1 inherits:
  - `infra/.env` is the single token source. `GLITCHTIP_AUTH_TOKEN` exists there with the right scopes (`org:read`, `project:read`, `event:write`); `org:read` + `project:read` are sufficient for read-only discovery.
  - LAN endpoint `http://192.168.2.190:8800` works end-to-end for REST GETs (Phase 0 re-run #2 hit it for chunk-upload config; the same auth + base path serves issue queries).
  - Public fallback `https://glitchtip.ezop.ddns.net` is fine for sub-MB GETs (proven by Phase 0's nginx body-size investigation — only the chunk-upload path needed the 50 MB bump; standard REST GETs were unaffected).
- **Story 1.6 close-out** documented the "every replacement keeps its predecessor as documented manual recovery for one release cycle" principle. This story is upstream of any code change — Story 2.4 is the consumer; the discovery output IS the input contract, not a replacement of an existing mechanism.

### From Epic 3 close-out (Stories 3.1 → 3.4, all `done`)

- **Story 3.1 (`verify-symbolication.sh`)** is the gold reference for bash conventions when querying the same GlitchTip REST API. Its header doc-block format, env validation, exit-code map, and curl+jq idiom are the patterns Story 2.1 follows for its (one-shot, throwaway) shell session — though no permanent script lands.
- **Story 3.1's debug log** notes that GlitchTip's `/api/0/projects/.../issues/?query=smoke.run_id:<uuid>` accepted the search query and returned the correct issue. The same query mechanic (substring match on title + structured tag matchers) is available to Story 2.1 if a deeper drill is needed — but the canonical 30-day list query is `statsPeriod=30d&limit=100&sort=lastSeen`, no `query=` param needed.
- **Story 3.4 (project-context.md +3 rules)** added the "use `glitchtip-triage.sh <issue_id>` before manual triage" rule. That script ships in Story 2.5 — until then, Story 2.1's discovery uses raw curl+jq directly. No conflict.

### From the Phase 0 / nginx config-fix narrative

- The public proxy at `~/repos/configs/nginx/glitchtip.ezop.ddns.net.conf` has `client_max_body_size 50m;` only on the `chunk-upload` path; standard `/api/0/` paths stay at 1 MB. Discovery queries are well under that — a top-100 issues response is typically 100–500 KB.
- Two test releases (`0.1.0+phase0`, `0.1.0+phase0-direct`) were created on the GlitchTip server during Phase 0 and later DELETEd via `/api/0/projects/.../releases/<v>/`. Those mutations are NOT Story 2.1's concern — discovery is read-only, and any noise from those test runs would have been ≥1 day old at this story's run time, well-aged out of relevance.

## Git Intelligence Summary

Recent commits (top of `main` as of story creation):

| SHA | Subject | Relevance to Story 2.1 |
|---|---|---|
| 50a7292 | docs(operations): rewrite GlitchTip section for current state (Story 3.3) | Reference: `docs/operations.md` carries the post-deploy verify ritual + token rotation procedure. Useful background for understanding the operational frame Story 2.1 sits inside. |
| 31dac06 | feat(infra): wire verify-symbolication into deploy.sh post-alembic (Story 3.2) | Establishes that `deploy.sh` calls verify after alembic. Story 2.1 doesn't deploy and doesn't run verify — separate axis. |
| 82addc7 | fix(infra+web): address Codex review of Story 3.1 (HIGH+MED+LOW) | Final state of `verify-symbolication.sh` post-review. Source-of-truth for bash conventions Story 2.1's ad-hoc shell session should mirror. |
| 11f048e | feat(infra): verify-symbolication.sh + smoke-trigger handler (Story 3.1) | First land of `verify-symbolication.sh` — the curl+jq idiom is consistent with what Story 2.1 will use for one-off queries. |
| 9e69e62 | chore(infra): decouple upload-sourcemaps.sh from deploy.sh (Story 1.6) | Establishes the "kept as documented manual recovery" principle. Story 2.1 doesn't replace anything, so the principle doesn't apply directly — but it's the philosophical context. |
| 6488cf8 | chore(bmad): bootstrap | Initial BMAD setup — `_bmad-output/` tree exists, gitignored, ready to receive the discovery markdown. |

No commit in the recent window touches `apps/web/src/instrument.ts` (last meaningful change to that file is older — the current state is the 2026-04-30 baseline + Story 1.2's `RELEASE` import). Story 2.2 is the next story to modify it; Story 2.1 has zero source-tree footprint.

## Latest Tech Information

### GlitchTip 6.1.x REST API — issue list endpoint

The canonical query for the 30-day issue sample is:

```
GET /api/0/projects/<org_slug>/<project_slug>/issues/?statsPeriod=30d&limit=100&sort=lastSeen
```

Notable response fields per issue (camelCase shape):
- `id` (string) — numeric ID, used in `/issues/<id>/...` follow-up calls.
- `title` (string) — the synthesized issue title; matches what GlitchTip web UI shows.
- `count` (string of digits — note: NOT a number in JSON, despite numeric content; cast via `tonumber` in jq).
- `culprit` (string or empty) — the function/module GlitchTip extracted from the top frame; often empty for cross-origin scripts.
- `lastSeen` / `firstSeen` (ISO-8601 timestamps).
- `permalink` (URL to the GlitchTip web UI for the issue).
- `level` (string: `error`, `warning`, `info`, etc.).
- `metadata.value` (string) — the `exception.values[0].value` field, often present in summary form. **This is the field `ignoreErrors` matches against** (per Decision H step 2). When `metadata.value` is present in the issue summary, the dev can derive the regex without drilling into `events/latest/`. When it's absent, fetch one event.

Pagination via `Link` headers (rel=`next`/`previous` + `cursor=`); see `~/repos/configs/docs/glitchtip-agent-guide.md` line 314 for the format.

### Sentry/GlitchTip `denyUrls` behavior

Sentry SDK 8.x's `denyUrls` (and the equivalent in `beforeSend`) matches against the **page URL** (`event.request.url`), NOT the script URL where the error originated. This is a frequent source of confusion: if a `chrome-extension://abc/` script throws on a `https://3d.ezop.ddns.net/` page, `event.request.url` is the latter, not the former — and `denyUrls` won't catch it. For extension noise that fires WHILE the user is on a real app page, `denyUrls` is mostly ineffective; the noise needs to be caught via `ignoreErrors` on the title family (or via the `event.exception.values[0].stacktrace.frames[].filename` check, which Story 2.4's `beforeSend` does NOT currently include — out of scope).

The 3 anticipated-minimum extension regexes in `denyUrls` cover the case where the user is **on** an extension-injected page when the event fires (rare but real — happens when extensions inject iframes that throw). They're cheap insurance, mandatory per FR5, but don't shoulder the bulk of extension-noise filtering.

### TypeScript regex literal compatibility

The output `denyUrls` and `ignoreErrors` arrays are typed `RegExp[]` in Story 2.4's `apps/web/src/instrument-filters.ts`. Modern TypeScript (5.x with `strict`) accepts regex literals directly without explicit `new RegExp(...)` wrapping. Slash-delimited literals (`/pattern/flags`) work; comments in JSON-style arrays (`,` after the last element is fine — Vite's parser tolerates trailing commas in TS).

## Project Context Reference

The dev MUST read `_bmad-output/project-context.md` before implementation. Critical rules for Story 2.1:

- **Token hygiene** (Critical Don't-Miss → Cross-cutting → "No secrets in commits, plans, or `_bmad-output/`"): the 3-line rule applies. Output file passes the audit only if the resolved token never appears in it.
- **`docs/plans/` is gitignored** — analogous: `_bmad-output/` is also gitignored. The discovery markdown is allowed to inline internal hostnames (`192.168.2.190:8800`) because it stays on the dev box.
- **Cross-repo grounding** — `~/repos/configs/docs/glitchtip-agent-guide.md` is the canonical REST source. Read it before reaching for any unfamiliar query syntax.
- **No silent scope creep** — discovery doesn't write code, doesn't ship a permanent script, doesn't touch `apps/`. If a regex pattern looks edge-case enough to warrant code, it's Story 2.4's call, not Story 2.1's.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 384–408 — Story 2.1 + Epic 2 framing + Story 2.4 dependency.
- `_bmad-output/planning-artifacts/epics.md` lines 143, 150 — AR6 + AR11 specifics.
- `_bmad-output/planning-artifacts/architecture.md` lines 205–210 — Decision H (`beforeSend` filter contract).
- `_bmad-output/planning-artifacts/architecture.md` lines 292–306 — Sentry SDK usage idioms (filter ordering, regex match targets).
- `_bmad-output/planning-artifacts/architecture.md` lines 387–407 — curl + jq idiom (AR13).
- `_bmad-output/planning-artifacts/prd.md` FR5, FR6, FR20, NFR-S1, NFR-S2, NFR-I3 — functional + non-functional pins.
- `_bmad-output/implementation-artifacts/phase0-result.md` — confirms `infra/.env` token + LAN endpoint reachability.
- `_bmad-output/implementation-artifacts/3-1-verify-symbolication-script.md` — bash conventions reference for ad-hoc REST queries.
- `~/repos/configs/docs/glitchtip-agent-guide.md` — canonical GlitchTip REST recipe source (auth flow, pagination, schema gotchas).
- `apps/web/src/instrument.ts` (current state, 19 lines) — baseline that Story 2.4 will modify; Story 2.1 does NOT touch it.
- `infra/scripts/verify-symbolication.sh` (current state, post-Story 3.1) — exemplar bash script for GlitchTip REST querying.

## Dev Agent Record

### Agent Model Used

`claude-opus-4-7[1m]` (Claude Opus 4.7, 1M context) — running in same session as `bmad-create-story` (cache-warm continuation per operator decision; 5h budget at 32% at story-dev start).

### Debug Log References

- **Pre-flight (Task 1):** `infra/.env` mode 600 ✓; `jq`/`curl`/`node` on PATH ✓; token len=64 ✓; org=`homelab`, project=`3d-portal`; `GLITCHTIP_URL` unset → defaulted to LAN `http://192.168.2.190:8800`. Reachability smoke (`GET /api/0/organizations/`) returned `http_code=200 size=287`.
- **Sourcing snag flagged to operator:** `set -a; source infra/.env; set +a` triggered a bash error on line 17 of `infra/.env` — a 128-char hex value (NOT `GLITCHTIP_AUTH_TOKEN`, which has len=64) was treated as a command. Operator informed mid-flow; subsequent invocations used `( set -a; source infra/.env 2>/dev/null; set +a; ... )` to suppress the syntax noise without affecting the working env vars. Out of scope to fix from this story; flagged for follow-up.
- **API gotcha (Task 2):** GlitchTip 6.1.x rejected the epic-AC's `sort=lastSeen` (camelCase) with HTTP 422 + literal_error citing the allowed set: `last_seen, first_seen, count, priority, -last_seen, -first_seen, -count, -priority` (snake_case + sign prefix for descending). Switched to `sort=-count` (front-loads noisiest by event count, which is what ranking ultimately wants). Documented the gotcha in the discovery report's Methodology section.
- **Fetch result:** `http_code=200 size=20725 bytes`. `jq 'length'` returned `21` issues — well below the 100-row limit, no pagination triggered.
- **Schema gotcha (Task 3, drill-down):** `/api/0/issues/<id>/events/latest/` does NOT carry a top-level `.exception` or `.request` field. Both live under `entries[]` keyed by `type`: `entries[].type=="exception".data.values[0].value` and `entries[].type=="request".data.url`. This is REST-only; the SDK-side `beforeSend(event, hint)` callback that Story 2.4 wires up receives the canonical `event.exception.values[0].value` / `event.request.url` shape. Documented in the report's "Drill-down findings" + Methodology sections.
- **Paste-readiness (Task 7):** Node REPL round-trip:
  - `denyUrls`: 3 regexes, all valid; `chrome-extension://abc/inject.js` → match ✓; `moz-extension://xyz/popup.js` → match ✓; `https://3d.ezop.ddns.net/catalog/m_142` → no match ✓.
  - `ignoreErrors`: 2 regexes, all valid; `ResizeObserver loop limit exceeded` → match ✓; `Non-Error promise rejection captured with value: undefined` → match ✓; `TypeError: Cannot read property foo of undefined` → no match ✓ (real bugs not filtered).
- **Token hygiene (Task 8):** 10-char prefix `grep -F` against the 158-line / 12,346-byte report → no match. `git status` clean. `git check-ignore -v` confirms the report is matched by `.gitignore:65: _bmad-output/`.

### Completion Notes List

- **Empirical sample composition** — 21 issues / 27 events across the 30-day window. **100% synthetic/operator-driven**, no genuine production noise:
  - 1 issue / 7 events: `verify-symbolication.sh` synthetic alarm (`deploy.verification=failed`) — operator alarm signal, not noise.
  - 12 issues / 12 events: smoke events emitted by `verify-symbolication.sh` from `https://3d.ezop.ddns.net/?__sentry_smoke=<uuid>` — proof-of-life signal, not noise.
  - 5 issues / 5 events: phase-0/3/4 manual verification events from 2026-04-30 (historical operator artifacts).
  - 1 issue / 1 event: `RuntimeError: sentry-test: deliberate test event` from `/api/admin/sentry-test` — asserted endpoint per project-context.md, not a bug.
  - 2 issues / 2 events: backend `FileNotFoundError` from catalog migration test paths — out of scope for frontend `beforeSend`.
- **Empirical additions: 0.** No browser-extension URLs, no `ResizeObserver loop`, no `Script error.`, no `Non-Error promise rejection`, no `Object Not Found Matching Id`, no `Failed to fetch`/`Load failed`. The homelab project simply has no organic browser traffic yet — the only frontend events GlitchTip has seen are operator-driven test artifacts.
- **Floor patterns enacted as mandated** (FR5 + FR6, AC5 of this story): 3 `denyUrls` regexes (`/^chrome-extension:\/\//`, `/^moz-extension:\/\//`, `/^safari-web-extension:\/\//`) + 2 `ignoreErrors` regexes (`/ResizeObserver loop/`, `/Non-Error promise rejection captured/`).
- **Recommendation captured in report:** revisit discovery 30 days post-organic-traffic activation. Until then, the empirical layer is intentionally empty. Re-running discovery is the canonical way to extend the ruleset (manual edits to `instrument-filters.ts` would drift from observed reality).
- **Schema gotcha worth flagging to Story 2.4 author:** when writing unit tests for `beforeSend`, use the SDK-side shape (`event.exception.values[0].value`, `event.request.url`) — that's what Sentry passes to the callback. The REST-side `entries[].type==...` shape is only for verifying that an event landed in GlitchTip, not for SDK callback testing.
- **Epic-AC vs reality gap (sort key):** Epic 2.1 AC1 referenced `sort=lastSeen` (camelCase). Real GlitchTip 6.1.x requires snake_case (`sort=-count` was used here). Not a defect in either layer — epic was written speculatively before the homelab API was probed; the gap is now closed in the report's Methodology section. Story 2.5 (`glitchtip-triage.sh`) will inherit the same convention since it queries the same REST surface.
- **No code changes.** No commits expected. No `infra/scripts/deploy.sh` invocation. The single artifact (`glitchtip-discovery-2026-05-09.md`) lives in the gitignored `_bmad-output/` tree, local to the dev box.
- **Filename note:** `date -u +%Y-%m-%d` resolved to `2026-05-09` at run time (UTC was still 2026-05-09T23:47Z when the discovery executed). System context `currentDate=2026-05-10` reflected user-localtime; AC2 explicit pin to `date -u` was honored. Filename: `glitchtip-discovery-2026-05-09.md`.

### File List

| Path | Status | Notes |
|---|---|---|
| `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` | NEW | Single artifact; gitignored (`.gitignore:65: _bmad-output/`). 158 lines / 12,346 bytes. Token-leak-free (10-char-prefix `grep -F` returns zero hits). |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | MODIFIED | Story `2-1-...` flipped `ready-for-dev → in-progress → done`; `epic-2: backlog → in-progress`; `last_updated → 2026-05-10`. Gitignored. |
| `_bmad-output/implementation-artifacts/2-1-glitchtip-discovery-empirical-filter-ruleset.md` | MODIFIED | This file. Status `ready-for-dev → done`; all 9 task groups + subtasks marked `[x]`; Dev Agent Record filled. Gitignored. |

### Change Log

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-09T23:47Z | Claude Opus 4.7 (1M ctx) | Discovery executed; report written; ruleset = floor only (empirical = 0 due to no organic traffic). Status `ready-for-dev → done`. |
