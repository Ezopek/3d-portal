# GlitchTip Discovery — 30-Day Issue Sample + Empirical Filter Ruleset

**Run timestamp (UTC):** 2026-05-09T23:47:05Z
**GlitchTip endpoint:** http://192.168.2.190:8800 (LAN)
**Project:** homelab / 3d-portal
**Window:** statsPeriod=30d (sort=-count, limit=100, pagination=not_triggered — 21 issues fit comfortably under the 100 ceiling)
**Total issues returned:** 21
**Total events represented:** 27 (sum of `count` across the 21 issues)

## Top 25 issues by event count (descending)

The 30-day window contains fewer than 25 issues, so all 21 are listed.

| rank | count | level | title | culprit | last_seen |
|---|---|---|---|---|---|
| 1 | 7 | warning | deploy verification failed: symbolication broken (top frame regex mismatch) | — | 2026-05-09T21:20:33.725Z |
| 2 | 1 | error | RuntimeError: sentry-test: deliberate test event | — | 2026-04-30T19:38:31.546Z |
| 3 | 1 | error | FileNotFoundError: \[Errno 2\] No such file or directory: '/data/catalog/_index/index.json' | — | 2026-04-30T19:44:45.328Z |
| 4 | 1 | error | FileNotFoundError: \[Errno 2\] No such file or directory: '/data/catalog/_index/index.json' | — | 2026-04-30T19:45:43.788Z |
| 5 | 1 | error | VerificationError: phase-3 web SDK config check | — | 2026-04-30T19:51:09.864Z |
| 6 | 1 | error | SourceMapTest: phase-4 sourcemap symbolication check | — | 2026-04-30T20:00:43.962Z |
| 7 | 1 | error | SourceMapTest2: phase-4 sourcemap symbolication check (post-extract) | — | 2026-04-30T20:02:38.973Z |
| 8 | 1 | error | SourceMapTest3: phase-4 envelope test | — | 2026-04-30T20:03:15.730Z |
| 9 | 1 | error | Error: smoke 1082a8ac-a163-4ace-b199-3c4a83c3b54b | — | 2026-05-09T20:46:15.062Z |
| 10 | 1 | error | Error: smoke 6de56054-2c3f-4b5a-8d79-8777483c513b | — | 2026-05-09T20:48:27.904Z |
| 11 | 1 | error | Error: smoke 729c2c4f-a056-4831-8e83-3567799ce08b | — | 2026-05-09T21:04:09.099Z |
| 12 | 1 | error | Error: smoke 401b39ce-3681-4f65-9293-136bded173f4 | — | 2026-05-09T21:13:56.899Z |
| 13 | 1 | error | Error: smoke 825655a9-0b2e-4897-9efe-f3b1544c5bc0 | — | 2026-05-09T21:16:27.221Z |
| 14 | 1 | error | Error: smoke a455e843-77c8-4e25-bd98-4d384c0707c3 | — | 2026-05-09T21:18:12.416Z |
| 15 | 1 | error | Error: smoke 0e759bc5-231c-4652-ad8a-a6bee3b7b448 | — | 2026-05-09T21:20:28.997Z |
| 16 | 1 | error | Error: smoke 0d79704b-6af8-43b6-b37c-062a331e5213 | — | 2026-05-09T21:23:04.992Z |
| 17 | 1 | error | Error: smoke 192a0de1-b3e9-4816-961c-c4e635cd5f25 | — | 2026-05-09T22:37:23.896Z |
| 18 | 1 | error | Error: smoke 45ccc4d9-b668-4987-bd3a-3829dcb03cc3 | — | 2026-05-09T22:44:57.079Z |
| 19 | 1 | error | Error: smoke 26ac0b59-537f-4452-b6ae-367764fc6c0a | — | 2026-05-09T22:45:57.037Z |
| 20 | 1 | info | phase-0 connectivity check | — | 2026-04-30T19:31:08.509Z |
| 21 | 1 | error | Error: smoke e86df3e5-f433-488e-9ea5-c56c5419b120 | — | 2026-05-09T22:46:00.141Z |

## Drill-down findings (top 3 issues + smoke-event family)

Sample queries against `/api/0/issues/<id>/events/latest/` for the highest-count issues and a representative smoke event:

| issue id | exception.values\[0\].value | request.url |
|---|---|---|
| 34 (rank 1, synthetic alarm) | _no exception_ (envelope-injected synthetic event; payload is `level=warning` + `message`, not `exception`) | _no request_ (envelope POSTed by `verify-symbolication.sh`, not from a browser context) |
| 17 (rank 2, sentry-test) | `sentry-test: deliberate test event` | `http://192.168.2.190/api/admin/sentry-test` |
| 18 (rank 3, FileNotFoundError) | `[Errno 2] No such file or directory: '/data/catalog/_index/index.json'` | `http://192.168.2.190/api/admin/render/001` |
| 33 (rank 8, smoke event) | `smoke 1082a8ac-a163-4ace-b199-3c4a83c3b54b` | `https://3d.ezop.ddns.net/?__sentry_smoke=1082a8ac-a163-4ace-b199-3c4a83c3b54b` |

## Sample composition analysis

The 21 issues fall into 5 distinct operational families, **none representing organic user traffic**:

| Family | Count | Origin | Signal vs noise |
|---|---|---|---|
| Synthetic alarm (`deploy.verification=failed`) | 7 events / 1 issue | `verify-symbolication.sh` envelope POST on FAIL | **Signal** (operator alarm — DO NOT filter) |
| `verify-symbolication.sh` smoke events | 12 events / 12 issues | Production SPA at `https://3d.ezop.ddns.net/?__sentry_smoke=<uuid>` | **Signal** (proof-of-life — DO NOT filter) |
| Phase-0/3/4 manual verification | 5 events / 5 issues | One-shot operator-injected events from 2026-04-30 | Historical operator artifact |
| `/api/admin/sentry-test` deliberate throw | 1 event / 1 issue | Backend admin endpoint (FastAPI raises `RuntimeError`) | **Signal** (asserted endpoint per project-context.md) |
| Backend `FileNotFoundError` | 2 events / 2 issues | API path `/api/admin/render/001` failing on missing catalog index | Real backend error (out of scope for frontend `beforeSend` filter) |

**Frontend-originated events from organic traffic: 0.** No browser-extension URLs in any `request.url`. No `ResizeObserver loop` titles. No `Script error.` cross-origin noise. No `Object Not Found Matching Id`. No `Failed to fetch` / `Load failed` patterns.

This reflects the homelab project's current state: 3d-portal has not yet been opened for organic browser traffic. The only frontend events GlitchTip has seen are operator-driven (`verify-symbolication.sh` smoke + manual phase-0..4 tests). Backend events are out of scope for the SDK-side `beforeSend` filter Story 2.4 will implement.

## Derived `denyUrls` (regex array, paste-ready into Story 2.4 `instrument-filters.ts`)

```typescript
export const denyUrls: RegExp[] = [
  // --- floor: anticipated minimums (FR5) ---
  /^chrome-extension:\/\//,           // floor: anticipated minimum (FR5)
  /^moz-extension:\/\//,              // floor: anticipated minimum (FR5)
  /^safari-web-extension:\/\//,       // floor: anticipated minimum (FR5)
  // --- empirical additions ---
  // (none: 30-day sample contained zero browser-extension URLs in `request.url`;
  //  see "Sample composition analysis" — no organic browser traffic yet)
];
```

## Derived `ignoreErrors` (regex array, paste-ready into Story 2.4 `instrument-filters.ts`)

```typescript
export const ignoreErrors: RegExp[] = [
  // --- floor: anticipated minimums (FR6) ---
  /ResizeObserver loop/,                              // floor: anticipated minimum (FR6)
  /Non-Error promise rejection captured/,             // floor: anticipated minimum (FR6)
  // --- empirical additions ---
  // (none: 30-day sample contained zero noise-title patterns; the entire sample
  //  is operator-driven test/synthetic/smoke events. Filtering smoke events would
  //  defeat verify-symbolication's purpose — they are signal, not noise.)
];
```

## Methodology

The 30-day window was queried via `GET /api/0/projects/homelab/3d-portal/issues/?statsPeriod=30d&limit=100&sort=-count` (snake_case `last_seen`/`-count` is required by GlitchTip 6.1.x — the camelCase `lastSeen` epic-AC reference returned 422). Sorting by `-count` (descending event count) front-loads the noisiest families when present; in this sample the synthetic alarm (count=7) was the only multi-event issue, with the rest at count=1. Pagination was not triggered (21 < 100 limit).

Drill-down via `GET /api/0/issues/<id>/events/latest/` confirmed the schema for `request.url` and `exception.values[0].value` extraction. **Schema gotcha worth flagging for Story 2.4:** the REST API surfaces these fields under `entries[].type=={"exception"|"request"}.data.{values|url}`, NOT at the top-level `event.exception`/`event.request` shape the Sentry SDK passes to `beforeSend(event, hint)` callbacks. Story 2.4's unit tests will mock the SDK-side shape directly (`event.exception.values[0].value`, `event.request.url`); REST roundtrip verification was not in this story's scope.

