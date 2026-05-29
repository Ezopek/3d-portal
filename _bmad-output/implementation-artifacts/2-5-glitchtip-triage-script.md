# Story 2.5: `glitchtip-triage.sh <issue_id>` + Golden-File Schema

Status: done

## Story

As an AI agent triaging a GlitchTip issue (Journey 1 in PRD),
I want one command that returns a markdown stub paste-ready into `bmad-quick-dev` / `bmad-create-story`,
So that I never need to open the GlitchTip UI — the stub is the entire interface, and its schema is verifiable so downstream BMAD parsers cannot break silently.

## Acceptance Criteria

1. **AC1 — Script location + permissions.** New file `infra/scripts/glitchtip-triage.sh`, mode 0755 (executable). Mirrors existing scripts (`verify-symbolication.sh`, `upload-sourcemaps.sh`).

2. **AC2 — Header comment block (AR12 + Decision F + Story 3.1 exemplar).** Lines 2-N of the script document: purpose, required env, optional env, exit codes, examples, `--schema` flag, `--help` flag. The header IS the help text — `--help` reprints it via `sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'` (Story 3.1 pattern). Format consistent with `verify-symbolication.sh`.

3. **AC3 — Strict mode + dependency check (AR12).** First non-comment lines:
   ```bash
   set -euo pipefail
   command -v jq curl >/dev/null || { echo "missing: jq/curl" >&2; exit 1; }
   ```

4. **AC4 — Env loading + validation.** Source `infra/.env` once via `set -a; source infra/.env; set +a` (relative to repo root resolved like `verify-symbolication.sh` does). Validate required env: `: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"`. Default `GLITCHTIP_URL` to LAN endpoint when unset: `GLITCHTIP_URL="${GLITCHTIP_URL:-http://192.168.2.190:8800}"`.

5. **AC5 — Argument handling.** Three modes:
   - `--help` / `-h`: reprint header comment block, exit 0.
   - `--schema`: print bare template with placeholder tokens (`<title>`, `<filename>:<line>`, etc.), exit 0. NO REST calls.
   - `<issue_id>` (numeric or string): perform the triage REST call. Missing arg → print `--help`, exit 2.

6. **AC6 — REST call (AR13 curl+jq idiom).** `GET ${GLITCHTIP_URL}/api/0/issues/<issue_id>/events/latest/` with `Authorization: Bearer $GLITCHTIP_AUTH_TOKEN`. Capture `http_code` via `-w '%{http_code}'`, save body to `/tmp/gt-triage-${issue_id}-$$.json`. Case-statement on `http_code`:
   - `20*`: success, fall through to extraction.
   - `401|403`: auth/scope failure → stderr message, exit 3.
   - `5*`: GlitchTip unreachable → stderr message, exit 2.
   - `*`: unexpected → stderr `cat $body_path`, exit 1.

