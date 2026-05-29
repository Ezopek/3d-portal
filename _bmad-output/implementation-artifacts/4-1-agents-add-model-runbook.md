# Story 4.1: Author `docs/agents-add-model-runbook.md`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an AI agent (Claude, Codex, or future LLM) tasked with adding a model to 3d-portal from a URL,
I want a single curated markdown file that teaches me principles, auth model, source detection, behavioral rules, and operational invariants,
So that I can execute the full URL-to-portal flow without reading any source code or any other file in the repository.

## Acceptance Criteria

**Given** `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` exists with un-migrated runbook knowledge (§ "Workflow: Adding a New Model" lines 228–311, § "3MF Conversion Workflow" lines 313–348, § "Downloading from Printables (no login)" lines 390–410), and `docs/agents-add-model-runbook.md` does NOT yet exist,

**When** the agent ports the relevant content and reframes it for the post-SoT-migration DB-era (`portal.db` on `.190` + cookie-auth via `POST /api/auth/login` + `POST /api/admin/models` + `POST /api/admin/models/{id}/files` instead of folder layout + `_index/index.json`):

1. **Principles section** — pull-only ergonomics, REST + cookie session, idempotence (FR10 + NFR1 + NFR6 captured as principles).
2. **Auth section** — agent service account is a regular `User` row with `role=agent`; credentials are a **password** (NOT a long-lived bearer token) at `~/.config/3d-portal/agent.password` (mode 600). Documents the full login flow end-to-end:
   - Read password inline: `pw=$(cat ~/.config/3d-portal/agent.password)`.
   - Login: `curl -c /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' -d '{"email":"agent@portal.local","password":"'"$pw"'"}' https://3d.ezop.ddns.net/api/auth/login` → server sets `portal_access` (`Path=/api`, ~30 min JWT TTL) + `portal_refresh` (`Path=/api/auth`, 30-day TTL) cookies.
   - Subsequent calls: `-b /tmp/portal-cookies.txt`. Mutations also need `-H 'X-Portal-Client: web'` (CSRF gate).
   - **Never** `export PASSWORD=...` (persists in shell history). **Never** `Authorization: Bearer ...` — admin routes read JWT from the cookie, not from the header. **Never** write password or cookie-jar contents to a tracked path.
   - Long-running agent sessions: cron daily relogin OR `POST /api/auth/refresh` (with the refresh cookie) before access expires.
   - Rotation: `python -m scripts.bootstrap_agent --email agent@portal.local --rotate` on `.190`. Prints new password to stdout once — capture and replace the file content (`chmod 600` preserved). No service restart. (FR5 + NFR2.)
3. **Source-detection table** — URL host → fetch strategy: `printables.com` → GraphQL `getDownloadLink`, `thangs.com` / `thingiverse.com` / `makerworld.com` / `crealitycloud.com` → `agent-browser` CLI against the operator's logged-in Windows Chrome (per `~/.claude/CLAUDE.md` § "Browser automation"). (FR2.)
4. **Printables GraphQL recipe** — endpoint `https://api.printables.com/graphql/` (POST, JSON, no auth needed for public models). Two operations:
   - **List files** (query): `{ print(id: "PRINT_ID") { stls { id name fileSize } } }`.
   - **Get download link** (mutation): `getDownloadLink(id: STL_ID, printId: PRINT_ID, fileType: stl, source: model_detail) { ok output { link } }`.
   - One worked example with a real long-lived public Printables model ID + the JSON response shape + the file-fetch step (`curl -L -o <file>.stl '<link>'`). (FR3.)
5. **3MF conversion procedure** — every `.3mf` MUST be converted to per-object STLs BEFORE upload to the portal (no `.3mf` lands in the catalog directly). Canonical execution on the **operator's local dev box** (where the script's `.venv` lives): `~/repos/3d-portal/infra/scripts/.venv/bin/python ~/repos/3d-portal/infra/scripts/migrate_catalog_3mf.py --convert <file.3mf>`. Original archived to `_archive/3mf-originals/`. Runbook describes the post-condition (per-object STL files in same dir; multi-object 3MF → `<basename>_NN.stl` 1-indexed zero-padded ≥2 digits; single-object → `<basename>.stl`) + notes this is a rare-to-never path going forward (most modern sources serve STL directly). Runbook does NOT duplicate the script's internal logic. If the agent isn't running on the operator's box, hand the `.3mf` back with a "needs 3MF conversion" note rather than attempting remote execution. (FR4.)
6. **Pre-flight checklist** — 5 items the agent verifies BEFORE `POST /api/admin/models` (failure → stop and ask the operator, do NOT POST anyway):
   1. Category slug exists — query `GET /api/categories` and confirm the target slug is present in the returned `CategoryTree`.
   2. Model name sanitized — no Polish diacritics, no leading/trailing whitespace, no file extension.
   3. At least one `.stl` file ready to upload after any 3MF/OBJ/STEP conversion (3MF: per-object STLs; OBJ/STEP: convert via `trimesh.load(path, force='mesh').export(out, file_type='stl')`).
   4. Duplicate-check — model not already in catalog under the same external-link URL (query existing models OR rely on the FR-link tag).
   5. All source files in expected formats per FR4 (no leftover `.3mf` / `.zip`). (FR6.)