Patterns are anchored where the noise source is structural (`^chrome-extension:\/\/` matches the URL scheme exactly). Title patterns use a substring regex (`/ResizeObserver loop/`) rather than the full literal because GlitchTip and browser variants append `limit exceeded` or `completed with undelivered notifications` — matching the family is more robust than an exact string. Empirical additions would have required ≥3 events of unambiguous noise; the sample had zero candidates meeting either condition.

**Real error families** (`TypeError`, `ReferenceError`, etc.) never enter `ignoreErrors` even when high-volume, by design — those are bugs, not noise. The two backend `FileNotFoundError` issues observed here would not have entered `ignoreErrors` even if they were frontend-originated, because the underlying path-missing error is signal worth surfacing.

## Recommendation: revisit after first organic traffic

Until 3d-portal serves real browser traffic, the empirical layer of this ruleset is necessarily empty. The first 30-day window post-traffic-activation is the correct moment to re-run this discovery:

- New `denyUrls` candidates likely emerge as users open the SPA from devices with browser extensions (ad blockers, password managers, dev tools) that inject scripts and throw — those throws will surface `chrome-extension://...` (or moz/safari analogs) in `request.url` and confirm the floor is doing its job, possibly extending it with specific extension-host URLs that prove especially noisy.
- New `ignoreErrors` candidates likely emerge as Safari and mobile browsers contribute their dialect-specific noise (`/Load failed/`, `/cancelled/`, `/AbortError/`).
- Re-running discovery is straightforward: copy this report's appendix command, replace the date stamp, observe the new top-25, append empirical patterns.

Per the brief's "every replacement keeps its predecessor as documented manual recovery" principle (and project-context.md observability rules), this discovery output is the **input contract** consumed by Story 2.4's `apps/web/src/instrument-filters.ts`. Re-running discovery is the canonical way to extend the ruleset; manual edits to `instrument-filters.ts` without a corresponding discovery refresh would drift the empirical floor away from observed reality.

## Appendix — sample queries used

```bash
# Source token + slugs from infra/.env (token never echoed)
set -a; source infra/.env; set +a

# Pre-flight reachability smoke (200 OK confirms LAN endpoint + token scope)
curl -sS -o /dev/null -w '%{http_code}\n' \
  --max-time 10 \
  -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "${GLITCHTIP_URL:-http://192.168.2.190:8800}/api/0/organizations/"

# 30-day issue list, top 100 by event count descending (snake_case sort key — camelCase 422s)
GT="${GLITCHTIP_URL:-http://192.168.2.190:8800}"
ORG="${GLITCHTIP_ORG_SLUG}"
PROJ="${GLITCHTIP_PROJECT_SLUG}"
curl -sS -D /tmp/gt-issues-30d.headers \
  -o /tmp/gt-issues-30d.json \
  --max-time 30 \
  -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GT/api/0/projects/$ORG/$PROJ/issues/?statsPeriod=30d&limit=100&sort=-count"

# Rank all issues by count descending (count is a string in JSON — cast via tonumber)
jq -r '
  sort_by(-(.count|tonumber))
  | to_entries[]
  | "\(.key+1)|\(.value.count)|\(.value.level)|\(.value.title)|\(.value.culprit // "—")|\(.value.lastSeen)"
' /tmp/gt-issues-30d.json

# Drill-down: single issue's latest event (REST schema = entries[] shape, NOT top-level event.exception)
curl -sS --max-time 10 \
  -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GT/api/0/issues/<ISSUE_ID>/events/latest/" \
  | jq '{
      title,
      exception_value: (.entries // [] | map(select(.type=="exception")) | .[0].data.values[0].value // "(none)"),
      request_url: (.entries // [] | map(select(.type=="request")) | .[0].data.url // "(none)")
    }'
```

## Sprint context

- **Story:** [2.1 — 30-Day GlitchTip Issue Discovery + Empirical Filter Ruleset](2-1-glitchtip-discovery-empirical-filter-ruleset.md)
- **Consumer:** [Story 2.4 — `instrument.ts` `beforeSend` Filter Contract](_bmad-output/planning-artifacts/epics.md) (paste-imports both arrays into `apps/web/src/instrument-filters.ts`)
- **Architecture pins:** AR6 (filter ordering), AR11 (discovery story), Decision H (`beforeSend` contract).
- **NFR pins satisfied:** S1 (token never echoed/logged/written here), S2 (read-only — only GET requests), I3 (Story 2.4 reads this layout literally).