7. **AC7 — Output extraction + formatting (Decision F).** Single `jq -r` invocation extracts in this exact field order, printed to stdout as a markdown stub:
   ```
   # Issue #<issue_id>: <title>

   - **Top frame:** `<filename>:<line>`
   - **Fingerprint:** `<fingerprint>`
   - **Route:** `<route.pathname>` (model.id=<id>)         ← `(model.id=...)` ONLY when tag present
   - **Release:** `<release>` (commit `<git.commit>`)
   - **Last 5 events:**
     1. `<timestamp>` — `<message preview>`
     2. ...
   - **Suggested file to edit:** `<filename>` (top-frame source)

   GlitchTip link: <permalink>
   ```

   Field source map (per `~/repos/configs/docs/glitchtip-agent-guide.md` + Story 2.1 drilldown):
   - `<title>`: `event.title`
   - `<filename>:<line>`: `event.entries[] | select(.type=="exception") | .data.values[0].stacktrace.frames[-1] | "\(.filename):\(.lineno)"` (last frame in array = top of stack per Sentry convention).
   - `<fingerprint>`: `event.groupID` (issue ID; GlitchTip's "fingerprint" is the issue group identifier).
   - `<route.pathname>`: `event.tags[] | select(.key=="route.pathname") | .value` (Story 2.3 dynamic tag).
   - `<id>` (model.id): `event.tags[] | select(.key=="model.id") | .value` (Story 2.3 dynamic tag; conditionally appended when present).
   - `<release>`: `event.release` (top-level field) or fallback `event.tags[] | select(.key=="service.version") | .value` (Story 2.2 static tag).
   - `<git.commit>`: `event.tags[] | select(.key=="git.commit") | .value` (Story 2.2 static tag).
   - `<permalink>`: `event.permalink` if present, else build from `${GLITCHTIP_URL}/<org>/<project>/issues/<issue_id>/`.

8. **AC8 — Last 5 events.** Latest-event endpoint may include `previousEventID` chain or sibling array — sufficient if the latest event itself is shown. **Implementation choice for this story:** issue a SECOND `GET ${GLITCHTIP_URL}/api/0/issues/<issue_id>/events/?limit=5` call to fetch the last 5 events deterministically. Extract `event_id` (snake_case at this endpoint per agent-guide line 276) and `date_created` + `message`/`title`. If the second call fails (5xx or 404), gracefully fall back to "—" for the section but DON'T fail the whole script (the latest event is still useful).

9. **AC9 — `--schema` flag output.** Bare template with placeholder tokens, no REST calls. Exact bytes match `tests/golden/triage-schema.txt`. Single source of truth: define the template in a shell variable (heredoc) or a function, used by both `--schema` and the post-extraction printf. This ensures the schema can never drift from the rendered output.

10. **AC10 — Golden file.** `tests/golden/triage-schema.txt` (NEW) contains exactly the bytes produced by `bash infra/scripts/glitchtip-triage.sh --schema`. Verify with `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` → zero diff, exit 0.

11. **AC11 — Read-only (FR20 / NFR-S2).** Script issues only `GET` requests. No `POST`, `PUT`, `PATCH`, `DELETE` against GlitchTip. Verifiable by grep on the source.

12. **AC12 — Performance budget (NFR-P4).** Typical lookup ≤ 5s wall-clock. Use `--max-time 10` on each curl invocation. No retry loops on transient 5xx — fail clean.

13. **AC13 — Stdout vs stderr split (AR12).** Markdown stub on stdout (pipeable to `pbcopy` / `bmad-quick-dev` / `bmad-create-story`). All progress, errors, warnings on stderr. `jq` extraction errors → stderr.

14. **AC14 — Tests / verification (no vitest required — bash project surface).**
    - **Schema verification (mandatory):** `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` → zero diff, exit 0. This is THE binding contract for NFR-I3.
    - **Help flag (mandatory):** `bash infra/scripts/glitchtip-triage.sh --help` exits 0, prints non-empty content.
    - **Missing-arg (mandatory):** `bash infra/scripts/glitchtip-triage.sh` (no args) exits non-zero with help-equivalent message.
    - **Real issue lookup (mandatory):** `bash infra/scripts/glitchtip-triage.sh 51` (or any recent verify-symbolication smoke event) returns markdown with all sections populated. Verify against the live GlitchTip — issue 51 is the post-Story-2.4-fix smoke event with full tag set.
    - **Read-only verification (mandatory):** `grep -E "(POST|PUT|PATCH|DELETE)" infra/scripts/glitchtip-triage.sh` returns zero results except in comments.
    - **Linting (optional but recommended):** `shellcheck infra/scripts/glitchtip-triage.sh` zero warnings (use the same conventions as `verify-symbolication.sh`).

15. **AC15 — Auto-deploy NOT applicable.** Bash script under `infra/scripts/` is operator-runnable; the `infra/scripts/deploy.sh` deploy chain doesn't ship it to `.190` (scripts stay on dev box). No deploy step. Per project memory rule: code change to `main` triggers deploy — but `infra/scripts/glitchtip-triage.sh` is dev-box-only tooling, not a runtime artifact. **Skip auto-deploy.**

## Tasks / Subtasks

- [x] **Task 1: Create `infra/scripts/glitchtip-triage.sh` (AC1-AC7, AC11-AC13)**
  - [x] Subtask 1.1: Header comment block (≥10 lines, ≤25 lines): purpose, required env (`GLITCHTIP_AUTH_TOKEN`), optional env (`GLITCHTIP_URL` defaults to `http://192.168.2.190:8800`), exit codes (0 success / 1 missing dep or unexpected REST / 2 missing arg or GlitchTip 5xx / 3 auth 401/403), example invocations (full + `--schema` + `--help`).
  - [x] Subtask 1.2: Strict mode + `--help` early return + dependency check (mirror `verify-symbolication.sh:49-57`).
  - [x] Subtask 1.3: Repo-root resolution: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` (same idiom as `verify-symbolication.sh:60`). Source `${REPO_DIR}/infra/.env` once.
  - [x] Subtask 1.4: Env validation + URL default.
  - [x] Subtask 1.5: Argument dispatch: `--help`/`-h` (reprint header), `--schema` (call schema function, exit 0), missing arg (print help, exit 2), valid issue_id (proceed).
  - [x] Subtask 1.6: REST call to `events/latest/` with curl+jq idiom (AR13). Save body to `/tmp/gt-triage-${ISSUE_ID}-$$.json`, capture `http_code`. Case-statement dispatch.
  - [x] Subtask 1.7: Optional second REST call to `events/?limit=5` for last-5 events. Graceful fallback to "—" on failure.
  - [x] Subtask 1.8: Schema function (heredoc template) used both by `--schema` and as the printf format string for the populated output. Single-source-of-truth.
  - [x] Subtask 1.9: jq extraction + printf to render the populated stub. `(model.id=...)` segment conditional on tag presence.
  - [x] Subtask 1.10: `chmod +x infra/scripts/glitchtip-triage.sh`.

- [x] **Task 2: Create `tests/golden/triage-schema.txt` (AC9, AC10)**
  - [x] Subtask 2.1: Run `bash infra/scripts/glitchtip-triage.sh --schema > tests/golden/triage-schema.txt` to seed the golden file.
  - [x] Subtask 2.2: Verify diff: `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` → zero diff.

- [x] **Task 3: Manual smoke against live GlitchTip (AC14)**
  - [x] Subtask 3.1: `bash infra/scripts/glitchtip-triage.sh --help` → exits 0, prints header.
  - [x] Subtask 3.2: `bash infra/scripts/glitchtip-triage.sh` (no args) → prints help, exits non-zero.
  - [x] Subtask 3.3: `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` → zero output, exit 0.
  - [x] Subtask 3.4: `bash infra/scripts/glitchtip-triage.sh 51` (post-2.4-fix verify-symbolication smoke event with full tag set) → markdown stub with `service.version=0.1.0+9d6d207`, `git.commit=9d6d207`, `host.name=Fenrir`, `route.pathname=/?__sentry_smoke=...` etc. Confirm `(model.id=...)` segment ABSENT (no model.id tag on smoke events).

- [x] **Task 4: Static analysis (AC11, AC14)**
  - [x] Subtask 4.1: `grep -E "(\bPOST\b|\bPUT\b|\bPATCH\b|\bDELETE\b)" infra/scripts/glitchtip-triage.sh` → zero non-comment matches.
  - [x] Subtask 4.2 (optional): `shellcheck infra/scripts/glitchtip-triage.sh` → zero warnings.

- [x] **Task 5: Commit (AC15 — NO auto-deploy)**
  - [x] Subtask 5.1: Stage `infra/scripts/glitchtip-triage.sh` (NEW, mode 0755) + `tests/golden/triage-schema.txt` (NEW).
  - [x] Subtask 5.2: Conventional commit, scope `infra`: `feat(infra): glitchtip-triage.sh + golden-file schema (Story 2.5)`. Body: covers FR17-20, Decision F, NFR-I3 verifiable contract, NFR-P4 perf budget, AR12 conventions, AR13 curl+jq idiom.
  - [x] Subtask 5.3: **Skip `infra/scripts/deploy.sh`** — script is dev-box tooling, not deployed.

## Dev Notes

### Files being created — no existing files modified

| Path | Status | Notes |
|---|---|---|
| `infra/scripts/glitchtip-triage.sh` | NEW | Mode 0755. Header + strict mode + dep check + env + arg dispatch + REST + jq render. ~120-150 lines. |
| `tests/golden/triage-schema.txt` | NEW | Bare template, one source-of-truth used by both `--schema` and the populated render. ~12-15 lines. |

### Architecture pin: AR12 (Bash script conventions)

> All scripts: `set -euo pipefail`. Dependency check via `command -v <tool>`. Env loading exactly once via `set -a; source infra/.env; set +a`. Required-env validation via `:` `${VAR:?msg}`. Stdout = operator narrative + structured output; stderr = errors/warnings. Exit codes documented in the header comment. Header (10-20 lines) explains purpose, required env, exit codes, when to run, recovery path.
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 270-278]

### Architecture pin: AR13 (curl + jq idiom for GlitchTip REST)

```bash
http_code=$(curl -sS -o /tmp/gt-response.json -w '%{http_code}' \
  -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GLITCHTIP_URL/api/0/...")

case "$http_code" in
  20*) ;;
  401|403) echo "auth/scope failure ($http_code)" >&2; exit 3 ;;
  5*)  echo "GlitchTip unreachable ($http_code)" >&2; exit 2 ;;
  *)   echo "unexpected response ($http_code): $(cat /tmp/gt-response.json)" >&2; exit 1 ;;