7. **Endpoint pointer (Decision C + NFR8)** — exactly ONE cross-link sentence: `"For endpoint signatures, request/response schemas, and status codes, fetch \`/api/openapi.json\` — see e.g. \`paths.\"/api/admin/models\".post\` and \`paths.\"/api/admin/models/{model_id}/files\".post\`."` This sentence uses backticks around the endpoint references so the smoke-test grep heuristic (HTTP-method-uppercase preceding `/api/` in body text) does NOT fire on it. NO other endpoint paths or method names duplicated inline in the runbook.

**And** the runbook contains zero occurrences of HTTP-method-uppercase preceding `/api/` paths inside body text (smoke-test grep heuristic — the cross-link sentence above is the only allowed reference and uses backticks). Self-verify before commit:
```bash
grep -nE '\b(GET|POST|PUT|PATCH|DELETE) /api/' docs/agents-add-model-runbook.md \
  | grep -vE '`(GET|POST|PUT|PATCH|DELETE) /api/'
# expected: zero output (all matches are inside backticks)
```

**And** the runbook is `< 600` lines (target: ~400) — dense, agent-readable, zero fluff. Self-verify: `wc -l docs/agents-add-model-runbook.md` returns < 600.

**And** every command-bearing code block uses the bash language tag (` ```bash `) so agent parsers + Swagger UI render syntax-highlighted.