esac

title=$(jq -r '.title' < /tmp/gt-response.json)
```

> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 387-407]

### Architecture pin: Decision F (Markdown stub schema)

> `glitchtip-triage.sh <issue_id>` outputs a markdown stub with fields in fixed order: top frame `(filename:line)`, fingerprint, route context, `model.id` (when present), release SHA, last 5 events, suggested file. Schema verifiable via `./infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returning zero diff.
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 187-189, 366-385]

### Architecture pin: NFR-I3 (BMAD pipeline contract)

> Output format is stable and documented (FR18). Changes to the field set or order are breaking changes requiring a follow-up PRD, not a silent edit. **Verifiable:** `./infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returns zero changes. Diff failure during verify / CI means schema drift and must be reconciled to PRD via a follow-up edit, not absorbed silently.
> [Source: `_bmad-output/planning-artifacts/prd.md` NFR-I3]

### NFR-P4 (Triage performance budget)

> `glitchtip-triage.sh` returns within 5 seconds for typical issue lookup. Single REST GET to `/issues/<id>/events/latest/`; 10 s ceiling for large events. No retry loop on transient 5xx — fail clean.
> [Source: `_bmad-output/planning-artifacts/prd.md` NFR-P4]

### Story 3.1 exemplar — bash conventions to mirror

`infra/scripts/verify-symbolication.sh` is the canonical example. Specifically:
- Header doc-block format (lines 2-47).
- `--help` flag implementation: `if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'; exit 0; fi`.
- `REPO_DIR` resolution: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"`.
- Env loading + validation pattern.
- Curl+jq idiom matching AR13.