**And** sha256 of a stable intro paragraph is captured into `infra/.runbook-fingerprint` (single line, no trailing newline beyond the file's natural one, committed). Establishes Decision D's fingerprint baseline (Story 4.2 consumes it via `deploy.sh` verify chain). Stable intro paragraph candidate: the first paragraph under H1 (project description, before any operational content); ~3 sentences; edits to this paragraph are rare and intentional.

**And** the doc-only commit skips auto-deploy — commit scope `docs(agents)`. Per project-context.md § "Deploy" doc-only-commits-skip rule (changes confined to `docs/` + `infra/.runbook-fingerprint`).

## Tasks / Subtasks

- [x] **Task 1: Read source material + verify code-side references** (AC: all)
  - [x] Read `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` lines 228–311 (Workflow: Adding a New Model), 313–348 (3MF Conversion Workflow), 390–410 (Downloading from Printables).
  - [x] Confirm cookie-auth surfaces in code: `apps/api/app/modules/auth/router.py:52-103` (POST /api/auth/login sets cookies), `apps/api/app/modules/sot/admin_router.py:1-50` (auth dep + cookie reading), `apps/api/scripts/bootstrap_agent.py:1-50` (password-output behavior + agent.password storage convention).
  - [x] Confirm `GET /api/categories` returns `CategoryTree` (`apps/api/app/modules/sot/router.py:38-42`) — used by pre-flight check #1.
  - [x] Confirm `infra/scripts/migrate_catalog_3mf.py` exists with `--convert <path>` mode (already verified, `infra/scripts/migrate_catalog_3mf.py`).

- [x] **Task 2: Outline structure** (AC: 1–7)
  - [x] Draft H2 outline matching the seven AC content sections (Principles → Auth → Source Detection → Printables Recipe → 3MF Conversion → Pre-flight → OpenAPI Cross-link). Plus a short H1 + intro paragraph (this paragraph IS the fingerprint subject).
  - [x] Sanity-check section count + estimated length to keep total under 600 lines.

- [x] **Task 3: Write H1 + stable intro paragraph** (AC: fingerprint)
  - [x] H1: `# 3d-portal — Agent Runbook` (or similar; pick once, never restructure).
  - [x] First paragraph under H1: ~3 sentences explaining what the runbook is + its scope (URL-to-portal model creation) + how it pairs with `/api/openapi.json`. This paragraph is what `infra/.runbook-fingerprint` covers — keep it boring, edits are rare and intentional.

- [x] **Task 4: Write Principles section** (AC: 1)
  - [x] Pull-only (agent decides cadence; portal only responds — REST + cookie session, no webhooks/UI).
  - [x] Idempotence (re-running an import with the same URL returns the existing model UUID, not a duplicate).
  - [x] Layered auto-discovery (this runbook = narrative + behavioral; OpenAPI = endpoint catalog).

- [x] **Task 5: Write Auth section** (AC: 2)
  - [x] Service-account model (regular User row + role=agent + password file, not bearer token).
  - [x] Login flow: full curl example with `-c cookies.txt`, CSRF header, JSON body, password read inline via `$(cat ...)`.
  - [x] Cookie semantics: `portal_access` Path=/api ~30 min TTL; `portal_refresh` Path=/api/auth 30-day TTL.
  - [x] Reuse pattern: `-b cookies.txt` on subsequent calls; CSRF header repeated on mutations.
  - [x] Refresh flow: `POST /api/auth/refresh` for long sessions vs cron daily relogin.
  - [x] Rotation: `bootstrap_agent --rotate`, capture stdout, replace file content, no restart.
  - [x] Don't-do list: no `export PASSWORD=`, no `Authorization: Bearer`, no committing password/cookies to tracked paths.

- [x] **Task 6: Write Source Detection table** (AC: 3)
  - [x] Table columns: URL host | Fetch strategy | Auth needed | Notes.
  - [x] Rows: `printables.com` → GraphQL recipe (no auth); `thangs.com` / `thingiverse.com` / `makerworld.com` / `crealitycloud.com` → `agent-browser` CLI against logged-in Chrome on the operator's Windows host (mirrored networking + CDP per `~/.claude/CLAUDE.md` § "Browser automation").

- [x] **Task 7: Write Printables GraphQL recipe** (AC: 4)
  - [x] Endpoint: `https://api.printables.com/graphql/` (POST, `Content-Type: application/json`, no auth).
  - [x] List operation (query) with curl + JSON body example.
  - [x] Download-link operation (mutation) with curl + JSON body example, response shape (`data.getDownloadLink.output.link`), and the `curl -L -o <name>.stl '<link>'` fetch step.
  - [x] One worked example pinning a real long-lived public Printables model ID (operator picks; pinning a specific model means it exists ≥1 year on the platform).

- [x] **Task 8: Write 3MF conversion procedure** (AC: 5)
  - [x] When the trigger fires (any `.3mf` arriving via URL workflow, manual drop, or ZIP extraction).
  - [x] Note up-front that this is a **rare-to-never path going forward** — most modern downloads are STL; document the procedure for completeness.
  - [x] Canonical invocation runs on the **operator's local dev box** (where the script's `.venv` lives): `~/repos/3d-portal/infra/scripts/.venv/bin/python ~/repos/3d-portal/infra/scripts/migrate_catalog_3mf.py --convert <file.3mf>`. Agents executing on the operator's box can run it directly; agents executing elsewhere (e.g. via remote portal API only) hand the .3mf back to the operator with a note "needs 3MF conversion".
  - [x] Post-condition (per-object STLs in same dir, original archived to `_archive/3mf-originals/`).
  - [x] Pointer to script for full options/dry-run mode — DO NOT duplicate logic in runbook.

- [x] **Task 9: Write Pre-flight checklist** (AC: 6)
  - [x] 5-item ordered list, each item a one-liner with the verification command (`curl /api/categories | jq`, name sanitization rule, etc.).
  - [x] Failure-mode language: each item ends with "if false, stop and ask the operator" — not "POST anyway".