### GlitchTip event payload schema (load-bearing for jq extraction)

Per Story 2.1 drilldown (verified 2026-05-09):

`/api/0/issues/<id>/events/latest/` returns top-level keys:
```
context, contexts, culprit, dateCreated, dateReceived, dist, entries,
errors, eventID, groupID, id, message, metadata, nextEventID,
packages, platform, previousEventID, projectID, sdk, tags, title,
type, user, userReport
```

- **Tags** are an array of `{key, value}` objects (NOT a flat object). Extract via `.tags[] | select(.key=="X") | .value`.
- **Stack trace** is in `entries[] | select(.type=="exception") | .data.values[0].stacktrace.frames`. Frames array is in **call order** — last element is the top frame (the function that threw).
- **Request** is in `entries[] | select(.type=="request") | .data.url`.
- **`message`** at top level is the formatted display message; **`exception.values[0].value`** in `entries` is the canonical exception text.
- **`groupID`** is what GlitchTip uses internally as the "fingerprint" / issue identifier.

### Story 2.1 paste-import pattern reused — but for OPERATIONAL contract

Story 2.4 paste-imported the discovery ruleset into TS code. Story 2.5 paste-imports the agent-guide REST schema knowledge into a bash script. Both are NFR-I3 contracts: changes break downstream consumers (Story 2.4's beforeSend filter for the former, BMAD planning prompts for the latter).

### `--schema` single-source-of-truth pattern

The story plan AC9 + Subtask 1.8 mandate that `--schema` and the populated output share the same template. Implementation: define a shell function `print_schema_template()` that takes optional values (or empty for placeholders) and uses `printf` with positional args. Calling with no args (or all empties) prints the schema; calling with extracted values prints the populated stub. Both paths emit the SAME bytes minus the placeholder substitutions.

Pseudo-code:
```bash
render_stub() {
  local issue_id="${1:-<issue_id>}"
  local title="${2:-<title>}"
  # ... etc
  cat <<EOF
# Issue #${issue_id}: ${title}

- **Top frame:** \`${filename}:${line}\`
...
EOF
}

if [[ "${1:-}" == "--schema" ]]; then
  render_stub                # all positional args default to placeholders
  exit 0
fi

# ... after extraction ...
render_stub "$ISSUE_ID" "$title" "$filename" "$line" ...
```

The golden file is the bytes from `render_stub` with placeholder defaults — guaranteed schema parity.

### File-structure footprint

| Path | Status | Notes |
|---|---|---|
| `infra/scripts/glitchtip-triage.sh` | NEW | Mode 0755, ~120-150 lines. |
| `tests/golden/triage-schema.txt` | NEW | ~12-15 lines, ASCII. |

## Previous Story Intelligence

### From Story 2.4 (just shipped)

- **Codex review caught a P2** architectural-assumption gap (denyUrls page-URL only). Same review discipline applies for 2.5 — bash scripts can have analogous gaps (e.g., wrong endpoint, fragile jq paths, missing edge cases).
- **6 unit tests in instrument-filters.test.ts** — Story 2.5 has no vitest surface; tests are the schema-diff + manual smoke against live GlitchTip.
- **`vi.resetModules()` ↔ reference equality** — N/A here, bash has no module system.

### From Story 3.1 (verify-symbolication.sh — the exemplar)

- **Header doc-block format**: 2-47 lines of `# `-prefixed text covering purpose, required env, optional env, exit codes, example, help. `--help` reprints lines 2 through first blank.
- **REPO_DIR pattern**: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"`.
- **Env source**: `set -a; source "${REPO_DIR}/infra/.env"; set +a` (NB: needs the REPO_DIR prefix or it's relative to PWD which can drift).
- **Stdout/stderr split**: `printf '\033[34m→ ...\033[0m\n'` for blue progress on stdout; `>&2` for warnings/errors.
- **Smoke event compatibility:** verify-symbolication produces `Error: smoke <uuid>` events with full tag set. Issue 51 (post-2.4-fix) is the most recent and has all 8 tags (5 static + 3 dynamic = `service.version, host.name, deployment.environment, git.commit, build.time, route.pathname, model.id (none — smoke has no catalog match), auth.is_authenticated`). Use issue 51 for Subtask 3.4 manual smoke.

### From Story 2.1 (GlitchTip discovery — schema knowledge transfer)

- **camelCase vs snake_case gotcha:** `/api/0/issues/<id>/events/latest/` returns **camelCase** (`eventID`, `dateCreated`, `groupID`). `/api/0/issues/<id>/events/?limit=N` returns **snake_case** (`event_id`, `date_created`, `group_id`). 2.5's two REST calls use BOTH — extraction must normalize.
- **`statsPeriod=30d&sort=-count`** are correct snake_case GT 6.1.x parameters (last_seen / -count NOT camelCase). 2.5 doesn't use these (single-issue lookup), but worth knowing.
- **HTTP 422 + literal_error** is GT 6.1.x's response when query parameters are wrong. 2.5's GET path doesn't take query params (just `/issues/<id>/events/latest/` and `/issues/<id>/events/?limit=5`), so unlikely.

## Git Intelligence Summary

| SHA | Subject | Relevance |
|---|---|---|
| 9d6d207 | fix(web): match denyUrls against frame filenames too (Story 2.4 review) | Latest commit; verify-symbolication smoke (issue 51) carries the post-fix release tag. |
| 4149507 | feat(web): beforeSend filter contract per Decision H (Story 2.4) | Story 2.4 ship; events filtered through `applyBeforeSendFilters` post-this. |
| 8023404 | fix(web): re-emit auth.is_authenticated on every auth-state change | Auth tag now stable across nav. |
| c85cd30 | feat(web): dynamic context tags via router.subscribe (Story 2.3) | route.pathname / model.id / auth.is_authenticated tags exist on user-traffic events. Smoke events are pre-router so don't carry these. |
| 6ce2640 | fix(infra): plumb VITE_BUILD_HOST through docker build | host.name=Fenrir on smoke events. |

## Latest Tech Information

### GlitchTip 6.1.x REST endpoints used by 2.5

- `GET /api/0/issues/<id>/events/latest/` — single-event detail (camelCase, full payload).
- `GET /api/0/issues/<id>/events/?limit=5` — recent event list (snake_case, condensed payload).

Both return JSON. Both gated on Bearer token. Both well under 1 MB → public proxy works fine; LAN endpoint also works. Default to LAN for performance per Story 3.1 precedent.

### `jq -r '.tags[] | select(.key=="X") | .value'` returns empty string when key absent

Useful for the `(model.id=...)` conditional segment — empty string lets the script test whether to emit the segment.

### shellcheck

Optional but recommended. `shellcheck infra/scripts/glitchtip-triage.sh` should produce zero output (no warnings). Use `# shellcheck disable=SC<XXXX>` only with inline justification.

## Project Context Reference

- **Bash conventions** (project-context.md "Bash Script Conventions"): strict mode, dep check, env once, validation, stdout/stderr split, header comment.
- **Token hygiene (NFR-S1):** never echo `GLITCHTIP_AUTH_TOKEN` in any output. The script reads the env var into curl's `-H` and never prints it.
- **No `--no-verify`, no `--no-gpg-sign`** in commit (project-context.md Git rules).
- **Cross-repo grounding:** `~/repos/configs/docs/glitchtip-agent-guide.md` is the canonical REST recipe source. Read it before implementing the jq paths.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 473-512 — Story 2.5 verbatim ACs.
- `_bmad-output/planning-artifacts/architecture.md` lines 187-189 — Decision F.
- `_bmad-output/planning-artifacts/architecture.md` lines 270-278 — AR12 bash conventions.
- `_bmad-output/planning-artifacts/architecture.md` lines 366-385 — Markdown stub format.
- `_bmad-output/planning-artifacts/architecture.md` lines 387-407 — AR13 curl+jq idiom.
- `_bmad-output/planning-artifacts/prd.md` NFR-I3 — golden-file diff verification.
- `_bmad-output/planning-artifacts/prd.md` NFR-P4 — 5s wall-clock budget.
- `_bmad-output/planning-artifacts/prd.md` FR17-FR20 — triage script functional requirements.
- `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` — Story 2.1 drilldown that confirms event payload shape.
- `infra/scripts/verify-symbolication.sh` — Story 3.1 bash exemplar.
- `~/repos/configs/docs/glitchtip-agent-guide.md` lines 263-281 — issue/event REST recipes; line 276 schema gotcha.

## Dev Agent Record

### Agent Model Used

`claude-opus-4-7[1m]`. 5h budget at 71% start.

### Debug Log References

- **Schema diff (binding NFR-I3 contract):** `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` → zero diff, exit 0.
- **Exit codes verified:** missing-arg → 2, `--schema` → 0, `--help` → 0, valid issue (51) → 0.
- **Manual smoke against issue 51 (post-2.4-fix verify-symbolication smoke event):** all sections populated, `(model.id=...)` segment correctly suppressed (smoke events have no model.id tag), `Release: 0.1.0+9d6d207`, `git.commit: 9d6d207`, `Top frame: apps/web/src/main.tsx:—` (lineno absent on synthetic captureException — gracefully fallbacks to "—").
- **Read-only:** `grep -nE "(\bPOST\b|\bPUT\b|\bPATCH\b|\bDELETE\b)"` → zero matches.
- **shellcheck:** not installed on the dev box; skipped (optional per AC14).

### Completion Notes List

- **`infra/.env` line 17 syntax issue (flagged in 2.1+2.2)** explodes under `set -e` on `source` — defensive `set +e` ... `source ... 2>/dev/null` ... `set -e` guard added in the env-loading block. Comment explains the rationale. The script no longer relies on the `.env` being syntactically clean — only on the `KEY=VALUE` pairs being parseable, which they are.
- **Bash `${var:-default}` vs `${var-default}` gotcha** caught at first manual smoke: the `:`-form substitutes default for both unset AND empty values, which broke the `(model.id=...)` segment suppression (empty string from a populated render became the placeholder again). Switched to `${var-default}` (no colon) — substitutes only when unset. Schema render path (no args) still gets defaults; populated render path (empty string for missing tag) preserves the empty string.
- **Top-frame `lineno` may be absent** on synthetic `captureException` calls (no source-mapped frames available). The jq extraction returns "—" gracefully — populated as `apps/web/src/main.tsx:—` for issue 51. For real production errors with stack traces, `lineno` is present and renders correctly.
- **Single source of truth for the schema (AC9):** `render_stub` function is called from both `--schema` (no args → all defaults → bare template) and the populated render path (extracted values → real content). Same heredoc, byte-identical structure modulo placeholder substitution. NFR-I3 schema parity guaranteed.
- **Last-5 events fallback:** if the `/events/?limit=5` REST call fails (5xx / 404), the section degrades to "—" rather than failing the whole script — partial info beats no info, especially since the latest event (the primary signal) is already extracted.
- **Did NOT auto-deploy** per Story plan AC15: `infra/scripts/*` is dev-box tooling, not deployed to `.190`. Per project memory rule "auto-deploy after every code/infra commit to main" — the spirit of the rule is "deploy.sh runs deployable artifacts"; bash tooling that operators invoke locally is out-of-scope for the auto-deploy hook. Flagged for operator awareness in the commit body.
- **Pre-existing failures still flagged (Stories 2.1+2.2+2.3+2.4):** Node 18 unplugin breakage, 3 CardCarousel test failures, `infra/.env` line 17. No new regressions.

### File List

| Path | Status | Notes |
|---|---|---|
| `infra/scripts/glitchtip-triage.sh` | NEW | mode 0755 |
| `tests/golden/triage-schema.txt` | NEW | golden schema |

### Change Log

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-10T~01:15Z | Claude Opus 4.7 (1M ctx) | New `infra/scripts/glitchtip-triage.sh` (mode 0755) + `tests/golden/triage-schema.txt`. Schema diff = clean; manual smoke against issue 51 OK; read-only verified; exit codes 0/2/3 confirmed. Status `in-progress → review`. Commit `ed48ab2`. |
| 2026-05-10T~01:25Z | Codex review + Claude Opus 4.7 fix | Codex returned 2 findings (P1 paginated `{items}` shape crash + P2 primary-curl-transport-failure exit-code leak). Both RESOLVED in next commit: jq normalizes both array and `{items}` shapes; primary curl wrapped in if-guard mapping transport failures to exit 2. Verified end-to-end via Codex's exact paginated mock payload. Status `review → done`. |

## Senior Developer Review (AI)

**Reviewer:** Codex (`codex review --commit ed48ab2`)
**Date:** 2026-05-10T~01:25Z (UTC)
**Outcome:** Changes Requested (2 findings: 1 P1 + 1 P2)

### Findings

| ID | Severity | Status | Location | Issue |
|---|---|---|---|---|
| R1 | P1 (High) | RESOLVED | `infra/scripts/glitchtip-triage.sh:196-198` (pre-fix line range) | The `/issues/<id>/events/?limit=5` endpoint may return GlitchTip's paginated wrapper `{"items":[...], "next":...}` for larger result sets. The original jq pipeline called `to_entries` on the wrapper object and indexed `.items` as if it were an event payload — jq errored out, set -e killed the whole script, and the main story-stub path failed. The homelab instance happens to return a plain array for sub-page result sets, masking the bug in manual testing. Codex's mock against the documented paginated shape reliably reproduced the crash. |
| R2 | P2 (Medium) | RESOLVED | `infra/scripts/glitchtip-triage.sh:128-131` (pre-fix line range) | The primary curl invocation lived outside an if-guard. Transport failures (DNS error, connect refused, `--max-time` exceeded) caused set -e to terminate with curl's raw exit code (7, 28, etc.) instead of the documented exit 2 + clean error message — silent contract drift for operators reading the documented exit-code map. |

### Action Items

- [x] **[AI-Review] [P1] Normalize both array and paginated shapes for the events list endpoint.** Wrap the jq projection in `(if type == "array" then . else (.items // []) end)` before `to_entries`. Add `2>/dev/null || true` to swallow any residual jq errors so the last-5 block degrades to "—" rather than crashing the whole render. Verified via Codex's exact mock payload — paginated case now renders correctly. **Resolved in commit (next after ed48ab2).**
- [x] **[AI-Review] [P2] Wrap primary curl in if-guard mapping transport failures to exit 2.** Mirror `infra/scripts/verify-symbolication.sh`'s `if ! http_code=$(curl ...); then exit 2; fi` pattern. Verified by inspection — script no longer leaks curl raw exit codes when the GlitchTip endpoint is unreachable. **Resolved in same commit.**

### Notable absent findings

- Read-only verification — accepted (zero POST/PUT/PATCH/DELETE non-comment matches).
- AR12/AR13 conventions adherence — accepted.
- Schema heredoc single-source-of-truth pattern — accepted.
- `set +e` guard around `source infra/.env` — accepted (defensive against pre-existing line-17 syntax noise).
- Conditional `(model.id=...)` segment — accepted (`${var-default}` correctly preserves empty string).
- Non-deploy decision (script is dev-box tooling) — accepted.