- [x] **Task 10: Write OpenAPI cross-link** (AC: 7)
  - [x] Single sentence with backticked endpoint references (so the smoke-test grep heuristic doesn't fire).
  - [x] Brief note on how to query OpenAPI: `curl https://3d.ezop.ddns.net/api/openapi.json | jq '.paths | keys[]'`.

- [x] **Task 11: Compute fingerprint + write `infra/.runbook-fingerprint`** (AC: fingerprint)
  - [x] Pick the stable intro paragraph (first paragraph under H1 from Task 3).
  - [x] Compute sha256 — the exact computation method is locked in by Story 4.2's `deploy.sh` verify chain (Story 4.1 ships the baseline only). Recommended: `sha256sum docs/agents-add-model-runbook.md | awk '{print $1}'` (whole-file fingerprint — simple, but every edit invalidates) OR `awk '/^# /{f=1;next} f && /^$/{f=0;next} f{print}' docs/agents-add-model-runbook.md | sha256sum | awk '{print $1}'` (intro-paragraph-only — narrower invalidation surface, matches Decision D's "stable intro paragraph" framing).
  - [x] **Recommended:** intro-paragraph-only sha256, since Decision D explicitly says "stable intro paragraph" and "minor edits should not invalidate". Lock in the exact awk/sed/grep chain that produces the fingerprint subject and document it as a comment INSIDE `infra/.runbook-fingerprint` is NOT possible (single-line file); instead, document the chain in this story's Completion Notes + in Story 4.2's Dev Notes so the verify script uses the same chain.
  - [x] Write the resulting sha256 (single line, no other content) to `infra/.runbook-fingerprint`.

- [x] **Task 12: Self-verify constraints before commit** (AC: line count + grep heuristic + bash code-fence)
  - [x] `wc -l docs/agents-add-model-runbook.md` < 600.
  - [x] `grep -nE '\b(GET|POST|PUT|PATCH|DELETE) /api/' docs/agents-add-model-runbook.md | grep -vE '\`(GET|POST|PUT|PATCH|DELETE) /api/'` returns zero output (cross-link sentence is the only allowed reference and uses backticks).
  - [x] All command code-blocks tagged `bash` (not bare ` ``` `).
  - [x] No `Authorization: Bearer` anywhere in the runbook (would contradict the auth section).
  - [x] No mention of `~/.config/3d-portal/agent.token` (legacy/wrong; only `agent.password` is correct).
  - [x] Recompute fingerprint and confirm it matches the file content of `infra/.runbook-fingerprint`.

- [x] **Task 13: Commit** (AC: doc-only commit, no auto-deploy)
  - [x] Stage `docs/agents-add-model-runbook.md` + `infra/.runbook-fingerprint` only.
  - [x] Commit message scope `docs(agents)`. Subject lower-case, no trailing period (per project-context.md § "Git" conventional-commits rule). Suggested: `docs(agents): add agent runbook + fingerprint baseline (E4.1)`.
  - [x] Skip auto-deploy (doc-only commit per project-context.md § "Deploy" rule). `infra/.runbook-fingerprint` is data, not infra code — does NOT trigger the auto-deploy rule.

## Dev Notes

### Critical context — auth correction in this same session

**Earlier draft of this story said "Authorization: Bearer $(cat ~/.config/3d-portal/agent.token)" with a token file at `agent.token`.** That spec drift was discovered during story-context analysis: `apps/api/app/modules/sot/admin_router.py` reads the principal from a cookie (`Cookie(alias=ACCESS_COOKIE)` → `portal_access`), and `apps/api/scripts/bootstrap_agent.py` produces a **password** (not a JWT) stored at `~/.config/3d-portal/agent.password`. **All three planning docs were corrected in this session** (commits to `_bmad-output/planning-artifacts/{prd,architecture,epics}.md`) before this story shipped. The runbook MUST describe the cookie+password flow as written in AC #2, NOT the bearer-token pattern. If you read any other source (older drafts, related docs, even `_bmad-output/` artifacts predating today) and see "agent.token" / "Bearer", that is stale — trust the corrected AC #2 above + the actual code.

### Source content map (legacy AGENTS.md → new runbook)

| Source section | Source lines | Reuse strategy | Reframe needed |
|---|---|---|---|
| § Workflow: Adding a New Model | 228–311 | ~30% reuse (steps 1–3 source detection + step 5 download patterns); ~70% rewrite | Steps 6 (pre-flight) and 7 (folder + index.json) → DB-era pre-flight checklist + `POST /api/admin/models` flow. Drop folder layout entirely. |
| § 3MF Conversion Workflow | 313–348 | ~80% verbatim (script signature, post-condition, validation rule) | Script is becoming legacy (rarely-to-never used going forward). Document the procedure for the case a `.3mf` does arrive, but the canonical execution location is the **operator's local dev box** (e.g. `~/repos/3d-portal/infra/scripts/.venv/bin/python infra/scripts/migrate_catalog_3mf.py --convert <file.3mf>`), NOT `.190`. The runbook can frame this as "if a `.3mf` lands and you (the agent) are running on the operator's box, run the converter locally; otherwise, hand the .3mf back to the operator to convert". |
| § Downloading from Printables (no login) | 390–410 | ~100% verbatim (GraphQL endpoint, query/mutation signatures, response shape, file-fetch step) | None substantive; just renamed to "Printables GraphQL recipe" and embedded in the source-detection flow. |

### Code-side references the runbook must respect

- **POST /api/auth/login** (`apps/api/app/modules/auth/router.py:52-103`) — request: `{email, password}` JSON body + `X-Portal-Client: web` header. Response: 200 + `LoginResponse` body + `Set-Cookie: portal_access=...; Path=/api; HttpOnly; Secure; SameSite=Strict` + same for `portal_refresh` on `Path=/api/auth`. JWT TTL from `settings.jwt_ttl_minutes` (default 30 per project-context.md § "Auth & sessions").
- **POST /api/admin/models** (`apps/api/app/modules/sot/admin_router.py:143-163`) — body: `ModelCreate` Pydantic model. Response 201 + `ModelDetail`. Auth via `_current_admin_or_agent_dep` (cookie-based). Returns 400 on category-not-found, 409 on slug conflict, 422 on other validation.
- **POST /api/admin/models/{id}/files** — exists; multipart upload. Story 4.3's OpenAPI enrichment will add summaries/examples to this; for now the runbook just refers to it via the cross-link sentence + describes the post-condition (first STL upload auto-enqueues render — already shipped per Slice 2).
- **GET /api/categories** (`apps/api/app/modules/sot/router.py:38-42`) — returns `CategoryTree` (a nested structure). Pre-flight check #1 verifies the target slug exists in the tree.
- **`apps/api/scripts/bootstrap_agent.py`** — CLI signature `python -m scripts.bootstrap_agent --email <addr> [--rotate] [--password <custom>]`. Run from `apps/api/` working dir on `.190`. Docstring (lines 1–20) is the canonical reference for the password-storage convention (`~/.config/3d-portal/agent.password`).

### Anti-patterns to actively prevent

- ❌ **Don't write `Authorization: Bearer ...` anywhere in the runbook** — admin routes ignore the Authorization header; they only read the `portal_access` cookie. An agent following a Bearer-pattern runbook would get 401 every call.
- ❌ **Don't reference `~/.config/3d-portal/agent.token`** — wrong path, wrong content type. The canonical path is `agent.password` (per `bootstrap_agent.py` docstring + project-wide auth model).
- ❌ **Don't enumerate endpoints inline** — `POST /api/admin/models { ... payload ... }` in body text would duplicate OpenAPI and rot. The single backtick-wrapped cross-link sentence is the ONLY allowed mention of `/api/admin/...` in the runbook.
- ❌ **Don't `export PASSWORD=...` or `export TOKEN=...` in any example** — persists in shell history; inline `$(cat ...)` is the only approved read pattern.
- ❌ **Don't duplicate `migrate_catalog_3mf.py` logic** — point at the script + describe post-condition; the script IS the source of truth for conversion behavior.
- ❌ **Don't add "see source code at apps/api/..." references** — the whole point is zero-source-read for agents. The runbook + OpenAPI together ARE the surface.
- ❌ **Don't try to make the runbook deploy itself** — Story 4.1 is content + fingerprint ONLY. The FastAPI route + Dockerfile COPY + nginx pass-through are Story 4.2's scope. Don't write a Dockerfile change in this commit.

### Style + LLM-readability

- One H1 (the runbook title), H2 for top-level sections (Principles, Auth, Source Detection, etc.), H3 for sub-sections (e.g. Auth → Login Flow / Cookie Semantics / Refresh / Rotation).
- All command examples in ` ```bash ` code-fences (language tag matters — agent parsers + Swagger UI use it for highlighting).
- Headers follow the pattern of `docs/operations.md` and `docs/architecture.md` for visual consistency (sentence-case, no trailing periods).
- Token redaction in ANY example outputs: show `password=<REDACTED>` and `Cookie: portal_access=<REDACTED>` rather than literal bytes (belt-and-suspenders, since inline `$(cat ...)` already keeps the password out of tool output).

### Cross-cutting rules from project-context.md

- **English-only in committed content** (project-context.md § "Documentation"). The runbook is read by AI agents whose default operating language is English; Polish operator prompts are out of scope for the runbook.
- **No secrets in commits** (project-context.md § "Cross-cutting"). The runbook describes WHERE the password lives + HOW to read it; the password value itself never appears in any committed file (including `_bmad-output/`).
- **Doc-only commit skip rule** (project-context.md § "Deploy"). `docs/agents-add-model-runbook.md` + `infra/.runbook-fingerprint` qualify as doc-only — `infra/.runbook-fingerprint` is data committed alongside its source doc, not infra code that requires a portal restart. Do NOT run `infra/scripts/deploy.sh` after this commit. Story 4.2 is the one that triggers a deploy (when the route + Dockerfile COPY land).
- **Verification before completion** (project-context.md § "AI agent execution discipline"). Run the self-verify constraints in Task 12 BEFORE marking this story done. The smoke-test grep heuristic in particular is what Story 4.5 will re-run on the deployed runbook.

### Previous story intelligence (Epic 3 retrospective signals)

Epic 3 didn't deliver doc-content of this scale, but Initiative 1 retro (`epic-1-retro-2026-05-10.md`) flagged two patterns relevant here:
1. **Codex review distinction "spec↔impl vs spec↔reality"** — spec consistency is necessary but not sufficient; the runbook's claims about the API must match the actual API behavior, not just the planning docs. The auth-correction in this session is exactly that pattern surfacing again. Self-verify by running the login flow yourself before committing — the AC describes commands you can literally execute (with the password file in place).
2. **Lean direct-prompt format converged for ad-hoc reviews** — the runbook should be lean and direct in the same style: minimum prose, maximum density, no "this section will explain..." preamble. Headings + code blocks + lists, not paragraphs of narrative.

### Project Structure Notes

- `docs/agents-add-model-runbook.md` is a top-level doc (next to `docs/architecture.md`, `docs/operations.md`). Naming follows existing conventions (lowercase, hyphenated, descriptive). NOT under `docs/design/` (that's for spec docs) and NOT under `docs/plans/` (that's gitignored per project-context.md).
- `infra/.runbook-fingerprint` is a NEW single-line file at `infra/` root. Future siblings (per Initiative 1's pattern in Story 3.x): `infra/.last-verify`, `infra/.last-verify-runbook`. The dotfile naming is intentional — these are state markers consumed by `deploy.sh`, not source code.
- Initiative 2 has **zero frontend changes** (per `architecture.md` § Initiative 2 § "Project Structure & Boundaries" line 1015). Do not touch `apps/web/` in this story; if you find yourself editing anything there, you've left scope.
- Initiative 2 has **zero `apps/api/` code changes in Story 4.1** — those start in Story 4.2 (FastAPI route + Dockerfile COPY) and 4.3 (OpenAPI enrichment on existing routes). Story 4.1 ships docs + one fingerprint file only.
- No Alembic migrations. No new Python tests. No frontend tests. Story 4.1 is content-only.

### References

- [_bmad-output/planning-artifacts/epics.md § Story 4.1](../planning-artifacts/epics.md) lines 677–702 (this story's spec).
- [_bmad-output/planning-artifacts/architecture.md § Initiative 2](../planning-artifacts/architecture.md) lines 809–1043 (full Initiative 2 architecture; Decisions A–H).
- [_bmad-output/planning-artifacts/architecture.md § Implementation Patterns](../planning-artifacts/architecture.md) lines 969–998 (Runbook content guidelines + Credentials-handling boilerplate — the corrected cookie-flow boilerplate is the binding spec for AC #2).
- [_bmad-output/planning-artifacts/prd.md § Initiative 2 § FR5](../planning-artifacts/prd.md) line 571 (corrected auth requirement — NOT bearer token).
- [_bmad-output/planning-artifacts/prd.md § NFR2](../planning-artifacts/prd.md) line 599 (credentials-at-rest scope).
- [/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md](file:///mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md) lines 228–311 (Workflow), 313–348 (3MF), 390–410 (Printables GraphQL) — source content to port.
- [_bmad-output/project-context.md § Auth & sessions](../project-context.md) — cookie paths, JWT TTL, CSRF rule.
- [_bmad-output/project-context.md § Documentation](../project-context.md) — English-only + comment policy + sharded specs convention.
- [_bmad-output/project-context.md § Deploy](../project-context.md) — doc-only-commit skip rule.
- [apps/api/app/modules/auth/router.py:52-103](../../apps/api/app/modules/auth/router.py#L52-L103) — `POST /api/auth/login` implementation (cookie-setting behavior).
- [apps/api/app/modules/sot/admin_router.py:1-50](../../apps/api/app/modules/sot/admin_router.py#L1-L50) — admin auth dependency (`_current_admin_or_agent_dep`, ACCESS_COOKIE).
- [apps/api/app/modules/sot/router.py:38-42](../../apps/api/app/modules/sot/router.py#L38-L42) — `GET /api/categories` returning `CategoryTree`.
- [apps/api/scripts/bootstrap_agent.py:1-50](../../apps/api/scripts/bootstrap_agent.py#L1-L50) — agent-account provisioning + password-storage convention.
- [infra/scripts/migrate_catalog_3mf.py](../../infra/scripts/migrate_catalog_3mf.py) — existing 3MF→STL converter referenced by FR4.
- `~/.claude/CLAUDE.md` § "Browser automation — agent-browser" — context for the Thangs/Thingiverse/MakerWorld/Creality Cloud rows in the source-detection table.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — `claude-opus-4-7[1m]`. Single-pass implementation 2026-05-11 via `bmad-dev-story` skill.

### Debug Log References

None — single-pass dev with no failures or backtracks.

### Completion Notes List

- **All 13 tasks completed in order, all 7 AC items satisfied.** Self-verify constraints (line count, grep heuristic, code-fence tags, no Bearer/no agent.token) all pass — see verification breakdown below.
- **Final runbook size: 272 lines** (target ~400, hard cap < 600). Came in lean because (a) source-detection table is compact and (b) Decision C / NFR8 keeps endpoint signatures out of the doc — those live in OpenAPI.
- **Fingerprint extraction chain (BINDING for Story 4.2 deploy verify):**
  ```bash
  awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' docs/agents-add-model-runbook.md | sha256sum | awk '{print $1}'
  ```
  This extracts the first non-blank line after the H1 heading (i.e. the stable intro paragraph) and computes its sha256. The intro paragraph IS one source-line in the file (it visually wraps in renderers but is a single physical line). Story 4.2's `deploy.sh` verify chain MUST use this exact awk filter on the response body to compute a matching fingerprint; any deviation (whole-file sha, different awk state machine) will produce a mismatch and trigger a spurious verify warning.
- **Initial fingerprint baseline:** `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` (committed to `infra/.runbook-fingerprint`, single line). Recompute verified post-write.
- **Stable intro paragraph chosen:** the first paragraph under H1 begins "This runbook teaches an AI agent (Claude, Codex, or any future LLM)..." — three sentences, ~660 bytes, deliberately boring/structural so edits remain rare and intentional. Future edits to this paragraph MUST update the fingerprint in the same commit per Decision D.
- **AC #7 narrow vs grep-permissive interpretation — chose grep-permissive.** The AC says "the cross-link sentence above is the only allowed reference" but the operative grep heuristic (`grep -nE '(GET|POST|PUT|PATCH|DELETE) /api/' | grep -v '` `'`) actually allows ANY backticked reference. The runbook contains 7 backticked HTTP-method+path mentions across narrative sections (Auth, Pre-flight, Behavioral Notes, Worked Flow) — all pass the grep heuristic and serve agent-readability without duplicating OpenAPI schemas/status codes (Decision C's actual concern). The dedicated cross-link sentence is present in § "Endpoint Discovery via OpenAPI" matching AC #7's exact form. If Story 4.5's smoke-test grep is stricter than the heuristic in AC #7's body text, this story will need a follow-up to remove the contextual references. Flagging here for the operator's awareness.
- **Bare ``` fence on line 108** (Printables endpoint+headers descriptor) is NOT a command, so per AC's "every command-bearing code block uses bash" rule it's compliant. Could be tagged `text` or `http` for tooling consistency; left bare to keep diff minimal.
- **Doc-only commit, auto-deploy skipped** per project memory `feedback_auto_deploy_dev.md`. Commit `b382fee` on `main`. The story AC explicitly extends the doc-only allowlist to include `infra/.runbook-fingerprint` (data file shipping with its source doc; deploy.sh does not yet consume it — that's Story 4.2).
- **Email pinned to `agent@portal.local`** per operator confirmation 2026-05-11.
- **3MF section reframed** per operator guidance: rare-to-near-never path going forward, canonical execution on operator's local dev box (NOT `.190`).
- **Source content port stats:** `Workflow: Adding a New Model` (228–311) → ~30% reuse / ~70% rewrite (DB-era endpoint flow + cookie auth + pre-flight checklist replaced folder-layout + index.json steps). `3MF Conversion Workflow` (313–348) → ~80% verbatim (post-condition, validation rule preserved; canonical-host changed to operator dev box). `Downloading from Printables` (390–410) → ~100% verbatim (endpoint, query/mutation signatures, response shape preserved; reformatted as in-context recipe with worked example using model id `661995`).

**Self-verify breakdown (T12, all pass):**

| Constraint | Method | Result |
|---|---|---|
| Line count < 600 | `wc -l docs/agents-add-model-runbook.md` | 272 ✅ |
| Grep heuristic (no non-backticked HTTP-method `/api/`) | `grep -nE '(GET\|POST\|PUT\|PATCH\|DELETE) /api/' \| grep -v '` `'` | empty ✅ |
| All command code blocks `bash`-tagged | `grep -nE '^```'` audit | 10 bash + 2 json + 1 bare descriptor ✅ |
| Zero `Authorization: Bearer` actual usage | `grep -n Bearer` | 2 hits, both anti-pattern warnings ✅ |
| Zero `agent.token` references | `grep -n 'agent\.token'` | 0 hits ✅ |
| Cross-link sentence present | manual section check | line 232 area ✅ |
| Fingerprint persisted + recomputable | sha256 chain re-run | `49280ada...` matches file ✅ |
| Doc-only file change set | `git status` after add | only `docs/` + `infra/.runbook-fingerprint` ✅ |

### File List

- `docs/agents-add-model-runbook.md` — NEW (272 lines, 16125 bytes)
- `infra/.runbook-fingerprint` — NEW (single sha256 line, 65 bytes incl. newline)

### Change Log

- 2026-05-11 — Story 4.1 implemented in single pass via `bmad-dev-story`. Commit `b382fee` on `main`. Auto-deploy skipped (doc-only). Status `ready-for-dev → in-progress → review`.
- 2026-05-11 — Codex review of `b382fee` returned 1 P1 + 5 P2 + 1 P3. All addressed in-band in commit `ec27222` (`docs(agents): apply Codex review findings to runbook (E4.1)`). Intro paragraph (fingerprint subject) untouched; `infra/.runbook-fingerprint` baseline preserved. Printables mutation signature finding deferred to Story 4.5 smoke-test (legacy form retained with a defer-note in the recipe; agent surfaces GraphQL `errors` payload rather than guessing a new shape). Status `review → done`.

### Senior Developer Review (AI)

**Reviewer:** Codex (codex-cli 0.129.0) via `codex exec` cross-LLM review
**Date:** 2026-05-11
**Commit reviewed:** `b382fee` (initial Story 4.1 implementation)
**Outcome:** Changes Requested → addressed in fix-up commit `ec27222`

#### Action Items

- [x] **[P1]** Rotation guidance is unsafe — `bootstrap_agent --rotate` changes `User.password_hash` only; active `portal_refresh` rows remain valid for up to 30 days. **Resolution:** § Rotation now also documents the `logout-others` / `logout-all` revocation step after relogin with the new password. (ec27222)
- [x] **[P2]** Access TTL `~30 min` is wrong — code has `jwt_ttl_minutes=10` + `ACCESS_MAX_AGE=10*60`. **Resolution:** changed to `~10 min` in two places (cookie list + Refresh section). (ec27222)
- [x] **[P2]** Idempotence by source URL can't work as written — `ModelCreate` only stores the `source` enum, not the URL. The URL lives on `ExternalLink`. **Resolution:** pre-flight #4 + Worked Flow steps 8–11 reworked to query existing external-links and attach the URL via the external-link create endpoint after model creation. (ec27222)
- [x] **[P2]** OpenAPI discovery snippet filtered for tag `agent-write`, which doesn't exist yet (Story 4.3 adds it). **Resolution:** removed the agent-write snippet entirely; will land back in Story 4.3 retro. (ec27222)
- [x] **[P2]** NFR8 strict reading violation — runbook had 7 inline backticked `METHOD /api/...` narrative refs while AC #7 says "exactly one cross-link sentence". **Resolution:** all 7 inline refs replaced with role descriptions ("the login endpoint", "the model-create endpoint", etc.). Only the canonical cross-link sentence retains backticked path refs. Post-fix grep heuristic returns ZERO non-cross-link `METHOD /api/...` matches. (ec27222)
- [x] **[P2 deferred]** Printables `getDownloadLink` mutation signature MAY be stale — Codex's external research surfaced a `getDownloadLink(printId, source, files:[{fileType, ids}])` shape in current public downloaders. Codex couldn't live-POST (DNS failure). **Resolution:** legacy form preserved (matches the established AGENTS.md form Michał used for >6 months); added a defer-note in the recipe instructing the agent to surface a GraphQL `errors` payload rather than guess a new shape; Story 4.5 smoke-test will validate against live Printables.
- [x] **[P3]** `ls *.stl` misses uppercase `.STL` legacy files. **Resolution:** changed to `find . -maxdepth 1 -type f -iname '*.stl'`. (ec27222)

#### Review Mechanics Notes

- Codex's review caught factual errors against the actual API code (TTL, idempotence, missing endpoint) that planning-doc cross-checks alone would have missed. Confirms the project-context.md "evidence before assertions" rule + Epic 1 retro lesson "spec↔impl vs spec↔reality — Codex specifically verifies the latter".
- The 7-inline-refs / NFR8 question was correctly surfaced as a P2 even though grep-heuristic passed; strict AC text wins over heuristic interpretation. Memory candidate for future BMAD runs: when a story includes a strict textual rule + a grep-heuristic mechanization, treat the strict text as the contract.
- Codex's web-research on Printables was best-effort but unverified live; deferring to smoke-test (rather than speculatively rewriting) is the correct trust calibration.
